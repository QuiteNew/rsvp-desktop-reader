"""The detached window's own controls, used the way a person uses them: the reading
keys, the buttons above the reader, Esc to stop, and closing the app while the
window is reading (gui/components/detached_window.py).

The window is its own top-level window with its own key bindings and its own
buttons, wired to its own reader. Tests of the main window's keys and buttons
(test_main_window_controls.py) can't show that these work too. And other tests
that reach the detached window call its methods straight away, which proves what
a method does but not that a key is bound to it or a button wired to it. Here
the keys are sent as key presses and the buttons are clicked, in a real app,
and each time the test looks at the reader on screen, at the toolbar, and at
what was saved for the transcript.

The Up and Down keys change the speed by 10. Their size and limits have their
own tests (test_wpm_keys.py); here they only need to be bound.
"""
import pytest

from core.transcript_store import TranscriptStore
from gui.components.bookmarks_popover import BookmarksPopover
from tk_helpers import click_button, settle

WORDS = " ".join(f"w{number}" for number in range(400))
PAUSED = "▶"
RUNNING = "⏸"


# ---- helpers ----

def _add(app, title="Book", text=WORDS, paused=True):
    transcript = app.store.add_transcript(title, app.store.current_space, wpm=300)
    app.store.set_transcript_text(transcript.id, text)
    app.store.set_transcript_paused(transcript.id, paused)
    app._refresh_transcript_list()
    settle(app, 200)
    return transcript


def _give_keyboard(window):
    """Put the keyboard on the window itself, as a person clicking into it would."""
    window.focus_force()
    settle(window, 100)


def _detach(app, transcript):
    """Open the transcript in the main window and detach it with the button
    above the reader. Returns the window, widened and with the keyboard on it.

    The window is made wider because it opens 500 pixels wide, and the buttons
    above the reader need about 610: at 500 the restart and bookmark buttons
    have no room and aren't shown at all, and the pause button is squeezed to
    a sliver. A person has to drag the window wider to reach them, and so do
    the tests."""
    app._handle_open_transcript(transcript)
    settle(app, 300)
    click_button(app.canvas.toolbar.detach_button)
    settle(app, 700)
    window = app.canvas._detached_window
    assert window is not None
    # Tk prints an error raised inside a key or button handler and carries on, so
    # without this a handler that fell over would not fail a test.
    app.callback_errors = []
    app.report_callback_exception = lambda *details: app.callback_errors.append(details)
    window.geometry("700x350")
    settle(window, 300)
    _give_keyboard(window)
    return window


@pytest.fixture
def detached(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _add(app)
        window = _detach(app, transcript)
        yield app, transcript, window


def _press(window, key):
    """Send a key to the widget that has the keyboard, or the window if none
    has, the way a real key press arrives."""
    (window.focus_get() or window).event_generate(f"<{key}>")
    settle(window, 60)


def _index(window):
    return window.reader_display.session.index


def _pause_label(window):
    return window.toolbar.pause_button.cget("text")


# ---- the keys ----

def test_every_reading_key_reaches_its_action(detached, monkeypatch):
    app, transcript, window = detached
    assert transcript.is_paused and _pause_label(window) == PAUSED
    centred = []
    monkeypatch.setattr(window.reader_display, "center_pan", lambda: centred.append(True))

    _press(window, "space")
    assert transcript.is_paused is False and _pause_label(window) == RUNNING
    _press(window, "space")
    assert transcript.is_paused is True and _pause_label(window) == PAUSED

    start = _index(window)
    step = window.skip_word_count
    _press(window, "Right")
    assert _index(window) == start + step
    assert transcript.position == start + step, "the place is saved"
    assert window.scrub_bar.slider.get() == start + step, "and the scrubber follows"
    _press(window, "Left")
    assert _index(window) == start
    assert transcript.position == start

    wpm = transcript.wpm
    _press(window, "Up")
    assert transcript.wpm == wpm + 10
    assert window.reader_display.session.wpm == wpm + 10
    _press(window, "Down")
    assert transcript.wpm == wpm

    for key in ("b", "B"):
        _press(window, key)
        assert [b.index for b in transcript.bookmarks] == [start], key
        assert window.scrub_bar._bookmark_indices == [start], "the scrubber shows the tick"
        _press(window, key)
        assert transcript.bookmarks == [], key
        assert window.scrub_bar._bookmark_indices == []

    for key in ("r", "R"):
        _press(window, "Right")
        assert _index(window) > start
        _press(window, key)
        assert transcript.is_paused is False, key
        assert _pause_label(window) == RUNNING
        assert _index(window) <= 1, f"{key} should start again from the first word"
        assert transcript.position <= 1
        _press(window, "space")
        assert transcript.is_paused is True

    for key in ("c", "C"):
        before = len(centred)
        _press(window, key)
        assert len(centred) == before + 1, key

    assert transcript.is_stopped is False
    _press(window, "Escape")
    assert transcript.is_stopped is True
    assert window.input_view.winfo_manager() != "", "Esc is Stop: back to the edit box"
    assert window.reader_display.winfo_manager() == ""
    assert app.callback_errors == []


def test_the_keys_move_this_windows_transcript_while_another_is_open_in_the_main_window(detached):
    app, transcript, window = detached
    other = _add(app, "Other", " ".join(f"o{number}" for number in range(400)))
    app._handle_open_transcript(other)
    settle(app, 300)
    _give_keyboard(window)
    other_before = (other.position, other.is_paused, other.wpm, other.bookmarks)
    start = _index(window)

    _press(window, "Right")
    _press(window, "Up")
    _press(window, "b")
    _press(window, "space")

    assert transcript.position == start + window.skip_word_count
    assert transcript.wpm == 310 and transcript.is_paused is False
    assert [b.index for b in transcript.bookmarks] == [transcript.position]
    assert (other.position, other.is_paused, other.wpm, other.bookmarks) == other_before
    assert app.canvas.reader_display.session.index == 0
    assert app.footer.wpm_slider.get() == other.wpm, "the footer belongs to the transcript open in the main window"
    _press(window, "space")


ALL_KEYS = ("space", "r", "R", "b", "B", "c", "C", "Left", "Right", "Up", "Down", "Escape")


def test_the_keys_are_just_typing_while_the_edit_box_has_the_keyboard(tmp_path, open_real_app, monkeypatch):
    with open_real_app(tmp_path) as app:
        transcript = _add(app, paused=True)
        app.store.set_transcript_stopped(transcript.id, True)
        window = _detach(app, transcript)
        centred = []
        monkeypatch.setattr(window.reader_display, "center_pan", lambda: centred.append(True))
        inner = window.input_view.textbox._textbox
        inner.focus_force()
        settle(window, 100)
        assert window.focus_get() is inner

        def everything():
            return (transcript.is_paused, transcript.wpm, len(transcript.bookmarks), transcript.is_stopped,
                    transcript.position, len(centred), window.input_view.winfo_manager())

        before = everything()
        for key in ALL_KEYS:
            _press(window, key)
            assert everything() == before, key

        assert window.get_draft_text().strip().endswith("rRbBcC"), "the letters went into the box"
        assert app.callback_errors == []


def test_with_nothing_started_the_keys_have_nothing_to_act_on(tmp_path, open_real_app):
    """A transcript that was never started has no reader. The keys must leave it
    be, and Esc must not wipe the text typed so far (it would have, as Stop
    puts back the saved text, which is empty)."""
    with open_real_app(tmp_path) as app:
        transcript = app.store.add_transcript("Draft", app.store.current_space, wpm=300)
        app.store.set_transcript_draft_text(transcript.id, "my notes so far")
        app._refresh_transcript_list()
        settle(app, 200)
        window = _detach(app, transcript)
        assert window.get_draft_text().strip() == "my notes so far"
        assert window.focus_get() is window, "the keyboard is on the window, not in the box"
        before = (transcript.is_paused, transcript.is_stopped, transcript.position, transcript.bookmarks)

        for key in ("space", "Left", "Right", "r", "b", "c", "Escape"):
            _press(window, key)

        assert (transcript.is_paused, transcript.is_stopped, transcript.position, transcript.bookmarks) == before
        assert window.get_draft_text().strip() == "my notes so far"
        assert window.input_view.winfo_manager() != ""
        assert window._bookmarks_popover is None
        assert app.callback_errors == [], "a key fell over for want of a reader"


# ---- the buttons above the reader ----

def test_the_pause_button_starts_and_stops_the_reading(detached):
    app, transcript, window = detached

    click_button(window.toolbar.pause_button)
    settle(window, 60)
    assert transcript.is_paused is False and _pause_label(window) == RUNNING
    assert window.reader_display._is_paused is False
    click_button(window.toolbar.pause_button)
    settle(window, 60)
    assert transcript.is_paused is True and _pause_label(window) == PAUSED
    assert window.reader_display._is_paused is True


def test_the_skip_buttons_move_by_the_skip_setting_and_save_the_place(detached):
    app, transcript, window = detached
    step = window.skip_word_count
    toolbar = window.toolbar

    click_button(toolbar.skip_forward_button)
    settle(window, 60)
    assert _index(window) == step and transcript.position == step
    assert window.scrub_bar.slider.get() == step
    click_button(toolbar.skip_forward_button)
    settle(window, 60)
    assert _index(window) == 2 * step
    click_button(toolbar.skip_back_button)
    settle(window, 60)
    assert _index(window) == step and transcript.position == step
    assert transcript.is_paused is True, "skipping on its own doesn't start the reading"


def test_the_skip_buttons_follow_the_skip_setting_while_the_window_is_open(detached):
    app, transcript, window = detached

    app.canvas.set_skip_word_count(25)
    click_button(window.toolbar.skip_forward_button)
    settle(window, 60)
    assert _index(window) == 25 and transcript.position == 25
    _press(window, "Right")
    assert _index(window) == 50, "the keys use the same setting"
    click_button(window.toolbar.skip_back_button)
    settle(window, 60)
    assert _index(window) == 25


def test_a_window_opened_after_the_settings_changed_starts_with_them(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _add(app)
        app.canvas.set_skip_word_count(25)
        app.canvas.set_pause_on_skip(True)
        window = _detach(app, transcript)
        assert window.skip_word_count == 25 and window.pause_on_skip is True

        click_button(window.toolbar.pause_button)
        settle(window, 60)
        click_button(window.toolbar.skip_forward_button)
        settle(window, 60)

        assert _index(window) == 25
        assert transcript.is_paused is True


@pytest.mark.parametrize("pause_on_skip", [True, False], ids=["on", "off"])
def test_pause_on_skip_decides_whether_a_skip_leaves_the_reading_paused(detached, pause_on_skip):
    app, transcript, window = detached
    app.canvas.set_pause_on_skip(pause_on_skip)
    click_button(window.toolbar.pause_button)
    settle(window, 60)
    assert transcript.is_paused is False

    click_button(window.toolbar.skip_forward_button)
    settle(window, 60)

    assert transcript.is_paused is pause_on_skip
    assert window.reader_display._is_paused is pause_on_skip
    assert _pause_label(window) == (PAUSED if pause_on_skip else RUNNING)
    click_button(window.toolbar.pause_button)  # leaves it paused whichever way it was
    settle(window, 60)


def test_the_restart_button_starts_again_from_the_first_word(detached):
    app, transcript, window = detached
    _press(window, "Right")
    _press(window, "Right")
    assert _index(window) == 2 * window.skip_word_count

    click_button(window.toolbar.restart_button)
    settle(window, 60)

    assert _index(window) <= 1
    assert transcript.position <= 1
    assert transcript.is_paused is False and _pause_label(window) == RUNNING
    click_button(window.toolbar.pause_button)
    settle(window, 60)


def test_the_readouts_follow_the_reading(detached):
    app, transcript, window = detached
    toolbar = window.toolbar
    percent_at_start = toolbar.percent_readout.cget("text")
    time_at_start = toolbar.time_readout.cget("text")
    assert percent_at_start.endswith("%")

    for _ in range(5):
        click_button(toolbar.skip_forward_button)
        settle(window, 40)

    assert int(toolbar.percent_readout.cget("text")[:-1]) > int(percent_at_start[:-1])
    assert toolbar.time_readout.cget("text") != time_at_start, "less time is left"
    click_button(toolbar.restart_button)
    settle(window, 60)
    click_button(toolbar.pause_button)
    settle(window, 60)


def test_the_bookmarks_button_opens_one_popover_that_belongs_to_this_window(detached):
    app, transcript, window = detached
    assert window._bookmarks_popover is None

    click_button(window.toolbar.bookmark_button)
    settle(window, 300)
    popover = window._bookmarks_popover
    assert isinstance(popover, BookmarksPopover)
    assert popover.master is window
    assert app.canvas._bookmarks_popover is None, "not the main window's"

    click_button(window.toolbar.bookmark_button)
    settle(window, 300)
    assert window._bookmarks_popover is popover, "pressing again brings the same one forward"
    assert [w for w in window.winfo_children() if isinstance(w, BookmarksPopover)] == [popover]


# ---- Esc, and closing ----

def test_esc_stops_the_reading_and_shows_the_edit_box(detached):
    app, transcript, window = detached
    click_button(window.toolbar.pause_button)  # reading, so there are words to count
    settle(window, 700)
    _press(window, "Right")
    click_button(window.toolbar.pause_button)
    settle(window, 60)
    assert transcript.is_paused is True, "paused when it is stopped, so that a leftover pause would show"
    click_button(window.toolbar.bookmark_button)
    settle(window, 300)
    popover = window._bookmarks_popover
    assert popover is not None
    assert transcript.total_words_read == 0
    _give_keyboard(window)

    _press(window, "Escape")

    assert transcript.is_stopped is True
    assert transcript.position == 0 and transcript.is_paused is False
    assert window.reader_display.session is None
    assert window.input_view.winfo_manager() != ""
    assert window.reader_display.winfo_manager() == "" and window.control_row.winfo_manager() == ""
    assert window.get_draft_text().strip() == WORDS
    assert window._bookmarks_popover is None
    assert not popover.winfo_exists(), "its bookmarks list went with the reading"
    assert transcript.total_words_read > 0, "what was read before stopping is counted"


def test_closing_the_app_while_the_window_is_reading_keeps_what_was_read(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _add(app)
        window = _detach(app, transcript)
        click_button(window.toolbar.pause_button)
        settle(window, 900)
        assert transcript.total_words_read == 0, "reported when the reading ends, not before"

        app._handle_close()

        saved = TranscriptStore(data_directory=str(tmp_path)).transcripts
        assert saved[0].total_words_read > 0
