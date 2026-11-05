"""The main window's controls, used the way a person uses them: the reading
keys, the buttons above the reader, and the dividers.

Other tests call the shortcut handlers and the canvas methods straight away,
which proves what each one does but not that a key is bound to it, that a
button is wired to it, or that the keys stay out of the way while someone types
in a text box. Here the keys are sent as key presses, the buttons are clicked,
and the dividers are dragged with the mouse, all in a real app.

The Up and Down keys change the speed by 10. Their size and limits have their
own tests (test_wpm_keys.py); here they only need to be bound.
"""
import pytest

from core.settings_store import BOTTOM_BAND_HEIGHT_RANGE, SIDEBAR_WIDTH_RANGE, SettingsStore
from gui.components.bookmarks_popover import BookmarksPopover
from tk_helpers import click_button, settle

WORDS = " ".join(f"w{number}" for number in range(400))
PAUSED = "▶"
RUNNING = "⏸"


# ---- helpers ----

def _reading_app(app, text=WORDS):
    """A transcript with text, paused on its first word, open in the main window
    with the keyboard on the window itself."""
    transcript = app.store.add_transcript("Book", app.store.current_space, wpm=300)
    app.store.set_transcript_text(transcript.id, text)
    app.store.set_transcript_paused(transcript.id, True)
    app._refresh_transcript_list()
    settle(app, 200)
    app._handle_open_transcript(transcript)
    settle(app, 300)
    app.focus_force()
    settle(app, 100)
    return transcript


@pytest.fixture
def reading(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _reading_app(app)
        yield app, transcript


def _press(app, key, target=None):
    """Send a key to the widget that has the keyboard, or the window if none
    has, the way a real key press arrives."""
    target = target or app.focus_get() or app
    target.event_generate(f"<{key}>")
    settle(app, 60)


def _index(app):
    return app.canvas.reader_display.session.index


def _pause_label(app):
    return app.canvas.toolbar.pause_button.cget("text")


# ---- the keys ----

def test_every_reading_key_reaches_its_action(reading, monkeypatch):
    app, transcript = reading
    assert transcript.is_paused and _pause_label(app) == PAUSED
    centred = []
    monkeypatch.setattr(app.canvas.reader_display, "center_pan", lambda: centred.append(True))

    _press(app, "space")
    assert transcript.is_paused is False and _pause_label(app) == RUNNING
    _press(app, "space")
    assert transcript.is_paused is True and _pause_label(app) == PAUSED

    start = _index(app)
    _press(app, "Right")
    assert _index(app) > start
    _press(app, "Left")
    assert _index(app) == start

    wpm = transcript.wpm
    _press(app, "Up")
    assert transcript.wpm == wpm + 10
    assert app.footer.wpm_slider.get() == wpm + 10, "the footer follows"
    _press(app, "Down")
    assert transcript.wpm == wpm

    for key in ("b", "B"):
        _press(app, key)
        assert [b.index for b in transcript.bookmarks] == [start], key
        _press(app, key)
        assert transcript.bookmarks == [], key

    for key in ("r", "R"):
        _press(app, "Right")
        assert _index(app) > start
        _press(app, key)
        assert transcript.is_paused is False, key
        assert _index(app) <= 1, f"{key} should start again from the first word"
        _press(app, "space")
        assert transcript.is_paused is True

    for key in ("c", "C"):
        before = len(centred)
        _press(app, key)
        assert len(centred) == before + 1, key

    for key in ("f", "F"):
        assert app._focus_mode is False
        _press(app, key)
        assert app._focus_mode is True, key
        assert app.list_body.winfo_manager() == "", "the sidebar is hidden"
        _press(app, key)
        assert app._focus_mode is False, key
        assert app.list_body.winfo_manager() != ""

    assert transcript.is_stopped is False
    _press(app, "Escape")
    assert transcript.is_stopped is True
    assert app.canvas._input_currently_shown, "Esc is Stop: back to the edit box"


def test_the_keys_do_nothing_with_no_transcript_open(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        app.focus_force()
        settle(app, 100)

        for key in ("space", "Left", "Right", "Up", "Down", "r", "b", "c", "Escape"):
            _press(app, key)

        assert app.store.transcripts == []
        assert app._current_transcript is None
        _press(app, "f")
        assert app._focus_mode is True, "focus mode doesn't need a transcript"
        _press(app, "f")


ALL_KEYS = ("space", "r", "R", "f", "F", "b", "B", "c", "C", "Left", "Right", "Up", "Down", "Escape")


def _everything_a_key_can_change(app, transcript, centred):
    """What the reading keys act on, so that one key doing something shows even
    when the next would have undone it (f and F, b and B)."""
    session = app.canvas.reader_display.session
    return (
        transcript.is_paused, transcript.wpm, len(transcript.bookmarks), transcript.is_stopped,
        session.index if session else None, app._focus_mode, len(centred),
    )


def test_the_keys_are_just_typing_while_a_search_box_has_the_keyboard(reading, monkeypatch):
    app, transcript = reading
    centred = []
    monkeypatch.setattr(app.canvas.reader_display, "center_pan", lambda: centred.append(True))
    _press(app, "Right")  # off the first word, so that Left would show
    assert _index(app) > 0
    entry = app.list_body._search_box._entry
    entry.focus_force()
    settle(app, 100)
    assert app.focus_get() is entry._entry
    before = _everything_a_key_can_change(app, transcript, centred)

    for key in ALL_KEYS:
        _press(app, key)
        assert _everything_a_key_can_change(app, transcript, centred) == before, key

    assert entry.get() == " rRfFbBcC", "the letters went into the box"


def test_the_keys_are_just_typing_while_the_edit_box_has_the_keyboard(tmp_path, open_real_app, monkeypatch):
    with open_real_app(tmp_path) as app:
        transcript = app.store.add_transcript("Draft", app.store.current_space, wpm=300)
        app._refresh_transcript_list()
        settle(app, 200)
        app._handle_open_transcript(transcript)
        settle(app, 300)
        centred = []
        monkeypatch.setattr(app.canvas.reader_display, "center_pan", lambda: centred.append(True))
        inner = app.canvas.input_view.textbox._textbox
        inner.focus_force()
        settle(app, 100)
        assert app.focus_get() is inner
        before = _everything_a_key_can_change(app, transcript, centred)

        for key in ALL_KEYS:
            _press(app, key)
            assert _everything_a_key_can_change(app, transcript, centred) == before, key

        assert app.canvas.input_view.get_text().strip() == "rRfFbBcC"


# ---- the buttons above the reader ----

def test_the_pause_restart_maximize_and_bookmark_buttons_do_what_they_say(reading):
    app, transcript = reading
    toolbar = app.canvas.toolbar

    click_button(toolbar.pause_button)
    settle(app, 60)
    assert transcript.is_paused is False and _pause_label(app) == RUNNING
    click_button(toolbar.pause_button)
    settle(app, 60)
    assert transcript.is_paused is True and _pause_label(app) == PAUSED

    start = _index(app)
    _press(app, "Right")
    assert _index(app) > start
    click_button(toolbar.restart_button)
    settle(app, 60)
    assert transcript.is_paused is False
    assert _index(app) <= 1, "restart goes back to the first word"
    click_button(toolbar.pause_button)
    settle(app, 60)

    assert toolbar.maximize_button.cget("text") == "< >"
    click_button(toolbar.maximize_button)
    settle(app, 100)
    assert app._focus_mode is True
    assert toolbar.maximize_button.cget("text") == "> <"
    click_button(toolbar.maximize_button)
    settle(app, 100)
    assert app._focus_mode is False
    assert toolbar.maximize_button.cget("text") == "< >"

    assert app.canvas._bookmarks_popover is None
    click_button(toolbar.bookmark_button)
    settle(app, 200)
    assert isinstance(app.canvas._bookmarks_popover, BookmarksPopover)


def test_the_detach_button_moves_the_reading_into_its_own_window(reading):
    app, transcript = reading

    click_button(app.canvas.toolbar.detach_button)
    settle(app, 600)

    assert app.canvas._detached_window is not None
    assert app.canvas._detached_transcript_id == transcript.id


def test_the_buttons_over_the_edit_box_change_nothing(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = app.store.add_transcript("Draft", app.store.current_space, wpm=300)
        app.store.set_transcript_draft_text(transcript.id, "a draft that has not been started")
        app._refresh_transcript_list()
        settle(app, 200)
        app._handle_open_transcript(transcript)
        settle(app, 300)
        before = (transcript.is_paused, transcript.is_stopped, transcript.raw_text, transcript.bookmarks)
        toolbar = app.canvas.toolbar

        click_button(toolbar.pause_button)
        click_button(toolbar.restart_button)
        click_button(toolbar.bookmark_button)
        settle(app, 300)

        assert (transcript.is_paused, transcript.is_stopped, transcript.raw_text, transcript.bookmarks) == before
        assert app.canvas._bookmarks_popover is None
        assert app.canvas._input_currently_shown


# ---- the dividers ----

def _drag(app, divider, dx=0, dy=0, start=(300, 300)):
    """Press the divider, move the mouse by dx, dy and let go. The events go to
    the canvas inside the divider, where its bindings are."""
    where = divider._canvas
    x0, y0 = start
    where.event_generate("<ButtonPress-1>", x=3, y=3, rootx=x0, rooty=y0)
    where.event_generate("<B1-Motion>", x=3 + dx, y=3 + dy, rootx=x0 + dx, rooty=y0 + dy)
    where.event_generate("<ButtonRelease-1>", x=3 + dx, y=3 + dy, rootx=x0 + dx, rooty=y0 + dy)
    settle(app, 60)


def _column_width(app):
    return int(app.grid_columnconfigure(0)["minsize"])


def _band_height(app):
    return int(app.grid_rowconfigure(4)["minsize"])


def _sizes(app):
    return (
        _column_width(app), _band_height(app),
        app.settings_store.sidebar_width, app.settings_store.bottom_band_height,
    )


def _dividers(app):
    return {
        "sidebar": app.vertical_divider,
        "bottom left": app.bottom_divider_left,
        "bottom right": app.bottom_divider_right,
    }


def test_the_dividers_ignore_the_mouse_while_free_resizing_is_off(tmp_path, open_real_app):
    def free_resizing_off():
        settings = SettingsStore()
        settings.set_freeform_resize_enabled(False)

    with open_real_app(tmp_path, before_start=free_resizing_off) as app:
        before = _sizes(app)

        for name, divider in _dividers(app).items():
            divider._canvas.event_generate("<Enter>", x=3, y=3)
            assert str(divider.cget("cursor")) == "", name
            _drag(app, divider, dx=60, dy=-60)
            assert _sizes(app) == before, name

        assert SettingsStore(settings_directory=str(tmp_path)).sidebar_width == before[2]


def test_the_dividers_drag_and_save_the_new_size_once_free_resizing_is_on(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        app.settings_store.set_freeform_resize_enabled(True)
        app._apply_freeform_resize_state()
        width, height = _column_width(app), _band_height(app)

        app.vertical_divider._canvas.event_generate("<Enter>", x=3, y=3)
        assert str(app.vertical_divider.cget("cursor")) == "sb_h_double_arrow"
        app.bottom_divider_left._canvas.event_generate("<Enter>", x=3, y=3)
        assert str(app.bottom_divider_left.cget("cursor")) == "sb_v_double_arrow"

        _drag(app, app.vertical_divider, dx=40)
        assert _column_width(app) == width + 40
        assert app.settings_store.sidebar_width == width + 40, "saved when the mouse is let go"

        _drag(app, app.bottom_divider_left, dy=-30)
        assert _band_height(app) == height + 30, "dragging up makes the band taller"
        assert app.settings_store.bottom_band_height == height + 30
        _drag(app, app.bottom_divider_right, dy=10)
        assert _band_height(app) == height + 20
        assert app.settings_store.bottom_band_height == height + 20, "both bottom dividers move the one band"
        assert app.settings_store.sidebar_width == width + 40, "and leave the sidebar alone"

        saved = SettingsStore(settings_directory=str(tmp_path))
        assert (saved.sidebar_width, saved.bottom_band_height) == (width + 40, height + 20)


def test_the_dividers_stop_at_the_limits(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        app.settings_store.set_freeform_resize_enabled(True)
        app._apply_freeform_resize_state()

        _drag(app, app.vertical_divider, dx=2000)
        assert _column_width(app) == SIDEBAR_WIDTH_RANGE[1]
        _drag(app, app.vertical_divider, dx=-2000)
        assert _column_width(app) == SIDEBAR_WIDTH_RANGE[0]
        _drag(app, app.bottom_divider_left, dy=-2000)
        assert _band_height(app) == BOTTOM_BAND_HEIGHT_RANGE[1]
        _drag(app, app.bottom_divider_right, dy=2000)
        assert _band_height(app) == BOTTOM_BAND_HEIGHT_RANGE[0]
        assert app.settings_store.sidebar_width == SIDEBAR_WIDTH_RANGE[0]
        assert app.settings_store.bottom_band_height == BOTTOM_BAND_HEIGHT_RANGE[0]


def test_free_resizing_can_be_switched_on_at_start_and_off_again(tmp_path, open_real_app):
    def free_resizing_on():
        settings = SettingsStore()
        settings.set_freeform_resize_enabled(True)

    with open_real_app(tmp_path, before_start=free_resizing_on) as app:
        width = _column_width(app)
        _drag(app, app.vertical_divider, dx=25)
        assert _column_width(app) == width + 25, "on from the start, as saved"

        app.settings_store.set_freeform_resize_enabled(False)
        app._apply_freeform_resize_state()
        assert str(app.vertical_divider.cget("cursor")) == ""
        _drag(app, app.vertical_divider, dx=25)
        assert _column_width(app) == width + 25, "off again"
