"""Shared pytest fixtures for the whole suite.

The one thing worth centralizing: making sure no test can ever read or write
the real ~/.rsvp_reader. Tests that build a store with an explicit tmp_path are
already isolated, but a store constructed with no arguments falls back to the
on-disk default location. This points those fallbacks at a throwaway temp
directory, as a safety net, so a no-argument SettingsStore() or
TranscriptStore() in any test (today or later) stays off your real data.

It has to happen before any test file is even loaded, not just before the
first test runs. gui/theme.py reads the saved settings the moment it is
imported, to pick the colour theme and the fonts, and test files import it
while pytest is still collecting them. When this was a session fixture, that
read still reached the real settings, so the whole suite ran in whatever theme
and font the app on that machine was set to, and a test about the font failed
on a machine with the OpenDyslexic font switched on.

It deliberately leaves core.storage.DEFAULT_DATA_DIR itself untouched, so
test_storage.py's check that the default sits under the home directory still
sees the real value.

It also holds fresh_widget_image_caches, which a test module that builds the
toolbar (so, a Canvas or the whole app) asks for when it makes a Tk root of its
own, root, the hidden Tk root a test module builds its own widgets and windows
on, wait_until_shown, for a test that needs a window to actually be on screen,
and open_real_app, for a test that builds the whole app. See each fixture for
why.
"""
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

import core.settings_store as settings_store
import core.transcript_store as transcript_store


# The module-level names the no-argument store constructors actually read:
#   SettingsStore()   -> settings_store.SETTINGS_DIR
#   AppSettings()     -> settings_store.DEFAULT_DATA_DIR  (data_directory default)
#   TranscriptStore() -> transcript_store.DEFAULT_DATA_DIR
# core.storage.DEFAULT_DATA_DIR is the original these were copied from; it is
# left alone on purpose, so test_storage.py still sees the real home path.
_FALLBACK_LOCATION_NAMES = (
    (settings_store, "DEFAULT_DATA_DIR"),
    (settings_store, "SETTINGS_DIR"),
    (transcript_store, "DEFAULT_DATA_DIR"),
)


# The redirect in place for this run: (safe folder, the values it replaced).
_redirect = {}


def pytest_configure(config):
    """Point the default data location at a fresh temp folder before pytest
    loads any test file (see the module docstring for why it can't wait)."""
    safe_dir = Path(tempfile.mkdtemp(prefix="rsvp_no_real_data_"))
    _redirect["safe_dir"] = safe_dir
    _redirect["originals"] = [(mod, name, getattr(mod, name)) for mod, name in _FALLBACK_LOCATION_NAMES]
    for mod, name in _FALLBACK_LOCATION_NAMES:
        setattr(mod, name, safe_dir)


def pytest_unconfigure(config):
    """Put the real locations back and remove the temp folder."""
    for mod, name, value in _redirect.get("originals", []):
        setattr(mod, name, value)
    if "safe_dir" in _redirect:
        shutil.rmtree(_redirect["safe_dir"], ignore_errors=True)


def _forget_cached_widget_images() -> None:
    """Empty the module-level caches that hold a picture made for one Tk root."""
    from gui import theme
    from gui.components import canvas_toolbar

    canvas_toolbar._BOOKMARK_IMAGE = None
    theme._icon_photo_image = None


@pytest.fixture(scope="module")
def fresh_widget_image_caches():
    """For a test module that makes its own Tk root and builds the toolbar.

    The toolbar's bookmark picture (and, off Windows, the window icon) is made
    once and kept in a module-level variable, and a picture belongs to the Tk
    root that was running when it was made. A second root in the same process
    then fails with "image pyimageN doesn't exist" the moment it builds a toolbar,
    and a root that is gone leaves its picture behind for the next module to trip
    over. test_gui_smoke.py avoids it by sharing one root for the whole module.
    A module that cannot share that root empties the caches here, before its own
    root is made and again after it is destroyed. Only the modules that ask for
    it are affected.

    What the fixture hands back is the function that empties them, for a module
    that makes more than one root in turn (a fixture with several parameters):
    call it before each new root is made and after each one is destroyed."""
    _forget_cached_widget_images()
    yield _forget_cached_widget_images
    _forget_cached_widget_images()


@pytest.fixture(scope="module")
def root(fresh_widget_image_caches):
    """One hidden CustomTkinter root for a whole test module, for tests that
    build their own widgets and windows on it rather than the whole app. Skips
    if Tk has no display.

    The picture caches are emptied around it (see fresh_widget_image_caches):
    the popups and the Settings window set the app icon, and that picture
    belongs to the root it was made for.

    When the module is done, every timer still waiting is cancelled before the
    root is destroyed. CustomTkinter keeps a few going on its windows, and left
    alone they would run during the next module and report errors about a
    destroyed app. Each one that a live widget scheduled is cancelled through
    that widget (see cancel_pending_afters in tk_helpers.py). What's left after
    that belongs to widgets a test has already destroyed, and is cancelled
    directly.

    It stays hidden to the end. Destroying the real app while it was hidden
    made Tk crash on Linux (see open_real_app), but a plain root like this one
    hasn't done that, with the whole suite run in one process."""
    window = _new_root()
    window.withdraw()
    yield window
    _take_down_root(window)


def _new_root():
    """A new CustomTkinter root, or a skip if Tk has no display."""
    import tkinter

    import customtkinter as ctk

    try:
        return ctk.CTk()
    except tkinter.TclError as exc:
        pytest.skip(f"Tk can't start a display here: {exc}")


def _take_down_root(window):
    """Cancel every timer the root still has waiting, then destroy it. See the
    root fixture for why it's done in two steps."""
    from tk_helpers import cancel_pending_afters

    cancel_pending_afters(window)
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()


@pytest.fixture
def wait_until_shown():
    """For a test that needs a window on screen. Hands back a function that
    runs the event loop until the window is shown and has had time to lay
    itself out, and fails with the window's state if that doesn't happen.

    A fixed wait isn't enough on Windows. A new CTkToplevel hides itself to
    colour its title bar and comes back on a timer, and Settings does that
    twice. How long that takes changes from run to run: the same Settings
    window sometimes wasn't back after 300 ms and sometimes was.

    The loop runs in steps of 300 ms and stops at the end of a step where the
    window is shown. Stopping as soon as it shows would be too early, because
    the second round of hiding can still be coming."""
    def wait(window, timeout=5.0, step=0.3):
        deadline = time.monotonic() + timeout
        while True:
            end = time.monotonic() + step
            while time.monotonic() < end:
                window.update()
                time.sleep(0.005)
            if window.winfo_ismapped():
                return
            if time.monotonic() > deadline:
                owner = window.master.winfo_toplevel()
                raise AssertionError(
                    f"{type(window).__name__} did not appear within {timeout} s: "
                    f"its state is {window.state()!r}, its owner's is {owner.state()!r} "
                    f"and the owner is {'shown' if owner.winfo_ismapped() else 'not shown'}"
                )

    return wait


@pytest.fixture(scope="module")
def open_real_app(fresh_widget_image_caches):
    """For a test, or a module's fixture, that builds the whole app. Hands back
    a context manager:

        with open_real_app(tmp_path) as app:
            ...

    Inside the with block the app's data lives in data_dir, and the app has
    been built and drawn once. At the end the app is taken down and the real
    locations are put back. Skips if Tk has no display.

    Every test that builds the real app used to do all of this itself, and two
    rules kept getting missed. Both live here now.

    Windows: the app is drawn once right after it's built, while the sidebar
    list is still empty. Adding transcripts and rebuilding the list before the
    window had ever been drawn made the list's CustomTkinter scrollbar redraw
    itself without end. The list never got a size, the test hung and the memory
    filled up. Most likely because Windows reports a widget's new size in the
    middle of laying out its neighbours, and the scrollbar's redraw then forces
    Tk to finish that layout from inside it.

    Linux: an app that is hidden is shown again before it's destroyed.
    Destroying an app hidden with withdraw() makes the next window that takes
    the keyboard focus crash Tk, in whatever test comes next.

    The options:

    before_start runs after the data has been moved to data_dir and before the
    app is built, for saving something the app should find when it starts. A
    store made with no arguments in there writes to data_dir. Doing the same
    thing before the with block would save the suite's shared stand-in folder
    (see pytest_configure) into the settings as the data folder, and the app
    would read and write its transcripts there instead of in data_dir.

    first_settle_ms is how long the app gets for that first draw. A test that
    has to change the app before the event loop ever runs passes 0, and then
    it isn't drawn first.

    hidden keeps the app off screen for the whole with block: it's hidden with
    withdraw() straight after it's built, instead of being drawn first, and its
    layout is worked out so that a mistake in it shows up there and then. It
    comes back on screen only to be destroyed, for the Linux rule above.

    A test may close the app itself, the way the window's close button does.
    The end of the with block then leaves it alone."""
    return lambda data_dir, **options: _real_app(fresh_widget_image_caches, data_dir, **options)


@contextmanager
def _real_app(forget_cached_images, data_dir, before_start=None, first_settle_ms=300, hidden=False):
    """The work behind open_real_app. See that fixture for what each step is for."""
    import tkinter

    from tk_helpers import settle

    originals = [(mod, name, getattr(mod, name)) for mod, name in _FALLBACK_LOCATION_NAMES]
    for mod, name in _FALLBACK_LOCATION_NAMES:
        setattr(mod, name, data_dir)
    forget_cached_images()
    try:
        if before_start is not None:
            before_start()

        from gui.app import RSVPApp

        try:
            app = RSVPApp()
        except tkinter.TclError as exc:
            pytest.skip(f"Tk can't start a display here: {exc}")
        try:
            if hidden:
                app.withdraw()
                app.update_idletasks()
            elif first_settle_ms:
                settle(app, first_settle_ms)
            yield app
        finally:
            _take_down(app)
    finally:
        for mod, name, value in originals:
            setattr(mod, name, value)
        forget_cached_images()


def _take_down(app):
    """Destroy a real app safely, unless a test has closed it already."""
    import tkinter

    from tk_helpers import cancel_pending_afters, settle

    try:
        if not app.winfo_exists():
            return
    except tkinter.TclError:
        return  # already destroyed, by the app's own close button for example
    if app.state() == "withdrawn":
        # deiconify() on its own isn't enough, the window has to really be
        # shown again, and that takes a turn of the event loop.
        app.deiconify()
        settle(app)
    # CustomTkinter keeps a few timers going on its windows, and a destroyed
    # app leaves the next round of them pending. They would run during the next
    # test and report errors about a destroyed app.
    cancel_pending_afters(app)
    app.destroy()