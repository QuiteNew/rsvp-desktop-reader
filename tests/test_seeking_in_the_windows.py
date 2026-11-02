"""Tests for moving to another place in the text from the windows: dragging the
progress bar and jumping to a bookmark, in the main window
(gui/components/canvas.py) and the detached window (detached_window.py).

What the reader itself does with a drag or a jump is tested in
test_seeking.py. Here the real app is built with open_real_app (conftest.py),
and the question is what each window shows and saves: the word, the bar's
read-out, the play button, and the position and pause stored for the right
transcript. They live in their own file because the real app can't share a
module with the hidden root test_seeking.py uses: the app's window icon would
be made for that root instead of the app."""

import json

from tk_helpers import settle

WORDS = [f"w{i}" for i in range(120)]
TEXT = " ".join(WORDS)


def _shown(reader):
    """The word a reader has on screen, put back together from its three
    parts (before the focus letter, the focus letter, after it)."""
    return "".join(label.cget("text") for label in (reader.before_label, reader.focus_label, reader.after_label))


def _read_on_until(reader, index, timeout_ms=5000):
    """Let Tk run until reading has passed the given word. Fails if it
    doesn't get there in time."""
    waited = 0
    while reader.session.index <= index and waited < timeout_ms:
        settle(reader, 50)
        waited += 50
    assert reader.session.index > index, "reading didn't carry on"


def _add(app, *titles, paused=False):
    """Add transcripts with text and show them in the sidebar. They open
    playing unless paused is set. Returns them in order."""
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


def _drag(bar, index):
    """Drag a progress bar to a word and let go: what the slider and its
    release binding call."""
    bar._handle_slide(float(index))
    bar._handle_release()


def _shows_paused(toolbar):
    return toolbar.pause_button.cget("text") == "▶"


def _saved(app, data_dir, transcript):
    app.store.flush()
    saved = json.loads((data_dir / "data.json").read_text(encoding="utf-8"))
    entry = next(t for t in saved["transcripts"] if t["id"] == transcript.id)
    return entry["position"], entry["is_paused"]


def test_a_drag_in_the_main_window_is_shown_and_saved(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        (a,) = _add(app, "A")
        _open(app, a)
        canvas = app.canvas

        canvas.scrub_bar._handle_slide(40.0)
        assert _shows_paused(canvas.toolbar), "the play button doesn't show the hold during the drag"
        canvas.scrub_bar._handle_release()
        settle(app, 300)

        assert _shown(canvas.reader_display) == "w40"
        assert canvas.scrub_bar.readout.cget("text") == "word 41 of 120"
        assert _shows_paused(canvas.toolbar)
        assert (a.position, a.is_paused) == (40, True)
        assert _saved(app, tmp_path, a) == (40, True)


def test_with_the_setting_off_a_drag_in_the_main_window_carries_on(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        (a,) = _add(app, "A")
        _open(app, a)
        canvas = app.canvas
        canvas.set_scrub_pause(False)

        _drag(canvas.scrub_bar, 40)
        _read_on_until(canvas.reader_display, 40)

        assert not _shows_paused(canvas.toolbar)
        assert a.is_paused is False
        assert a.position > 40


def test_a_bookmark_jump_in_the_main_window_lands_there_and_closes_the_list(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        (a,) = _add(app, "A")
        app.store.add_bookmark(a.id, 70, "w67 w68 w69 w70 w71 w72 w73")
        _open(app, a)
        canvas = app.canvas
        canvas.open_bookmarks()
        settle(app, 300)
        popover = canvas._bookmarks_popover

        popover._handle_jump(70)
        settle(app, 300)

        assert _shown(canvas.reader_display) == "w70"
        assert canvas.scrub_bar.readout.cget("text") == "word 71 of 120"
        assert _shows_paused(canvas.toolbar)
        assert canvas._bookmarks_popover is None
        assert not popover.winfo_exists()
        assert _saved(app, tmp_path, a) == (70, True)


def test_seeking_in_the_detached_window_moves_and_saves_its_own_transcript_only(tmp_path, open_real_app):
    """A is detached and playing, and B is open in the main window, paused. A
    drag and a bookmark jump in the detached window move A and save A, paused.
    B stays where it was, in the same reading session."""
    with open_real_app(tmp_path) as app:
        (a,) = _add(app, "A")
        (b,) = _add(app, "B", paused=True)
        app.store.add_bookmark(a.id, 90, "w87 w88 w89 w90 w91 w92 w93")
        _open(app, a)
        app.canvas._handle_detach()
        settle(app, 600)
        detached = app.canvas._detached_window
        _open(app, b)
        app._handle_shortcut_skip_forward()
        settle(app, 150)
        session_b = app.canvas.reader_display.session
        place_b = b.position
        assert place_b > 0

        _drag(detached.scrub_bar, 40)
        settle(app, 300)
        assert _shown(detached.reader_display) == "w40"
        assert _shows_paused(detached.toolbar)
        assert _saved(app, tmp_path, a) == (40, True)

        detached._handle_pause_toggle()
        assert a.is_paused is False
        detached.open_bookmarks()
        settle(app, 300)
        popover = detached._bookmarks_popover
        popover._handle_jump(90)
        settle(app, 300)
        assert _shown(detached.reader_display) == "w90"
        assert _shows_paused(detached.toolbar)
        assert detached._bookmarks_popover is None
        assert not popover.winfo_exists()
        assert _saved(app, tmp_path, a) == (90, True)

        assert app.canvas.reader_display.session is session_b
        assert session_b.index == place_b
        assert _saved(app, tmp_path, b) == (place_b, True)