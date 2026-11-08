"""A selection detached into its own window reads the way its transcript is set
to read, with the words grouped when chunking is on.

The window used to build its reader without any of the transcript's chunking
settings, so with chunking on, right-click Play flashed the selection in groups
while right-click Detach flashed it one word at a time. Everything here goes
through the real menu: select words, right-click, choose Detach, click Start
reading, then look at what the reader is showing.

Like the other settings, chunking is a snapshot taken when the window opens, so
turning it on or off afterwards does not reach a window that is already open.
"""
import pytest

from tk_helpers import click_button, settle

WORD_LIST = [f"w{number}" for number in range(60)]
WORDS = " ".join(WORD_LIST)


@pytest.fixture
def book(tmp_path, open_real_app):
    """A stopped transcript, open in the main window's edit box. Its speed is
    60 a minute so the reading hardly moves while a test looks at it."""
    with open_real_app(tmp_path) as app:
        transcript = app.store.add_transcript("Book", app.store.current_space, wpm=60)
        app.store.set_transcript_text(transcript.id, WORDS)
        app.store.set_transcript_stopped(transcript.id, True)
        app._refresh_transcript_list()
        settle(app, 200)
        yield app, transcript


def _open(app, transcript):
    app._handle_open_transcript(transcript)
    settle(app, 300)


def _detach_everything(app):
    """Select all the words, right-click, choose Detach. Returns the window."""
    inner = app.canvas.input_view.textbox._textbox
    inner.tag_add("sel", "1.0", "end - 1 chars")
    inner.focus_force()
    settle(app, 100)
    x, y = inner.bbox("sel.first")[:2]
    x, y = x + 1, y + 1
    inner.event_generate("<Button-3>", x=x, y=y, rootx=inner.winfo_rootx() + x, rooty=inner.winfo_rooty() + y)
    settle(app, 150)
    popup = app.canvas.input_view._selection_menu
    rows = {row.cget("text"): row for row in popup.winfo_children()[0].winfo_children()}
    rows["Detach"].event_generate("<Button-1>")
    settle(app, 500)
    return app.canvas._selection_previews[-1][0]


def _start_and_pause(window):
    click_button(window.input_view.start_button)
    settle(window, 300)
    window.focus_force()
    settle(window, 100)
    (window.focus_get() or window).event_generate("<space>")
    settle(window, 100)


def _shown(window):
    reader = window.reader_display
    return "".join(label.cget("text") for label in (reader.before_label, reader.focus_label, reader.after_label))


def test_with_chunking_on_the_selection_is_read_in_groups(book):
    app, transcript = book
    app.store.set_transcript_chunking(transcript.id, True, 3)
    _open(app, transcript)
    window = _detach_everything(app)

    _start_and_pause(window)

    session = window.reader_display.session
    assert (session.chunking_enabled, session.chunk_size, session.chunk_mode) == (True, 3, "fixed")
    index = session.index
    assert index % 3 == 0, "the reading is paused at the start of a group"
    assert _shown(window) == " ".join(WORD_LIST[index:index + 3])


def test_with_chunking_off_the_selection_is_read_a_word_at_a_time(book):
    app, transcript = book
    _open(app, transcript)
    window = _detach_everything(app)

    _start_and_pause(window)

    session = window.reader_display.session
    assert session.chunking_enabled is False
    assert _shown(window) == WORD_LIST[session.index]


def test_the_adaptive_mode_and_its_settings_are_passed_on_too(book):
    app, transcript = book
    app.store.set_transcript_chunking(transcript.id, True, 4, "adaptive", 18)
    _open(app, transcript)
    window = _detach_everything(app)

    _start_and_pause(window)

    session = window.reader_display.session
    assert (session.chunking_enabled, session.chunk_size, session.chunk_mode, session.chunk_char_target) == (
        True, 4, "adaptive", 18)


def test_a_change_made_after_the_window_opened_does_not_reach_it(book):
    app, transcript = book
    _open(app, transcript)
    window = _detach_everything(app)
    app.store.set_transcript_chunking(transcript.id, True, 3)

    _start_and_pause(window)

    session = window.reader_display.session
    assert session.chunking_enabled is False, "it keeps the chunking it was opened with"
    assert _shown(window) == WORD_LIST[session.index]
