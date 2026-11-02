"""Tests for deleting a transcript that is on screen: open in the main window,
off in the detached window, or both (gui/components/canvas.py,
handle_transcript_deleted(), and gui/app.py, _handle_delete_confirmed()).

The store's side of a delete is tested in test_transcript_store.py, and the
app's bookkeeping on a stand-in in test_reopen_last_transcript.py and
test_transcript_list_current.py. Here the real app is on the other end, so the
question is what the windows do: the reader for a deleted transcript stops, its
detached window closes, and a different transcript that is open stays exactly
as it was, still reading the same session from the same place.

Each test builds the real app with open_real_app (conftest.py), and the delete
goes through _handle_delete_confirmed(), what the confirm dialog's Delete
button calls."""

import json

from tk_helpers import settle

TEXT = "word " * 120


def _add(app, *titles, paused=True):
    """Add transcripts with text, the way they'd be after a first read, and
    show them in the sidebar. Returns them in order."""
    store = app.store
    added = []
    for title in titles:
        transcript = store.add_transcript(title, store.current_space)
        store.set_transcript_text(transcript.id, TEXT)
        store.set_transcript_paused(transcript.id, paused)
        added.append(transcript)
    app._refresh_transcript_list()
    settle(app, 300)
    return added


def _open(app, transcript):
    app._handle_open_transcript(transcript)
    settle(app, 300)


def _detach(app):
    app.canvas._handle_detach()
    settle(app, 600)
    return app.canvas._detached_window


def _shows_empty(app):
    return app.canvas.empty_label.winfo_manager() == "pack"


def _saved_titles(app, data_dir):
    app.store.flush()
    saved = json.loads((data_dir / "data.json").read_text(encoding="utf-8"))
    return [t["title"] for t in saved["transcripts"]]


def test_deleting_the_open_transcript_empties_the_main_window(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")
        _open(app, a)
        app.canvas.open_bookmarks()
        settle(app, 300)
        assert app.canvas._bookmarks_popover is not None

        app._handle_delete_confirmed(a)
        settle(app, 300)

        assert app.canvas.current_transcript is None
        assert app.canvas.reader_display.session is None
        assert app.canvas._bookmarks_popover is None
        assert _shows_empty(app)
        assert app._current_transcript is None
        assert app.header._full_title == "No transcript selected"
        assert app.settings_store.last_transcript_id is None
        assert a.id not in app.list_body._rows
        assert _saved_titles(app, tmp_path) == ["B"]


def test_deleting_the_open_transcript_while_it_plays_leaves_nothing_reading_it(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        (a,) = _add(app, "A", paused=False)
        _open(app, a)
        reader = app.canvas.reader_display
        assert reader.session is not None and not reader._is_paused

        app._handle_delete_confirmed(a)
        settle(app, 500)

        assert reader.session is None
        assert reader._after_id is None, "the next word is still on its way"
        assert _saved_titles(app, tmp_path) == []


def test_deleting_the_detached_transcript_closes_its_window(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        (a,) = _add(app, "A")
        _open(app, a)
        window = _detach(app)
        assert window is not None and window.winfo_exists()

        app._handle_delete_confirmed(a)
        settle(app, 300)

        assert app.canvas._detached_window is None
        assert app.canvas._detached_transcript_id is None
        assert not window.winfo_exists()
        assert app.canvas.current_transcript is None
        assert _shows_empty(app)
        assert _saved_titles(app, tmp_path) == []


def test_deleting_the_detached_transcript_leaves_the_one_open_here_alone(tmp_path, open_real_app):
    """A is detached and B is open in the main window. Deleting A closes A's
    window and nothing else: B keeps the very same reading session, at the
    same place, and the main window isn't reloaded."""
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")
        _open(app, a)
        window = _detach(app)
        _open(app, b)
        app._handle_shortcut_skip_forward()
        settle(app, 150)
        session = app.canvas.reader_display.session
        place = session.index
        assert place > 0

        app._handle_delete_confirmed(a)
        settle(app, 300)

        assert not window.winfo_exists()
        assert app.canvas._detached_window is None
        assert app.canvas.current_transcript is b
        assert app.canvas.reader_display.session is session
        assert session.index == place
        assert not _shows_empty(app)
        assert app.header._full_title == "B"
        assert _saved_titles(app, tmp_path) == ["B"]


def test_deleting_a_transcript_that_is_not_on_screen_changes_nothing_on_screen(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b = _add(app, "A", "B")
        _open(app, a)
        session = app.canvas.reader_display.session

        app._handle_delete_confirmed(b)
        settle(app, 300)

        assert app.canvas.current_transcript is a
        assert app.canvas.reader_display.session is session
        assert app.header._full_title == "A"
        assert list(app.list_body._rows) == [a.id]
        assert _saved_titles(app, tmp_path) == ["A"]


def test_deleting_another_transcript_leaves_the_detached_window_alone(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        a, b, c = _add(app, "A", "B", "C")
        _open(app, a)
        window = _detach(app)
        _open(app, b)

        app._handle_delete_confirmed(c)
        settle(app, 300)

        assert window.winfo_exists()
        assert app.canvas._detached_window is window
        assert app.canvas._detached_transcript_id == a.id
        assert app.canvas.current_transcript is b
        assert _saved_titles(app, tmp_path) == ["A", "B"]