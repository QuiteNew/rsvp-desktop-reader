"""Tests for gui/self_check.py, the window half of RSVPReader --self-check, and
for how it turns the results into an exit code. The checks that need no window
are tested in test_self_check.py, and the whole thing started from the command
line is in test_self_check_command_line.py.

The window checks run against the real app, built the same way the other GUI
tests build it, with its data in a temporary folder. As in those tests, the gui
import is local, so a machine with no display skips instead of failing while
the files are being collected.

Like the core checks, these only mean something if they can fail, so each one
is shown a window, an icon file or a widget count that is wrong."""

import pytest

from core.self_check import CheckResult


@pytest.fixture(scope="module")
def app(tmp_path_factory, open_real_app):
    with open_real_app(tmp_path_factory.mktemp("rsvp_self_check")) as application:
        yield application


@pytest.fixture
def self_check_module():
    from gui import self_check

    return self_check


def _by_name(results):
    return {result.name: result for result in results}


# ---- The window ----

def test_a_real_window_passes_every_window_check(app, self_check_module):
    results = self_check_module.check_window(app)
    failed = [f"{result.name}: {result.detail}" for result in results if not result.ok]
    assert failed == []
    assert [result.name for result in results] == ["window", "bundled icons and fonts", "pictures in Tk"]


def test_a_window_with_the_wrong_title_fails(app, self_check_module):
    original = app.title()
    app.title("Something else")
    try:
        result = _by_name(self_check_module.check_window(app))["window"]
    finally:
        app.title(original)
    assert not result.ok
    assert "Something else" in result.detail


def test_a_window_with_too_few_widgets_fails(app, self_check_module, monkeypatch):
    monkeypatch.setattr(self_check_module, "MIN_WIDGET_COUNT", 100_000)
    result = _by_name(self_check_module.check_window(app))["window"]
    assert not result.ok
    assert "widgets" in result.detail


def test_a_missing_icon_file_is_named(app, self_check_module, monkeypatch, tmp_path):
    from gui import theme

    monkeypatch.setattr(theme, "_ICON_PNG", str(tmp_path / "app.png"))
    result = _by_name(self_check_module.check_window(app))["bundled icons and fonts"]
    assert not result.ok
    assert "app.png" in result.detail


def test_a_missing_font_file_is_named(app, self_check_module, monkeypatch, tmp_path):
    from gui import theme

    monkeypatch.setattr(theme, "_FONT_DIR", str(tmp_path))
    result = _by_name(self_check_module.check_window(app))["bundled icons and fonts"]
    assert not result.ok
    assert "Quicksand-Medium.ttf" in result.detail
    assert "OpenDyslexic3-Regular.ttf" in result.detail


def test_pillow_not_being_able_to_hand_a_picture_to_tk_fails(app, self_check_module, monkeypatch):
    from PIL import ImageTk

    def broken(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'PIL._tkinter_finder'")

    monkeypatch.setattr(ImageTk, "PhotoImage", broken)
    result = _by_name(self_check_module.check_window(app))["pictures in Tk"]
    assert not result.ok
    assert "_tkinter_finder" in result.detail


# ---- The real data folder is left alone ----

def test_the_data_folder_is_pointed_somewhere_else_and_then_put_back(tmp_path, self_check_module):
    import core.settings_store as settings_store
    import core.transcript_store as transcript_store

    names = [
        (settings_store, "DEFAULT_DATA_DIR"),
        (settings_store, "SETTINGS_DIR"),
        (transcript_store, "DEFAULT_DATA_DIR"),
    ]
    before = [getattr(module, name) for module, name in names]
    folder = tmp_path / "data"
    with self_check_module._off_the_real_data(folder):
        assert [getattr(module, name) for module, name in names] == [folder] * 3
        assert folder.is_dir()
    assert [getattr(module, name) for module, name in names] == before


def test_the_data_folder_is_put_back_even_when_the_checks_blow_up(tmp_path, self_check_module):
    import core.settings_store as settings_store

    before = settings_store.SETTINGS_DIR
    with pytest.raises(RuntimeError):
        with self_check_module._off_the_real_data(tmp_path / "data"):
            raise RuntimeError("boom")
    assert settings_store.SETTINGS_DIR == before


# ---- The exit code and the report ----

@pytest.fixture
def fake_window(self_check_module, monkeypatch):
    """Stands in for building the real window, so these tests can look at the
    exit code and the report without opening another one. Hands back the list
    of results the stand-in will give."""
    results = [CheckResult("window", True)]
    monkeypatch.setattr(self_check_module, "_window_results", lambda: list(results))
    return results


def test_everything_passing_gives_exit_code_0_and_a_report_file(tmp_path, self_check_module, fake_window):
    report = tmp_path / "report.txt"
    assert self_check_module.run_self_check(str(report)) == 0
    text = report.read_text(encoding="utf-8")
    assert "SELF-CHECK PASSED" in text
    assert "ok    window" in text
    assert "PDF import (AES-256)" in text


def test_a_failing_window_check_gives_exit_code_1_and_says_why(tmp_path, self_check_module, fake_window):
    fake_window[:] = [CheckResult("window", False, "it had no widgets")]
    report = tmp_path / "report.txt"
    assert self_check_module.run_self_check(str(report)) == 1
    text = report.read_text(encoding="utf-8")
    assert "FAIL  window: it had no widgets" in text
    assert "SELF-CHECK FAILED: 1 of" in text


def test_a_failing_core_check_gives_exit_code_1(tmp_path, self_check_module, fake_window, monkeypatch):
    monkeypatch.setattr(
        self_check_module, "run_core_checks", lambda folder: [CheckResult("PDF import (AES-256)", False, "no cryptography")]
    )
    assert self_check_module.run_self_check(str(tmp_path / "report.txt")) == 1


def test_a_report_file_that_cannot_be_written_gives_exit_code_1(tmp_path, self_check_module, fake_window):
    folder_not_file = tmp_path / "a folder"
    folder_not_file.mkdir()
    assert self_check_module.run_self_check(str(folder_not_file)) == 1


def test_no_report_file_given_still_runs_and_gives_the_exit_code(self_check_module, fake_window, capsys):
    assert self_check_module.run_self_check(None) == 0
    assert "SELF-CHECK PASSED" in capsys.readouterr().out


def test_an_unexpected_error_never_escapes_and_gives_exit_code_1(tmp_path, self_check_module, fake_window, monkeypatch):
    """An unhandled error in the packaged Windows app stops to show a dialog
    that nobody is there to click, so the function has to catch everything."""
    def explode(folder):
        raise RuntimeError("something nobody planned for")

    monkeypatch.setattr(self_check_module, "run_core_checks", explode)
    report = tmp_path / "report.txt"
    assert self_check_module.run_self_check(str(report)) == 1
    assert "something nobody planned for" in report.read_text(encoding="utf-8")


def test_the_real_close_path_is_part_of_the_checks(app, self_check_module, monkeypatch):
    """_window_results builds its own app, so here it is given the shared one
    through a stand-in for the constructor, and its close would end the module's
    app early. What is looked at is only that a failure to close is reported
    rather than raised."""
    class AppThatFailsToClose:
        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def _handle_close(self):
            raise RuntimeError("could not save")

    monkeypatch.setattr(self_check_module, "RSVPApp", lambda: AppThatFailsToClose(app))
    monkeypatch.setattr(self_check_module, "SETTLE_SECONDS", 0)
    results = _by_name(self_check_module._window_results())
    assert results["window"].ok
    assert not results["closing the window"].ok
    assert "could not save" in results["closing the window"].detail
