"""The window half of `RSVPReader --self-check`. The checks that need no window
are in core/self_check.py, and the reasons for all of this are in its
docstring. This part builds the real app window the way a normal start does,
looks at it, closes it the way the close button does, then runs the core
checks and writes the report.

The window it opens is a real one on screen for a second or two. On a build
machine that's the point: a packaged app that can't draw its window is exactly
what this is looking for.

None of it touches the real data folder. The three folder names the stores
read are pointed at a temporary one for the duration, the same way
tests/conftest.py does for the tests, so running this on your own machine
leaves your transcripts and settings alone."""

import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import core.settings_store as settings_store
import core.transcript_store as transcript_store
from core.app_info import APP_NAME
from core.font_choice import DYSLEXIA_FONTS, STANDARD_FONTS
from core.self_check import CheckResult, all_passed, describe_error, format_report, run_core_checks
from gui import theme
from gui.app import RSVPApp

# The module-level names the stores read when they're made with no folder
# given. Same list as in tests/conftest.py, which says why these three.
_FOLDER_NAMES = (
    (settings_store, "DEFAULT_DATA_DIR"),
    (settings_store, "SETTINGS_DIR"),
    (transcript_store, "DEFAULT_DATA_DIR"),
)

# How long the window gets to finish drawing itself before it's looked at. The
# app starts a few timers of its own, and on Windows a window doesn't come up
# in one go (see tests/tk_helpers.py).
SETTLE_SECONDS = 1.0

# The real window has a couple of hundred widgets. Anything near this few
# means the layout didn't get built.
MIN_WIDGET_COUNT = 50


@contextmanager
def _off_the_real_data(folder: Path):
    """Points the default data folder at `folder` and puts the real one back
    afterwards."""
    folder.mkdir(parents=True, exist_ok=True)
    originals = [(module, name, getattr(module, name)) for module, name in _FOLDER_NAMES]
    for module, name in _FOLDER_NAMES:
        setattr(module, name, folder)
    try:
        yield
    finally:
        for module, name, value in originals:
            setattr(module, name, value)


def _settle(window, seconds: float) -> None:
    """Runs Tk's event loop for a while, so the window's own startup timers
    get to finish."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        window.update()
        time.sleep(0.005)


def _count_widgets(widget) -> int:
    return 1 + sum(_count_widgets(child) for child in widget.winfo_children())


def _check_window_built(app) -> CheckResult:
    try:
        if not app.winfo_exists():
            return CheckResult("window", False, "the window doesn't exist")
        if app.title() != APP_NAME:
            return CheckResult("window", False, f"its title is {app.title()!r}, not {APP_NAME!r}")
        widgets = _count_widgets(app)
        if widgets < MIN_WIDGET_COUNT:
            return CheckResult("window", False, f"only {widgets} widgets were built")
    except Exception as error:
        return CheckResult("window", False, describe_error(error))
    return CheckResult("window", True)


def _check_bundled_files() -> CheckResult:
    """The icons and both font sets are where the app looks for them. These
    are the data files the build has to copy in, since nothing imports them.
    A missing one never stops the app from starting, which is why this looks
    for it, so a packaged app that quietly lost its fonts or icon fails here."""
    wanted = [theme._ICON_PNG, theme._ICON_ICO]
    wanted += [os.path.join(theme._FONT_DIR, name) for name in STANDARD_FONTS.files + DYSLEXIA_FONTS.files]
    missing = [os.path.basename(path) for path in wanted if not os.path.isfile(path)]
    if missing:
        return CheckResult("bundled icons and fonts", False, "missing: " + ", ".join(missing))
    return CheckResult("bundled icons and fonts", True)


def _check_tk_images(app) -> CheckResult:
    """Pillow can hand a picture to Tk. Pillow finds the module that does it by
    name at runtime, so a build can miss it and still start; the app then
    crashed the moment it drew its first icon (see RSVPReader.spec)."""
    try:
        from PIL import Image, ImageTk
        picture = ImageTk.PhotoImage(Image.new("RGB", (8, 8)), master=app)
        del picture
    except Exception as error:
        return CheckResult("pictures in Tk", False, describe_error(error))
    return CheckResult("pictures in Tk", True)


def check_window(app) -> list[CheckResult]:
    """What can be looked at once the app is built and has had time to draw."""
    return [_check_window_built(app), _check_bundled_files(), _check_tk_images(app)]


def _window_results() -> list[CheckResult]:
    """Builds the real app, checks it, and closes it the way the close button
    does, which also saves its settings (to the temporary folder, see above)."""
    try:
        app = RSVPApp()
    except Exception as error:
        return [CheckResult("window", False, describe_error(error))]
    results = []
    try:
        _settle(app, SETTLE_SECONDS)
        results.extend(check_window(app))
    except Exception as error:
        results.append(CheckResult("window", False, describe_error(error)))
    try:
        app._handle_close()
    except Exception as error:
        results.append(CheckResult("closing the window", False, describe_error(error)))
    else:
        results.append(CheckResult("closing the window", True))
    return results


def _deliver(report: str, report_path: str | None) -> bool:
    """Prints the report, and writes it to report_path when one was given. A
    packaged Windows app has no console to print to, which is why there's a
    file at all. False if the file couldn't be written."""
    try:
        print(report)
    except Exception:
        pass
    if report_path:
        try:
            Path(report_path).write_text(report, encoding="utf-8")
        except OSError:
            return False
    return True


def run_self_check(report_path: str | None) -> int:
    """Runs the whole self-check and gives the exit code: 0 when every check
    passed and the report was delivered, 1 otherwise. It never raises, because
    a packaged Windows app that dies with an unhandled error stops to show a
    dialog, and a dialog nobody can click would hold the build until it gave
    up."""
    try:
        with tempfile.TemporaryDirectory(prefix="rsvp_self_check_") as folder:
            work = Path(folder)
            with _off_the_real_data(work / "data"):
                results = _window_results()
            results.extend(run_core_checks(work / "files"))
    except Exception as error:
        results = [CheckResult("self-check", False, describe_error(error))]
    delivered = _deliver(format_report(results), report_path)
    return 0 if all_passed(results) and delivered else 1
