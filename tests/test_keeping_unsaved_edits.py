"""Tests for keeping what was typed in the edit box when you leave it
(gui/components/canvas.py, _capture_current_draft(), and its callers
load_transcript(), save_pending_draft() and _handle_detach()).

The edit box doesn't save as you type. What's in it is saved when you leave it:
when you open another transcript, detach, or close the app. For a transcript
that was read and stopped, that's saved as its text, and for one never started,
as its draft.

Two ways out used to lose an edit that hadn't been saved yet, both fixed with
these tests:

  - Leaving while a selection preview (right-click Play) was playing. The
    preview hides the edit box, and the box was only saved while it was on
    screen, so opening another transcript or closing the app dropped the edit.
  - Detaching a stopped transcript. The detached window was given the last
    saved text instead of what was in the box.

Each test builds the real app with open_real_app (conftest.py), types an edit
into the box with set_text() and then leaves the way the app does."""

import json

from tk_helpers import settle

TEXT = " ".join(f"w{i}" for i in range(60))
EDITED = TEXT + " and an edit not saved yet"


def _stopped(app, title="A"):
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    store.set_transcript_text(transcript.id, TEXT)
    store.set_transcript_stopped(transcript.id, True)
    return transcript


def _draft(app, title="A"):
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    store.set_transcript_draft_text(transcript.id, TEXT)
    return transcript


def _paused(app, title="B"):
    store = app.store
    transcript = store.add_transcript(title, store.current_space)
    store.set_transcript_text(transcript.id, "one two three four")
    store.set_transcript_paused(transcript.id, True)
    return transcript


def _open(app, transcript):
    app._refresh_transcript_list()
    settle(app, 200)
    app._handle_open_transcript(transcript)
    settle(app, 300)


def _edit(app):
    app.canvas.input_view.set_text(EDITED)


def _play_a_selection(app):
    app.canvas.input_view._dispatch_play("w10 w11 w12 w13 w14 w15")
    settle(app, 200)
    assert app.canvas._ephemeral


def _box_text(view):
    return view.get_text().rstrip("\n")


def _saved(app, data_dir, transcript):
    app.store.flush()
    saved = json.loads((data_dir / "data.json").read_text(encoding="utf-8"))
    entry = next(t for t in saved["transcripts"] if t["id"] == transcript.id)
    return entry["raw_text"], entry["draft_text"]


def _detach(app):
    app.canvas._handle_detach()
    settle(app, 600)
    return app.canvas._detached_window


# ---- opening another transcript ----

def test_opening_another_transcript_keeps_the_edit_of_a_stopped_one(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _stopped(app), _paused(app)
        _open(app, a)
        _edit(app)

        _open(app, b)
        assert _saved(app, tmp_path, a) == (EDITED, "")

        _open(app, a)
        assert _box_text(app.canvas.input_view) == EDITED


def test_opening_another_transcript_keeps_the_edit_of_a_draft(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _draft(app), _paused(app)
        _open(app, a)
        _edit(app)

        _open(app, b)
        assert _saved(app, tmp_path, a) == ("", EDITED)


def test_opening_another_transcript_during_a_preview_keeps_the_edit(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _stopped(app), _paused(app)
        _open(app, a)
        _edit(app)
        _play_a_selection(app)

        _open(app, b)
        assert _saved(app, tmp_path, a) == (EDITED, "")

        _open(app, a)
        assert _box_text(app.canvas.input_view) == EDITED


def test_opening_another_transcript_during_a_preview_keeps_the_edit_of_a_draft(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _draft(app), _paused(app)
        _open(app, a)
        _edit(app)
        _play_a_selection(app)

        _open(app, b)
        assert _saved(app, tmp_path, a) == ("", EDITED)


# ---- closing the app ----

def test_closing_the_app_during_a_preview_keeps_the_edit(tmp_path, open_real_app):
    """save_pending_draft() is the first thing the app's close does."""
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        _edit(app)
        _play_a_selection(app)

        app.canvas.save_pending_draft()
        assert _saved(app, tmp_path, a) == (EDITED, "")


# ---- detaching ----

def test_detaching_a_stopped_transcript_takes_the_edit_along(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        _edit(app)

        window = _detach(app)
        assert _box_text(window.input_view) == EDITED
        assert _saved(app, tmp_path, a) == (EDITED, "")


def test_detaching_a_draft_takes_the_edit_along(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _draft(app)
        _open(app, a)
        _edit(app)

        window = _detach(app)
        assert _box_text(window.input_view) == EDITED
        assert _saved(app, tmp_path, a) == ("", EDITED)


def test_detaching_during_a_preview_takes_the_edit_along(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        _edit(app)
        _play_a_selection(app)

        window = _detach(app)
        assert window.reader_display.session is None
        assert _box_text(window.input_view) == EDITED
        assert _saved(app, tmp_path, a) == (EDITED, "")


def test_the_edit_survives_detaching_and_closing_the_detached_window(tmp_path, open_real_app):
    """The way back: closing the detached window saves its box and shows the
    transcript in the main window again."""
    with open_real_app(tmp_path) as app:
        a = _stopped(app)
        _open(app, a)
        _edit(app)

        window = _detach(app)
        window.close()
        settle(app, 300)

        assert app.canvas._detached_window is None
        assert _box_text(app.canvas.input_view) == EDITED
        assert _saved(app, tmp_path, a) == (EDITED, "")