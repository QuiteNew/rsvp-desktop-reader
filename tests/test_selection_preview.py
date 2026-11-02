"""Tests for reading just a selection: select some text in the edit box,
right-click it and choose Play (gui/components/canvas.py, play_selection(),
_stop_ephemeral(), and the _ephemeral checks in the handlers that save).

The user guide promises that selection reading "never changes the transcript's
saved text, position, or stats". So whatever is done during a preview (letting
it run, pausing, skipping, dragging the progress bar, restarting, letting it
reach the end, stopping it, or leaving it by opening another transcript,
detaching or closing the app), the transcript keeps its saved position, pause,
stopped state, text and stats. Bookmarks can't be added to a preview, and Stop
brings the edit box back with whatever was in it.

The Detach choice opens the selection in a window of its own
(selection_preview_window.py). That window is given no callback that could save
anything to the transcript, and it's built in test_gui_smoke.py.

Each test builds the real app with open_real_app (conftest.py). The preview is
started through the edit box's _dispatch_play(), what the menu's Play row
calls, and the text is a run of numbered words so the test can tell exactly
which one is on screen."""

import json

from tk_helpers import settle

WORDS = [f"w{i}" for i in range(120)]
TEXT = " ".join(WORDS)
SELECTION = " ".join(WORDS[10:40])
FAST = 900  # words a minute, so a preview gets through a few words quickly


def _stopped(app, title="A"):
    """A transcript that was read and then stopped, so it opens in the edit
    box with its text."""
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    store.set_transcript_text(transcript.id, TEXT)
    store.set_transcript_stopped(transcript.id, True)
    store.set_transcript_wpm(transcript.id, FAST)
    return transcript


def _draft(app, title="A"):
    """A transcript that was never started, with text waiting in its draft."""
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    store.set_transcript_draft_text(transcript.id, TEXT)
    store.set_transcript_wpm(transcript.id, FAST)
    return transcript


def _paused(app, title):
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


def _play(app, text=SELECTION):
    """Start a preview the way the menu's Play row does. Nothing is let run
    afterwards, so its first word is still on screen."""
    app.canvas.input_view._dispatch_play(text)


def _read_on_until(app, index, timeout_ms=5000):
    reader = app.canvas.reader_display
    waited = 0
    while reader.session.index < index and waited < timeout_ms:
        settle(app, 50)
        waited += 50
    assert reader.session.index >= index, "the preview didn't read on"


def _shown(reader):
    return "".join(label.cget("text") for label in (reader.before_label, reader.focus_label, reader.after_label))


def _state(transcript):
    """Everything a preview must leave as it was."""
    return {
        "position": transcript.position,
        "is_paused": transcript.is_paused,
        "is_stopped": transcript.is_stopped,
        "raw_text": transcript.raw_text,
        "draft_text": transcript.draft_text,
        "times_read": transcript.times_read,
        "total_words_read": transcript.total_words_read,
        "total_time_spent_seconds": transcript.total_time_spent_seconds,
        "bookmarks": list(transcript.bookmarks),
    }


def _saved_state(app, data_dir, transcript):
    app.store.flush()
    saved = json.loads((data_dir / "data.json").read_text(encoding="utf-8"))
    entry = next(t for t in saved["transcripts"] if t["id"] == transcript.id)
    return {key: entry[key] for key in _state(transcript) if key != "bookmarks"} | {"bookmarks": entry["bookmarks"]}


def _box_text(app):
    return app.canvas.input_view.get_text().rstrip("\n")


def test_play_reads_only_the_selection_from_its_first_word(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        canvas = app.canvas

        _play(app)

        assert canvas.reader_display.winfo_manager() == "pack"
        assert not canvas._input_currently_shown
        assert canvas.reader_display.session.total_words == 30
        assert _shown(canvas.reader_display) == "w10"
        assert canvas.scrub_bar.readout.cget("text") == "word 1 of 30"
        assert canvas.toolbar.pause_button.cget("text") == "⏸"


def test_whatever_is_done_in_a_preview_nothing_is_saved(tmp_path, open_real_app):
    """Reading on, pausing, playing again, skipping, dragging the progress bar,
    restarting, pausing and stopping: the transcript ends up exactly as it
    was, in memory and on disk. It ends paused, so a saved pause would show."""
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        canvas = app.canvas
        before = _state(a)
        saved_before = _saved_state(app, tmp_path, a)

        _play(app)
        _read_on_until(app, 5)
        canvas.toggle_pause()
        canvas.toggle_pause()
        canvas.skip_forward()
        canvas.scrub_bar._handle_slide(20.0)
        canvas.scrub_bar._handle_release()
        canvas.restart()
        _read_on_until(app, 3)
        canvas.toggle_pause()
        canvas.stop()
        settle(app, 300)

        assert _state(a) == before
        assert _saved_state(app, tmp_path, a) == saved_before
        assert canvas._input_currently_shown


def test_stop_brings_back_the_edit_box_with_what_was_in_it(tmp_path, open_real_app):
    """Including an edit that hasn't been saved yet: the box is hidden during
    the preview, not refilled from the saved text."""
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        canvas = app.canvas
        canvas.input_view.set_text(TEXT + " and one more")

        _play(app)
        _read_on_until(app, 3)
        canvas.stop()
        settle(app, 300)

        assert canvas._input_currently_shown
        assert canvas.input_view.winfo_manager() == "pack"
        assert _box_text(app) == TEXT + " and one more"
        assert canvas.scrub_bar.readout.cget("text") == ""


def test_a_preview_of_a_draft_leaves_it_a_draft(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _draft(app)
        _open(app, a)
        before = _state(a)

        _play(app)
        _read_on_until(app, 5)
        app.canvas.stop()
        settle(app, 300)

        assert _state(a) == before
        assert a.raw_text == ""
        assert _box_text(app) == TEXT


def test_a_preview_that_reaches_the_end_waits_for_stop(tmp_path, open_real_app):
    """It stays on "(finished)", the way the reader does at the end of a
    transcript, and counts nothing. Stop then brings back the edit box."""
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        canvas = app.canvas
        before = _state(a)

        _play(app, "w1 w2 w3 w4")
        _read_on_until(app, 4)
        settle(app, 300)

        assert canvas.reader_display.session.is_finished
        assert canvas.reader_display.before_label.cget("text") == "(finished)"
        assert not canvas._input_currently_shown
        assert _state(a) == before

        canvas.stop()
        settle(app, 300)
        assert canvas._input_currently_shown
        assert _box_text(app) == TEXT
        assert _state(a) == before


def test_a_preview_takes_no_bookmarks(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        canvas = app.canvas
        _play(app)
        canvas.toggle_pause()

        canvas.toggle_bookmark_here()
        canvas.open_bookmarks()
        settle(app, 300)

        assert a.bookmarks == []
        assert canvas._bookmarks_popover is None


def test_opening_another_transcript_ends_the_preview_and_saves_nothing(tmp_path, open_real_app):
    """The preview's words and time aren't counted for either transcript, and
    the one opened next is read and saved as usual."""
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        b = _paused(app, "B")
        _open(app, a)
        canvas = app.canvas
        before_a, before_b = _state(a), _state(b)

        _play(app)
        _read_on_until(app, 5)
        _open(app, b)

        assert canvas.current_transcript is b
        assert canvas.reader_display.session.total_words == 6
        assert _state(a) == before_a
        assert _state(b) == before_b

        canvas.toggle_pause()
        assert b.is_paused is False, "B's own play isn't saved once the preview is over"


def test_detaching_ends_the_preview_and_saves_nothing(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        canvas = app.canvas
        before = _state(a)

        _play(app)
        _read_on_until(app, 5)
        canvas._handle_detach()
        settle(app, 600)

        detached = canvas._detached_window
        assert detached is not None and detached.winfo_exists()
        assert detached.reader_display.session is None
        assert canvas.reader_display.session is None
        assert not canvas._ephemeral
        assert _state(a) == before


def test_closing_the_app_during_a_preview_counts_nothing(tmp_path, open_real_app):
    """The two things the app's close does before it saves: save the edit box
    and count the session still running. Neither may save anything from a
    preview."""
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        before = _state(a)

        _play(app)
        _read_on_until(app, 5)
        app.canvas.save_pending_draft()
        app.canvas.flush_active_session_stats()

        assert _state(a) == before
        assert _saved_state(app, tmp_path, a)["total_words_read"] == 0