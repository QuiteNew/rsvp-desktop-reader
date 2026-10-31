"""Tests for the bold word starts setting being saved and brought back by the
app (gui/app.py: _handle_bold_starts_toggled and the way the Canvas is built).

How the windows pass a click along is tested in test_bold_starts_wiring.py with
a plain callback in place of the app. Here the real app is on the other end, so
the question is whether a click ends up in the settings store and in
settings.json, whether the app opens with the look it saved, and whether a
selection preview, which keeps its own button, stays out of all that.

Persistence is redirected to a temporary directory. The setting is saved there
before the app is built, and the whole module runs twice, once with it saved as
on and once as off, so "opens with what was saved" cannot be mistaken for
"always opens on" or "always opens off". One app, one Tk root at a time, like
test_gui_smoke.py, with the picture caches that tie the toolbar to a root emptied
around each one (see fresh_widget_image_caches in conftest.py)."""

import json
from dataclasses import asdict

import pytest

import core.storage as storage
import core.settings_store as settings_store
import core.transcript_store as transcript_store

from tk_helpers import cancel_pending_afters, settle

_REDIRECT_TARGETS = (
    (storage, "DEFAULT_DATA_DIR"),
    (settings_store, "DEFAULT_DATA_DIR"),
    (settings_store, "SETTINGS_DIR"),
    (transcript_store, "DEFAULT_DATA_DIR"),
)


@pytest.fixture(scope="module", params=[True, False], ids=["saved_on", "saved_off"])
def saved_look(request):
    """Whether the look was saved as on before this round's app was built."""
    return request.param


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory, saved_look):
    return tmp_path_factory.mktemp("rsvp_bold_starts_app")


@pytest.fixture(scope="module")
def app(data_dir, saved_look, fresh_widget_image_caches):
    """An RSVPApp whose settings, saved beforehand in a temporary directory, have
    the bold word starts as saved_look says. Skips if Tk has no display."""
    import tkinter

    originals = [(mod, name, getattr(mod, name)) for mod, name in _REDIRECT_TARGETS]
    for mod, name in _REDIRECT_TARGETS:
        setattr(mod, name, data_dir)

    def _restore():
        for mod, name, value in originals:
            setattr(mod, name, value)

    fresh_widget_image_caches()
    settings_store.SettingsStore().set_bold_starts_enabled(saved_look)

    from gui.app import RSVPApp

    try:
        application = RSVPApp()
    except tkinter.TclError as exc:
        _restore()
        pytest.skip(f"Tk can't start a display here: {exc}")

    application.withdraw()
    application.update_idletasks()
    try:
        yield application
    finally:
        # Put the app back on screen before destroying it. On Linux, destroying
        # an app that is hidden with withdraw() makes the next window that takes
        # the keyboard focus crash Tk, in whatever test comes next. deiconify()
        # on its own isn't enough, the window has to really be shown again, and
        # that takes a turn of the event loop.
        application.deiconify()
        settle(application)
        # CustomTkinter keeps a few timers going on its windows, and a destroyed
        # app leaves the next round of them pending. They would run during the
        # next test module and report errors about a destroyed app. Each is
        # cancelled through the widget that scheduled it (see tk_helpers.py).
        cancel_pending_afters(application)
        application.destroy()
        _restore()
        fresh_widget_image_caches()


def _bold_pieces(input_view):
    from gui.components.transcript_input import BOLD_TAG

    inner = input_view.textbox._textbox
    ranges = inner.tag_ranges(BOLD_TAG)
    return [inner.get(str(ranges[i]), str(ranges[i + 1])) for i in range(0, len(ranges), 2)]


def is_on(input_view):
    """Whether the box shows the look, by its text: the same words in bold or not."""
    input_view.set_text("hello world")
    return _bold_pieces(input_view) == ["hel", "wor"]


def click(input_view):
    input_view.bold_starts_button.invoke()


def saved_on_disk(data_dir):
    """The setting as settings.json holds it right now."""
    return json.loads((data_dir / "settings.json").read_text(encoding="utf-8"))["bold_starts_enabled"]


def open_a_transcript(application):
    """Add a transcript with text and open it, so there is something to detach
    and to take a selection from."""
    store = application.store
    transcript = store.add_transcript("Bold starts", store.current_space)
    store.set_transcript_text(transcript.id, "one two three four five six seven eight")
    application._handle_open_transcript(transcript)
    return transcript


@pytest.fixture(scope="module")
def opened_with(app):
    """What the app showed as it came up. Read once, before any test has
    changed anything, since the fixture below puts things back after each one."""
    return {
        "store": app.settings_store.bold_starts_enabled,
        "canvas": app.canvas._bold_starts_enabled,
        "main_box": is_on(app.canvas.input_view),
    }


@pytest.fixture(autouse=True)
def back_to_what_was_saved(app, saved_look, opened_with):
    """Each test starts with the look as the app was built with it, and leaves it so."""
    app.settings_store.set_bold_starts_enabled(saved_look)
    app.canvas.set_bold_starts_enabled(saved_look)
    yield
    for window, _, _ in list(app.canvas._selection_previews):
        settle(window)
        cancel_pending_afters(window)
        window.close()
    if app.canvas._detached_window is not None:
        window = app.canvas._detached_window
        settle(window)
        cancel_pending_afters(window)
        app.canvas._handle_reattach()
    settle(app, 100)
    app.canvas.stop()


# ---- opening ----

def test_the_app_opens_with_the_look_it_saved(opened_with, saved_look):
    assert opened_with == {"store": saved_look, "canvas": saved_look, "main_box": saved_look}

def test_a_detached_window_opens_with_the_saved_look(app, saved_look):
    open_a_transcript(app)
    app.canvas._handle_detach()
    window = app.canvas._detached_window
    settle(window)
    assert is_on(window.input_view) is saved_look


# ---- saving ----

def test_a_click_in_the_main_edit_box_is_saved(app, data_dir, saved_look):
    click(app.canvas.input_view)
    assert app.settings_store.bold_starts_enabled is (not saved_look)
    assert saved_on_disk(data_dir) is (not saved_look)
    click(app.canvas.input_view)
    assert app.settings_store.bold_starts_enabled is saved_look
    assert saved_on_disk(data_dir) is saved_look

def test_what_was_clicked_is_there_for_the_next_start(app, saved_look):
    click(app.canvas.input_view)
    assert settings_store.SettingsStore().bold_starts_enabled is (not saved_look)
    click(app.canvas.input_view)
    assert settings_store.SettingsStore().bold_starts_enabled is saved_look

def test_a_click_in_the_detached_window_is_saved_and_reaches_the_main_box(app, data_dir, saved_look):
    open_a_transcript(app)
    app.canvas._handle_detach()
    window = app.canvas._detached_window
    settle(window)
    click(window.input_view)
    assert app.settings_store.bold_starts_enabled is (not saved_look)
    assert saved_on_disk(data_dir) is (not saved_look)
    assert is_on(app.canvas.input_view) is (not saved_look)
    assert is_on(window.input_view) is (not saved_look)

def test_a_click_changes_nothing_but_this_one_setting(app, saved_look):
    # Both ways, so a stray write that happens to match the old value is caught.
    for expected in (not saved_look, saved_look):
        before = asdict(app.settings_store._settings)
        click(app.canvas.input_view)
        after = asdict(app.settings_store._settings)
        changed = {key for key in before if before[key] != after[key]}
        assert changed == {"bold_starts_enabled"}
        assert after["bold_starts_enabled"] is expected


# ---- the selection previews stay out of it ----

def test_a_preview_opens_with_the_saved_look_and_its_click_is_not_saved(app, data_dir, saved_look):
    open_a_transcript(app)
    app.canvas.open_selection_preview("alpha beta gamma")
    preview = app.canvas._selection_previews[-1][0]
    settle(preview)
    assert is_on(preview.input_view) is saved_look
    click(preview.input_view)
    assert is_on(preview.input_view) is (not saved_look)
    assert app.settings_store.bold_starts_enabled is saved_look
    assert saved_on_disk(data_dir) is saved_look
    assert is_on(app.canvas.input_view) is saved_look