"""Tests for which reader the main window's controls reach while a transcript is
detached (gui/components/canvas.py, _detached_shows_current() and the methods
that ask it).

The bug: with transcript A in the detached window, the main window can open
and read another transcript, B. Its controls still went to A's detached reader
whenever any window was detached: the footer's speed changed A's reader on
screen without being saved to A, and Space started A while B was saved as
playing. Now the main window's keys, footer and toolbar reach the detached
reader only while the main window has that same transcript open (and shows
the "detached" placeholder for it), and otherwise they reach its own reader.
Settings that belong to the whole app, like the guide marks, still reach both
windows either way.

Canvas is tested on a stand-in, the same way as other tests run the app's
methods. The test at the end does the whole thing with the real app."""

import json

import pytest

from core.models import Transcript

from tk_helpers import settle

A, B = 1, 2


class _Part:
    """A reader or a toolbar that keeps a note of every call made to it, and
    answers the few that return something."""

    ANSWERS = {"skip": True, "toggle_pause": False, "current_bookmark_target": None}

    def __init__(self):
        self.calls = []
        self.session = None

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append(name)
            return self.ANSWERS.get(name)
        return call


class _DetachedWindow(_Part):
    def __init__(self):
        super().__init__()
        self.reader_display = _Part()
        self.toolbar = _Part()


class _Canvas:
    """Just enough of Canvas: its own reader and toolbar, a detached window
    reading transcript A (or none), and the transcript open here. Every other
    method is Canvas's own, run on this stand-in."""

    def __init__(self, open_id=A, detached=True):
        self.current_transcript = Transcript(id=open_id, title=f"T{open_id}", space="General")
        self._detached_window = _DetachedWindow() if detached else None
        self._detached_transcript_id = A if detached else None
        self.reader_display = _Part()
        self.toolbar = _Part()
        self._pause_on_skip = False
        self._skip_word_count = 10
        self._ephemeral = False
        self._highlight_offset_px = 0
        self.on_pause_changed = None

    def __getattr__(self, name):
        from gui.components.canvas import Canvas
        method = getattr(Canvas, name)
        return lambda *args, **kwargs: method(self, *args, **kwargs)


def _main_and_detached(canvas):
    """What reached this window's reader, and what reached the detached one's
    (or the detached window itself, for the bookmark controls)."""
    detached = canvas._detached_window
    return canvas.reader_display.calls, (detached.reader_display.calls + detached.calls) if detached else None


# ---- when the detached window counts ----

def test_the_detached_window_counts_when_it_holds_the_transcript_open_here():
    assert _Canvas(open_id=A)._detached_shows_current() is True


def test_it_does_not_when_another_transcript_is_open_here():
    assert _Canvas(open_id=B)._detached_shows_current() is False


def test_it_does_not_when_nothing_is_detached():
    assert _Canvas(detached=False)._detached_shows_current() is False


def test_it_does_not_without_a_window_even_if_the_transcript_matches():
    """Never left that way by Canvas, which forgets both together, but the
    answer has to be safe to act on: there is no window to send anything to."""
    canvas = _Canvas(open_id=A)
    canvas._detached_window = None
    assert canvas._detached_shows_current() is False


def test_it_does_not_when_nothing_is_open_here():
    canvas = _Canvas()
    canvas.current_transcript = None
    assert canvas._detached_shows_current() is False


# ---- the controls ----

CONTROLS = {
    "pause": (lambda c: c.toggle_pause(), "toggle_pause"),
    "restart": (lambda c: c.restart(), "restart"),
    "skip forward": (lambda c: c.skip_forward(), "skip"),
    "skip backward": (lambda c: c.skip_backward(), "skip"),
    "centre": (lambda c: c.center_pan(), "center_pan"),
    "bookmark": (lambda c: c.toggle_bookmark_here(), "current_bookmark_target"),
}
DETACHED_SIDE = {"bookmark": "toggle_bookmark_here"}


@pytest.mark.parametrize("name", CONTROLS)
def test_a_control_reaches_the_detached_reader_while_it_reads_the_open_transcript(name):
    press, main_call = CONTROLS[name]
    canvas = _Canvas(open_id=A)
    press(canvas)
    main, detached = _main_and_detached(canvas)
    assert main_call not in main
    assert DETACHED_SIDE.get(name, main_call) in detached


@pytest.mark.parametrize("name", CONTROLS)
def test_a_control_reaches_this_windows_reader_when_another_transcript_is_open(name):
    press, main_call = CONTROLS[name]
    canvas = _Canvas(open_id=B)
    press(canvas)
    main, detached = _main_and_detached(canvas)
    assert main_call in main
    assert detached == []


def test_bookmarks_open_for_the_detached_window_only_while_it_reads_the_open_transcript():
    canvas = _Canvas(open_id=A)
    canvas.open_bookmarks()
    assert canvas._detached_window.calls == ["open_bookmarks"]
    canvas = _Canvas(open_id=B)
    canvas.open_bookmarks()  # this window's reader has no session, so nothing opens
    assert canvas._detached_window.calls == []


# ---- the open transcript's own values ----

SETTERS = {
    "set_wpm": (500,),
    "set_chunking": (True, 3),
    "set_colors": ("#000000", "#111111", "#222222"),
    "set_font_size": (40,),
}


@pytest.mark.parametrize("setter", SETTERS)
def test_the_open_transcripts_values_reach_the_detached_reader_only_when_it_reads_it(setter):
    same = _Canvas(open_id=A)
    getattr(same, setter)(*SETTERS[setter])
    assert setter in same.reader_display.calls
    assert setter in same._detached_window.reader_display.calls

    other = _Canvas(open_id=B)
    getattr(other, setter)(*SETTERS[setter])
    assert setter in other.reader_display.calls
    assert other._detached_window.reader_display.calls == []


def test_settings_for_the_whole_app_still_reach_both_windows():
    canvas = _Canvas(open_id=B)
    canvas.set_highlight_offset(2)
    canvas.set_skip_word_count(5)
    assert "set_highlight_offset" in canvas._detached_window.reader_display.calls
    assert "set_skip_word_count" in canvas._detached_window.calls


# ---- the real app ----

def test_with_one_transcript_detached_the_main_window_reads_another_on_its_own(tmp_path, open_real_app):
    """A is detached and B is open in the main window. The footer's speed,
    Right and Space all act on B, and A is left as it was, on screen and in
    what is saved. Opening A again in the main window hands the controls back
    to the detached window."""
    with open_real_app(tmp_path) as app:
        try:
            store = app.store
            a = store.add_transcript("A", store.current_space)
            b = store.add_transcript("B", store.current_space)
            for transcript in (a, b):
                store.set_transcript_text(transcript.id, f"{transcript.title.lower()}word " * 60)
                store.set_transcript_paused(transcript.id, True)
            app._refresh_transcript_list()
            settle(app, 300)
            app._handle_open_transcript(a)
            settle(app, 300)
            app.canvas._handle_detach()
            settle(app, 600)
            detached = app.canvas._detached_window.reader_display
            app._handle_open_transcript(b)
            settle(app, 300)
            main = app.canvas.reader_display

            app.footer.wpm_slider.set(700)
            app.footer._handle_wpm_slide(700)
            app._handle_shortcut_skip_forward()
            app._handle_shortcut_pause_toggle()
            settle(app, 150)
            assert (main.session.wpm, main._is_paused) == (700, False)
            assert main.session.index > 0
            assert (detached.session.wpm, detached._is_paused, detached.session.index) == (300, True, 0)
            assert (b.wpm, b.is_paused) == (700, False)
            assert (a.wpm, a.is_paused) == (300, True)

            app._handle_shortcut_pause_toggle()  # B paused again, so it stops moving
            app._handle_open_transcript(a)
            settle(app, 300)
            assert app.canvas._detached_shows_current()
            app._handle_shortcut_pause_toggle()
            app._handle_shortcut_wpm_up()
            settle(app, 150)
            assert (detached.session.wpm, detached._is_paused) == (310, False)
            assert (a.wpm, a.is_paused) == (310, False)
            assert (b.wpm, b.is_paused) == (700, True)

            store.flush()
            saved = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
            assert {t["title"]: (t["wpm"], t["is_paused"]) for t in saved["transcripts"]} == {
                "A": (310, False), "B": (700, True),
            }
        finally:
            if app.canvas._detached_window is not None:
                app.canvas._detached_window.close()
            settle(app, 200)