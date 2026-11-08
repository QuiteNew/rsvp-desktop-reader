"""Detaching a selection, used the way a person does it: select some words in the
edit box, right-click, choose Detach, and then use the little window that opens
(gui/components/selection_preview_window.py, and the right-click menu in
gui/components/transcript_input.py).

Other tests call the menu's and the window's methods straight away, which proves
what each one does but not that the right-click opens the menu, that a row is
wired to its action, that Esc or a click elsewhere closes the menu, or that a
key or a button in the new window reaches its handler. Here the right-click, the
row click, the keys and the buttons are all real events in a real app, and each
time the test looks at what is on screen and at what was saved.

The window is meant to be throwaway: it reads its own copy of the words and is
given nothing that could save to the transcript. So half of the tests below
check the other side of that promise, that nothing done in the window ever
reaches the transcript it came from, in memory or on disk.

The window opens 500 pixels wide, the same as the detached transcript window,
and its buttons need about 610 (see test_detached_window_controls.py). At 500 the
restart button has no room and isn't shown. A person drags the window wider to
reach it, and so do the tests.
"""
import json

import pytest

from core.transcript_store import TranscriptStore
from tk_helpers import click, click_button, settle

WORD_LIST = [f"w{number}" for number in range(400)]
WORDS = " ".join(WORD_LIST)
PAUSED = "▶"
RUNNING = "⏸"


# ---- the main window: a transcript in its edit box, with words selected ----

def _add_book(app, title="Book"):
    """A transcript that was read and stopped, so it opens in the edit box with
    its text. Its speed is the default 300 a minute, a word every 200 ms."""
    transcript = app.store.add_transcript(title, app.store.current_space, wpm=300)
    app.store.set_transcript_text(transcript.id, WORDS)
    app.store.set_transcript_stopped(transcript.id, True)
    app._refresh_transcript_list()
    settle(app, 200)
    return transcript


@pytest.fixture
def book(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _add_book(app)
        app._handle_open_transcript(transcript)
        settle(app, 300)
        # Tk prints an error raised inside a key, button or menu handler and
        # carries on, so without this a handler that fell over would not fail a
        # test.
        app.callback_errors = []
        app.report_callback_exception = lambda *details: app.callback_errors.append(details)
        yield app, transcript


def _inner(app):
    return app.canvas.input_view.textbox._textbox


def _select(app, first=0, count=60):
    """Select `count` words of the edit box's text, from word number `first`.
    Returns them as the text a person would expect the menu to act on."""
    start = len(" ".join(WORD_LIST[:first])) + (1 if first else 0)
    chosen = " ".join(WORD_LIST[first:first + count])
    inner = _inner(app)
    inner.tag_remove("sel", "1.0", "end")
    inner.tag_add("sel", f"1.0 + {start} chars", f"1.0 + {start + len(chosen)} chars")
    return chosen


def _right_click(app):
    """Right-click on the first selected character, with the keyboard in the
    box. Returns where on the screen the click was."""
    inner = _inner(app)
    inner.focus_force()
    settle(app, 100)
    x, y = inner.bbox("sel.first")[:2]
    x, y = x + 1, y + 1
    where = (inner.winfo_rootx() + x, inner.winfo_rooty() + y)
    inner.event_generate("<Button-3>", x=x, y=y, rootx=where[0], rooty=where[1])
    settle(app, 150)
    return where


def _menu_rows(app):
    """The open menu's rows by name."""
    popup = app.canvas.input_view._selection_menu
    if popup is None:
        return {}
    return {row.cget("text"): row for row in popup.winfo_children()[0].winfo_children()}


def _menu_open(app):
    box = app.canvas.input_view
    popup = box._selection_menu
    return bool(box._selection_menu_visible and popup is not None and popup.winfo_ismapped())


def _choose(app, label):
    """Click a row of the open menu, and give a window it opens time to come up."""
    _menu_rows(app)[label].event_generate("<Button-1>")
    settle(app, 500)


def _saved_entry(app, tmp_path, transcript):
    """What the data file holds for the transcript right now."""
    app.store.flush()
    saved = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
    return next(entry for entry in saved["transcripts"] if entry["id"] == transcript.id)


def _detach_selection(app, first=0, count=60, wide=True):
    """Select words, right-click and choose Detach. Returns the window that
    opened and the words it was given. `wide` drags it wider, as a person would
    to get at all its buttons."""
    chosen = _select(app, first, count)
    _right_click(app)
    _choose(app, "Detach")
    window = app.canvas._selection_previews[-1][0]
    if wide:
        window.geometry("700x350")
        settle(window, 300)
    return window, chosen


def _close_with_the_x(app, window):
    """What the window's close button in the title bar does."""
    window.tk.call(window.protocol("WM_DELETE_WINDOW"))
    settle(app, 100)


# ---- the small window ----

@pytest.fixture
def preview(book):
    app, transcript = book
    window, chosen = _detach_selection(app)
    yield app, transcript, window, chosen


def _give_keyboard(window):
    """Put the keyboard on the window itself, as a person clicking into it would."""
    window.focus_force()
    settle(window, 100)


def _press(widget, key):
    """Send a key to the widget that has the keyboard, or to `widget` if none
    has, the way a real key press arrives."""
    (widget.focus_get() or widget).event_generate(f"<{key}>")
    settle(widget, 60)


def _start(window, paused=True):
    """Click Start reading, and by default pause on whichever word it has got to,
    so the reading stands still while a test looks at it."""
    click_button(window.input_view.start_button)
    settle(window, 300)
    _give_keyboard(window)
    if paused:
        click_button(window.toolbar.pause_button)
        settle(window, 60)


def _index(window):
    return window.reader_display.session.index


def _pause_label(window):
    return window.toolbar.pause_button.cget("text")


def _shown(window):
    reader = window.reader_display
    return "".join(label.cget("text") for label in (reader.before_label, reader.focus_label, reader.after_label))


def _read_on_until(window, index, timeout_ms=5000):
    waited = 0
    while _index(window) < index and waited < timeout_ms:
        settle(window, 50)
        waited += 50
    assert _index(window) >= index, "the reading didn't go on"


def _percent(window):
    return int(window.toolbar.percent_readout.cget("text").rstrip("%"))


# ---- the right-click menu ----

def test_a_right_click_on_a_selection_opens_the_menu_at_the_mouse(book):
    app, transcript = book
    _select(app)

    where = _right_click(app)

    popup = app.canvas.input_view._selection_menu
    assert _menu_open(app)
    assert list(_menu_rows(app)) == ["Play", "Detach"]
    # At the mouse, unless the menu would run off the right or bottom of the
    # screen. Then it sits against that edge instead (see the next test). On a
    # small screen the click can be low enough for that, so the spot is worked
    # out the same way rather than taken to be exactly where the mouse was.
    x = min(where[0], popup.winfo_screenwidth() - popup.winfo_reqwidth())
    y = min(where[1], popup.winfo_screenheight() - popup.winfo_reqheight())
    assert (popup.winfo_rootx(), popup.winfo_rooty()) == (x, y)
    assert _inner(app).tag_ranges("sel"), "the selection is still there"
    assert app.callback_errors == []


def test_a_menu_that_would_run_off_the_screen_is_nudged_back_on(book):
    app, transcript = book
    _select(app)
    _right_click(app)
    box = app.canvas.input_view
    popup = box._selection_menu
    width, height = popup.winfo_reqwidth(), popup.winfo_reqheight()
    screen_w, screen_h = popup.winfo_screenwidth(), popup.winfo_screenheight()

    box._place_selection_menu(popup, screen_w - 3, screen_h - 3)  # the very corner of the screen
    settle(app, 50)
    assert (popup.winfo_rootx(), popup.winfo_rooty()) == (screen_w - width, screen_h - height)

    box._place_selection_menu(popup, -40, -40)  # off the other corner
    settle(app, 50)
    assert (popup.winfo_rootx(), popup.winfo_rooty()) == (0, 0)
    assert app.callback_errors == []


def test_a_right_click_on_spaces_alone_opens_no_menu(book):
    app, transcript = book
    inner = _inner(app)
    inner.tag_add("sel", "1.0 + 2 chars", "1.0 + 3 chars")
    assert inner.get("sel.first", "sel.last") == " "

    _right_click(app)

    assert app.canvas.input_view._selection_menu is None
    assert app.callback_errors == []


def test_choosing_detach_opens_a_window_with_just_the_selected_words(book, tmp_path):
    app, transcript = book
    before = _saved_entry(app, tmp_path, transcript)
    chosen = _select(app, 20, 30)
    _right_click(app)

    _choose(app, "Detach")

    previews = app.canvas._selection_previews
    assert len(previews) == 1
    window, transcript_id, number = previews[0]
    assert (transcript_id, number) == (transcript.id, 1)
    assert window.title() == "Book (1)"
    assert window.input_view.get_text().strip() == chosen
    assert not _menu_open(app), "choosing a row closes the menu"
    assert app.canvas.input_view.get_text().strip() == WORDS, "the transcript's own box is as it was"
    assert app.canvas._input_currently_shown and app.canvas.reader_display.session is None
    assert _saved_entry(app, tmp_path, transcript) == before
    assert app.callback_errors == []


def test_choosing_play_reads_the_selection_in_the_main_window_and_opens_no_window(book):
    app, transcript = book
    _select(app, 20, 30)
    _right_click(app)

    _choose(app, "Play")

    assert app.canvas._selection_previews == []
    assert app.canvas.reader_display.winfo_manager() == "pack"
    assert app.canvas.reader_display.session.total_words == 30
    assert not _menu_open(app)
    assert app.callback_errors == []


def test_escape_closes_the_menu_and_does_nothing_else(book):
    app, transcript = book
    _select(app)
    _right_click(app)
    assert _menu_open(app)

    _press(app, "Escape")

    assert not _menu_open(app)
    assert app.canvas._selection_previews == []
    assert app.canvas.reader_display.session is None
    assert _inner(app).tag_ranges("sel"), "the selection is still there"
    _press(app, "Escape")  # with no menu open it is just an Escape in the edit box
    assert app.canvas._input_currently_shown
    _right_click(app)
    assert _menu_open(app), "and the menu can be opened again"
    assert app.callback_errors == []


def test_escape_is_swallowed_only_while_the_menu_is_open(book):
    app, transcript = book
    box = app.canvas.input_view
    assert box._handle_escape_key(None) is None, "nothing to close: left for other handlers"
    _select(app)
    _right_click(app)
    assert box._handle_escape_key(None) == "break", "the Escape that closes the menu does nothing more"
    assert not _menu_open(app)


@pytest.mark.parametrize("away", [
    pytest.param(lambda app: _inner(app), id="the edit box"),
    pytest.param(lambda app: app.footer._canvas, id="the bottom band"),
])
def test_a_click_elsewhere_in_the_window_closes_the_menu_and_does_nothing_else(book, away):
    app, transcript = book
    _select(app)
    _right_click(app)
    assert _menu_open(app)

    click(away(app))
    settle(app, 100)

    assert not _menu_open(app)
    assert app.canvas._selection_previews == []
    assert app.canvas.reader_display.session is None
    assert app.callback_errors == []


def test_the_menu_is_rebuilt_for_each_new_selection(book):
    app, transcript = book
    _select(app, 0, 10)
    _right_click(app)
    popup = app.canvas.input_view._selection_menu
    _press(app, "Escape")
    second = _select(app, 20, 10)

    _right_click(app)

    assert app.canvas.input_view._selection_menu is popup, "the same small window is reused"
    assert list(_menu_rows(app)) == ["Play", "Detach"]
    assert len(popup.winfo_children()) == 1, "the old rows were cleared out, not piled up"
    _choose(app, "Detach")
    window = app.canvas._selection_previews[-1][0]
    assert window.input_view.get_text().strip() == second, "and the row acts on the new selection"
    assert app.callback_errors == []


def test_each_detached_selection_gets_its_own_number_and_opens_down_and_right_of_the_last(book):
    app, transcript = book
    first, _ = _detach_selection(app, 0, 10, wide=False)
    second, _ = _detach_selection(app, 20, 10, wide=False)
    settle(app, 300)

    assert [window.title() for window, _, _ in app.canvas._selection_previews] == ["Book (1)", "Book (2)"]
    assert second.winfo_rootx() > first.winfo_rootx()
    assert second.winfo_rooty() > first.winfo_rooty()

    _close_with_the_x(app, first)
    third, _ = _detach_selection(app, 40, 10, wide=False)

    assert third.title() == "Book (1)", "a closed window's number is used again"
    assert [window.title() for window, _, _ in app.canvas._selection_previews] == ["Book (2)", "Book (1)"]
    assert app.callback_errors == []


@pytest.mark.parametrize("text", ["", "  \n  "], ids=["empty", "spaces"])
def test_a_blank_selection_opens_nothing(book, text):
    app, transcript = book

    app.canvas.open_selection_preview(text)
    app.canvas.play_selection(text)

    assert app.canvas._selection_previews == []
    assert app.canvas._ephemeral is False
    assert app.canvas.reader_display.session is None


def test_with_no_transcript_open_there_is_nothing_to_detach_or_play(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        assert app.canvas.current_transcript is None

        app.canvas.open_selection_preview("some words to read")
        app.canvas.play_selection("some words to read")

        assert app.canvas._selection_previews == []
        assert app.canvas._ephemeral is False


# ---- the window opens on its edit box ----

def test_it_opens_on_its_own_edit_box_with_the_selected_words_and_the_looks_of_the_moment(preview):
    app, transcript, window, chosen = preview

    assert window.input_view.get_text().strip() == chosen
    assert window.input_view.winfo_manager() == "pack"
    assert window.reader_display.winfo_manager() == "" and window.control_row.winfo_manager() == ""
    assert window.reader_display.session is None, "nothing is reading until it is asked to"
    assert (window.wpm, window.font_size) == (transcript.wpm, transcript.font_size)
    assert (window.font_color, window.highlight_color, window.background_color) == (
        transcript.font_color, transcript.highlight_color, transcript.background_color)
    assert window.skip_word_count == app.canvas._skip_word_count
    assert window.pause_on_skip == app.canvas._pause_on_skip


def test_start_reading_runs_what_is_in_the_box(book):
    app, transcript = book
    app.store.set_transcript_wpm(transcript.id, 450)
    window, chosen = _detach_selection(app)

    _start(window, paused=False)

    assert window.reader_display.winfo_manager() == "pack" and window.control_row.winfo_manager() == "pack"
    assert window.input_view.winfo_manager() == ""
    session = window.reader_display.session
    assert session.total_words == 60 and session.wpm == 450
    assert window.scrub_bar.readout.cget("text").endswith("of 60")
    assert _pause_label(window) == RUNNING
    _read_on_until(window, _index(window) + 1)
    click_button(window.toolbar.pause_button)
    settle(window, 60)
    assert _shown(window) == WORD_LIST[_index(window)], "the word on screen is the one it has got to"
    assert window.scrub_bar.slider.get() == _index(window), "the scrubber followed the reading"
    assert app.callback_errors == []


def test_start_reading_reads_the_text_as_it_is_now_not_as_it_opened(preview):
    app, transcript, window, chosen = preview
    inner = window.input_view.textbox._textbox
    inner.delete("1.0", "end")
    inner.insert("1.0", "alpha beta gamma delta")

    _start(window)

    assert window.reader_display.session.total_words == 4
    assert _shown(window) == ["alpha", "beta", "gamma", "delta"][_index(window)]


@pytest.mark.parametrize("typed", ["", "  \n\t "], ids=["empty", "spaces"])
def test_start_reading_on_a_box_with_nothing_to_read_does_nothing(preview, typed):
    app, transcript, window, chosen = preview
    inner = window.input_view.textbox._textbox
    inner.delete("1.0", "end")
    inner.insert("1.0", typed)

    click_button(window.input_view.start_button)
    settle(window, 300)

    assert window.reader_display.session is None
    assert window.input_view.winfo_manager() == "pack"
    assert window.reader_display.winfo_manager() == "" and window.control_row.winfo_manager() == ""
    assert app.callback_errors == []


# ---- the keys ----

def test_every_reading_key_reaches_its_action(preview, monkeypatch):
    app, transcript, window, chosen = preview
    centred = []
    monkeypatch.setattr(window.reader_display, "center_pan", lambda: centred.append(True))
    _start(window, paused=False)
    assert _pause_label(window) == RUNNING

    _press(window, "space")
    assert _pause_label(window) == PAUSED
    _press(window, "space")
    assert _pause_label(window) == RUNNING
    _press(window, "space")
    assert _pause_label(window) == PAUSED

    start = _index(window)
    step = window.skip_word_count
    _press(window, "Right")
    assert _index(window) == start + step
    _press(window, "Left")
    assert _index(window) == start

    for key in ("r", "R"):
        _press(window, "Right")
        assert _index(window) > start
        _press(window, key)
        assert _pause_label(window) == RUNNING, key
        assert _index(window) <= 1, f"{key} should start again from the first word"
        _press(window, "space")
        assert _pause_label(window) == PAUSED

    for key in ("c", "C"):
        before = len(centred)
        _press(window, key)
        assert len(centred) == before + 1, key

    _press(window, "Escape")
    assert window.input_view.winfo_manager() == "pack", "Esc is Stop: back to the edit box"
    assert window.reader_display.winfo_manager() == ""
    assert app.callback_errors == []


def test_the_keys_are_just_typing_while_the_edit_box_has_the_keyboard(preview, monkeypatch):
    app, transcript, window, chosen = preview
    centred = []
    monkeypatch.setattr(window.reader_display, "center_pan", lambda: centred.append(True))
    inner = window.input_view.textbox._textbox
    inner.focus_force()
    settle(window, 100)

    for key in ("r", "R", "c", "C", "space", "Left", "Right", "Escape"):
        _press(window, key)

    assert "rRcC " in window.input_view.get_text(), "the letters and the space were typed"
    assert window.reader_display.session is None and centred == []
    assert window.input_view.winfo_manager() == "pack"
    assert app.callback_errors == []


def test_the_keys_still_work_when_no_widget_reports_having_the_keyboard(preview, monkeypatch):
    app, transcript, window, chosen = preview
    _start(window, paused=False)
    monkeypatch.setattr(window, "focus_get", lambda: None)

    _press(window, "space")

    assert _pause_label(window) == PAUSED, "with no text box to type in, nothing holds the keys back"
    assert app.callback_errors == []


def test_the_keys_work_straight_after_start_reading_was_clicked_from_the_edit_box(preview):
    app, transcript, window, chosen = preview
    window.input_view.textbox._textbox.focus_force()  # the keyboard was in the box, as it is after typing there
    settle(window, 100)

    click_button(window.input_view.start_button)
    settle(window, 300)
    assert _pause_label(window) == RUNNING
    _press(window, "space")

    assert _pause_label(window) == PAUSED, "the keyboard moved off the hidden box, so the space paused"
    assert app.callback_errors == []


def test_esc_stops_the_reading_and_brings_back_the_edit_box_with_its_text(preview):
    app, transcript, window, chosen = preview
    _start(window, paused=False)
    _press(window, "Right")
    text = window.input_view.get_text()

    _press(window, "Escape")

    assert window.reader_display.session is None
    assert window.input_view.winfo_manager() == "pack"
    assert window.reader_display.winfo_manager() == "" and window.control_row.winfo_manager() == ""
    assert window.input_view.get_text() == text
    assert window.focus_get() is window.input_view.textbox._textbox, "typing goes to the box again"
    settle(window, 600)  # a leftover timer from the stopped reading would go off now
    _start(window)
    assert _index(window) <= 3, "starting again starts from the first word"
    assert app.callback_errors == []


# ---- the buttons ----

def test_the_pause_button_starts_and_stops_the_reading(preview):
    app, transcript, window, chosen = preview
    _start(window, paused=False)

    click_button(window.toolbar.pause_button)
    settle(window, 60)
    assert _pause_label(window) == PAUSED
    standing = _index(window)
    settle(window, 700)
    assert _index(window) == standing, "paused means paused"

    click_button(window.toolbar.pause_button)
    settle(window, 60)
    assert _pause_label(window) == RUNNING
    _read_on_until(window, standing + 1)
    assert app.callback_errors == []


def test_the_skip_buttons_move_by_the_skip_setting(book):
    app, transcript = book
    app.canvas.set_skip_word_count(15)
    window, _ = _detach_selection(app)
    _start(window)
    start = _index(window)

    click_button(window.toolbar.skip_forward_button)
    settle(window, 60)
    assert _index(window) == start + 15
    assert window.scrub_bar.slider.get() == start + 15

    click_button(window.toolbar.skip_back_button)
    settle(window, 60)
    assert _index(window) == start
    assert app.callback_errors == []


@pytest.mark.parametrize("pause_on_skip", [True, False])
def test_pause_on_skip_decides_whether_a_skip_leaves_the_reading_paused(book, pause_on_skip):
    app, transcript = book
    app.canvas.set_pause_on_skip(pause_on_skip)
    window, _ = _detach_selection(app)
    _start(window, paused=False)
    assert _pause_label(window) == RUNNING

    click_button(window.toolbar.skip_forward_button)
    settle(window, 60)

    assert (_pause_label(window) == PAUSED) is pause_on_skip
    assert app.callback_errors == []


def test_settings_changed_after_the_window_opened_do_not_reach_it(preview):
    app, transcript, window, chosen = preview
    step = window.skip_word_count
    app.canvas.set_skip_word_count(step + 15)
    app.canvas.set_pause_on_skip(True)
    app.store.set_transcript_wpm(transcript.id, 700)
    _start(window, paused=False)
    start = _index(window)

    click_button(window.toolbar.skip_forward_button)
    settle(window, 60)

    assert _index(window) >= start + step
    assert _index(window) < start + step + 15, "it skipped by the count it was opened with"
    assert _pause_label(window) == RUNNING, "and the reading was not paused by the new setting"
    assert window.reader_display.session.wpm == 300, "at the speed it was opened with"
    assert app.callback_errors == []


def test_the_restart_button_starts_again_from_the_first_word(preview):
    app, transcript, window, chosen = preview
    _start(window)
    click_button(window.toolbar.skip_forward_button)
    settle(window, 60)
    assert _index(window) >= window.skip_word_count

    click_button(window.toolbar.restart_button)
    settle(window, 60)

    assert _index(window) <= 1
    assert _pause_label(window) == RUNNING
    assert app.callback_errors == []


def test_the_readouts_follow_the_reading(preview):
    app, transcript, window, chosen = preview
    _start(window)
    percent = _percent(window)
    remaining = window.toolbar.time_readout.cget("text")

    click_button(window.toolbar.skip_forward_button)
    settle(window, 60)

    assert _percent(window) > percent
    assert window.toolbar.time_readout.cget("text") != remaining
    click_button(window.toolbar.restart_button)
    settle(window, 60)
    assert _percent(window) <= 5, "and back to the start after Restart"


@pytest.mark.parametrize("pause_after_scrubbing", [True, False])
def test_dragging_the_scrubber_moves_the_reading_and_letting_go_follows_the_setting(book, pause_after_scrubbing):
    app, transcript = book
    app.canvas.set_scrub_pause(pause_after_scrubbing)
    window, _ = _detach_selection(app)
    _start(window, paused=False)
    slider = window.scrub_bar.slider
    middle = slider.winfo_width() // 2
    height = slider.winfo_height() // 2

    slider._canvas.event_generate("<Button-1>", x=middle, y=height)
    slider._canvas.event_generate("<B1-Motion>", x=middle, y=height)
    settle(window, 60)

    assert 26 <= _index(window) <= 33, "the reading went to about the middle of the 60 words"
    assert window.scrub_bar.readout.cget("text") == f"word {_index(window) + 1} of 60"
    assert _pause_label(window) == PAUSED, "held still while the thumb is down"
    landed = _index(window)

    slider._canvas.event_generate("<ButtonRelease-1>", x=middle, y=height)
    settle(window, 60)

    assert (_pause_label(window) == PAUSED) is pause_after_scrubbing
    assert _index(window) >= landed
    assert app.callback_errors == []


# ---- the window is independent ----

def test_nothing_done_in_the_window_reaches_the_transcript(preview, tmp_path):
    app, transcript, window, chosen = preview
    watched = ("position", "is_paused", "is_stopped", "wpm", "raw_text", "draft_text", "times_read",
               "total_words_read", "total_time_spent_seconds")
    before = {name: getattr(transcript, name) for name in watched}
    before["bookmarks"] = list(transcript.bookmarks)
    saved_before = _saved_entry(app, tmp_path, transcript)

    _start(window, paused=False)
    _press(window, "space")
    _press(window, "Right")
    click_button(window.toolbar.skip_forward_button)
    click_button(window.toolbar.restart_button)
    settle(window, 800)
    for key in ("b", "B", "Up", "Down", "f", "F"):  # the main window's keys, which this one doesn't have
        _press(window, key)
    _press(window, "Escape")
    inner = window.input_view.textbox._textbox
    inner.insert("end", " one more")
    _start(window, paused=False)
    settle(window, 500)
    _close_with_the_x(app, window)

    after = {name: getattr(transcript, name) for name in watched}
    after["bookmarks"] = list(transcript.bookmarks)
    assert after == before
    assert _saved_entry(app, tmp_path, transcript) == saved_before
    assert app.canvas.input_view.get_text().strip() == WORDS
    assert app.canvas._input_currently_shown and app.canvas.reader_display.session is None
    assert app.footer.wpm_slider.get() == transcript.wpm
    assert app.callback_errors == []


def test_closing_the_window_forgets_it_and_stops_its_reading(preview):
    app, transcript, window, chosen = preview
    _start(window, paused=False)
    reader = window.reader_display

    _close_with_the_x(app, window)

    assert app.canvas._selection_previews == []
    assert not window.winfo_exists()
    assert reader.session is None, "its reader was stopped, not left with a timer running"
    settle(app, 600)  # a leftover timer from the reading would go off now
    assert app.canvas.input_view.get_text().strip() == WORDS
    assert app.callback_errors == []


def test_two_windows_each_have_their_own_keyboard_and_reading(book):
    app, transcript = book
    first, _ = _detach_selection(app, 0, 60)
    second, _ = _detach_selection(app, 100, 60)
    _start(first, paused=False)
    _start(second, paused=False)

    _give_keyboard(first)
    _press(first, "space")
    assert _pause_label(first) == PAUSED
    assert _pause_label(second) == RUNNING, "the other one went on"
    standing = _index(first)

    _give_keyboard(second)
    _press(second, "Right")
    settle(second, 60)
    assert _index(first) == standing, "a key in one doesn't move the other"
    assert _index(second) >= second.skip_word_count
    assert app.callback_errors == []


def test_closing_the_app_while_the_window_reads_saves_nothing_from_it(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _add_book(app)
        app._handle_open_transcript(transcript)
        settle(app, 300)
        window, _ = _detach_selection(app)
        _start(window, paused=False)
        settle(window, 900)

        app._handle_close()

        saved = TranscriptStore(data_directory=str(tmp_path)).transcripts
        assert saved[0].total_words_read == 0
        assert saved[0].times_read == 0
        assert saved[0].position == 0
