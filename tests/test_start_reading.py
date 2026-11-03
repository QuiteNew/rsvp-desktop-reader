"""Tests for the edit box's Start reading button, in the main window and in the
detached one (gui/components/canvas.py, _handle_text_submitted() and
_handle_detached_text_submitted(), detached_window.py, _handle_text_submitted(),
and gui/app.py, _handle_text_submitted()).

Start reading saves what's in the box as the transcript's text, clears its
draft and its stopped state, and opens the reader on it. Three things here used
to go wrong, and are fixed with these tests:

  - The text was saved exactly as Tk hands it back, with a newline added at the
    end, so every Start reading and Stop left one more blank line at the end of
    the text.
  - Loading the reader saved the edit box again, the way every switch does,
    after the draft had been cleared, so the whole text went straight back into
    the draft and every transcript started was saved twice.
  - Start reading in the detached window reloaded the main window with that
    transcript, even while a different one was open there. The main window
    dropped it, while the header and the sidebar still named it.

Each test builds the real app with open_real_app (conftest.py) and presses the
real button with invoke()."""

import json

from tk_helpers import settle

WORDS = [f"w{i}" for i in range(40)]
TEXT = " ".join(WORDS)


def _draft(app, title="A", text=TEXT):
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    store.set_transcript_draft_text(transcript.id, text)
    return transcript


def _stopped(app, title="A"):
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    store.set_transcript_text(transcript.id, TEXT)
    store.set_transcript_stopped(transcript.id, True)
    return transcript


def _paused(app, title="B"):
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    store.set_transcript_text(transcript.id, "one two three four five six")
    store.set_transcript_paused(transcript.id, True)
    return transcript


def _open(app, transcript):
    app._refresh_transcript_list()
    settle(app, 200)
    app._handle_open_transcript(transcript)
    settle(app, 300)


def _start(view):
    """Press Start reading on an edit box, the main one or the detached one."""
    view.input_view.start_button.invoke()


def _shown(reader):
    return "".join(label.cget("text") for label in (reader.before_label, reader.focus_label, reader.after_label))


def _saved(app, data_dir, transcript):
    app.store.flush()
    saved = json.loads((data_dir / "data.json").read_text(encoding="utf-8"))
    entry = next(t for t in saved["transcripts"] if t["id"] == transcript.id)
    return {key: entry[key] for key in ("raw_text", "draft_text", "is_stopped")}


def _detach(app):
    app.canvas._handle_detach()
    settle(app, 600)
    return app.canvas._detached_window


# ---- the main window ----

def test_starting_a_draft_reads_it_and_saves_it_as_the_text(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _draft(app)
        _open(app, a)
        canvas = app.canvas

        _start(canvas)

        assert not canvas._input_currently_shown
        assert canvas.reader_display.session.total_words == 40
        assert _shown(canvas.reader_display) == "w0"
        settle(app, 300)
        assert _saved(app, tmp_path, a) == {"raw_text": TEXT, "draft_text": "", "is_stopped": False}


def test_starting_a_stopped_transcript_reads_the_edit_in_the_box(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        canvas = app.canvas
        canvas.input_view.set_text(TEXT + " w40 w41")

        _start(canvas)

        assert canvas.reader_display.session.total_words == 42
        settle(app, 300)
        assert _saved(app, tmp_path, a) == {"raw_text": TEXT + " w40 w41", "draft_text": "", "is_stopped": False}


def test_the_text_is_saved_once_not_also_as_the_draft(tmp_path, open_real_app):
    """Leaving the transcript afterwards doesn't bring the copy back either."""
    with open_real_app(tmp_path) as app:
        a = _draft(app)
        b = _paused(app)
        _open(app, a)

        _start(app.canvas)
        settle(app, 300)
        assert a.draft_text == ""

        _open(app, b)
        assert _saved(app, tmp_path, a)["draft_text"] == ""


def test_the_text_is_saved_without_the_space_around_it(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _draft(app)
        _open(app, a)
        app.canvas.input_view.set_text("\n\n   " + TEXT + "   \n\n")

        _start(app.canvas)
        settle(app, 300)

        assert a.raw_text == TEXT


def test_starting_and_stopping_again_and_again_keeps_the_text_as_it_was(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _draft(app)
        _open(app, a)
        canvas = app.canvas

        for _ in range(3):
            _start(canvas)
            settle(app, 200)
            canvas.stop()
            settle(app, 200)

        assert a.raw_text == TEXT
        assert canvas.input_view.get_text().rstrip("\n") == TEXT
        assert canvas.input_view.get_text() == TEXT + "\n", "blank lines piled up at the end"


def test_starting_with_an_empty_box_stays_in_the_box(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _draft(app, text="")
        _open(app, a)
        canvas = app.canvas

        _start(canvas)
        settle(app, 300)

        assert canvas._input_currently_shown
        assert canvas.reader_display.session is None
        assert _saved(app, tmp_path, a) == {"raw_text": "", "draft_text": "", "is_stopped": False}


# ---- the detached window ----

def test_starting_in_the_detached_window_reads_there(tmp_path, open_real_app):
    """The main window keeps showing that the transcript is off in the
    detached window."""
    with open_real_app(tmp_path) as app:
        a = _draft(app)
        _open(app, a)
        window = _detach(app)

        _start(window)
        settle(app, 300)

        assert window.reader_display.session is not None
        assert window.reader_display.session.total_words == 40
        assert app.canvas.detached_placeholder.winfo_manager() == "pack"
        assert app.canvas.reader_display.session is None
        assert _saved(app, tmp_path, a) == {"raw_text": TEXT, "draft_text": "", "is_stopped": False}


def test_starting_in_the_detached_window_leaves_the_one_open_here_alone(tmp_path, open_real_app):
    """A is detached with its edit box, and B is open in the main window. Start
    reading in A's window reads A there, and the main window goes on reading
    B, with the same session, and with its keys still for B."""
    with open_real_app(tmp_path) as app:
        a = _draft(app)
        b = _paused(app)
        _open(app, a)
        window = _detach(app)
        _open(app, b)
        canvas = app.canvas
        session_b = canvas.reader_display.session

        _start(window)
        settle(app, 300)

        assert window.reader_display.session is not None
        assert canvas.current_transcript is b
        assert canvas.reader_display.session is session_b
        assert canvas.detached_placeholder.winfo_manager() == ""
        assert app.header._full_title == "B"

        a_was_paused = a.is_paused
        canvas.toggle_pause()
        assert b.is_paused is False, "Space in the main window didn't reach B"
        assert a.is_paused == a_was_paused