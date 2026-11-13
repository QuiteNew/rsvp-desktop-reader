"""Tests that start the app itself with --self-check, the way the release build
starts the packaged one: a new process running main.py, with a report file, and
the exit code and the report as the only things it hands back.

That is the only way to test main.py's part, which is the few lines that hand
over to the self-check, and it is a fresh process on purpose. The window checks
build the real app, and a second app in a process that already has one runs
into CustomTkinter's pictures belonging to the first (see test_gui_smoke.py).

The child process gets an empty home folder, so none of this can read or write
the real ~/.rsvp_reader, on top of the self-check keeping off it itself."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    sys.platform.startswith("linux") and not os.environ.get("DISPLAY"),
    reason="needs a display, like the other tests that open the real app",
)


def _run_main(tmp_path, *, before_main=""):
    """Runs main.py --self-check in a new process. before_main is Python run
    first in that process, for breaking something on purpose. Gives the finished
    process, the report text (None if no report was written) and the home
    folder it was given."""
    home = tmp_path / "home"
    home.mkdir()
    report = tmp_path / "report.txt"
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    script = (
        "import runpy, sys\n"
        f"{before_main}\n"
        f"sys.argv = ['main.py', '--self-check', {str(report)!r}]\n"
        "runpy.run_path('main.py', run_name='__main__')\n"
    )
    finished = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=180,
    )
    text = report.read_text(encoding="utf-8") if report.exists() else None
    return finished, text, home


def test_the_app_started_with_the_flag_passes_its_own_checks(tmp_path):
    finished, report, home = _run_main(tmp_path)
    assert finished.returncode == 0, f"{finished.stdout}\n{finished.stderr}\n{report}"
    assert report is not None
    assert "SELF-CHECK PASSED" in report
    # every kind of check ran: the window, the libraries and an encrypted PDF
    assert "ok    window" in report
    assert "ok    closing the window" in report
    assert "ok    PDF import (AES-256)" in report


def test_the_self_check_leaves_the_home_folder_alone(tmp_path):
    finished, report, home = _run_main(tmp_path)
    assert finished.returncode == 0, f"{finished.stdout}\n{finished.stderr}\n{report}"
    assert not (home / ".rsvp_reader").exists()


def test_a_broken_window_gives_exit_code_1_and_a_report_that_says_so(tmp_path):
    """The crash the app once had when packaged: Pillow's Tk helper was left out
    of the build, so the first picture failed to draw. The helper can't be
    removed the same way on every system (Windows builds of Pillow don't look
    for the module Linux ones do), so the picture call itself is what fails."""
    breakage = (
        "import PIL.ImageTk\n"
        "def _no_tk_helper(*args, **kwargs):\n"
        "    raise RuntimeError('no Tk helper in this build')\n"
        "PIL.ImageTk.PhotoImage = _no_tk_helper\n"
    )
    finished, report, home = _run_main(tmp_path, before_main=breakage)
    assert finished.returncode == 1, f"{finished.stdout}\n{finished.stderr}\n{report}"
    assert report is not None
    # building the window fails first, so the checks after it never run
    failed = [line for line in report.splitlines() if line.startswith("FAIL")]
    assert any("no Tk helper in this build" in line for line in failed), report
    assert "SELF-CHECK FAILED" in report