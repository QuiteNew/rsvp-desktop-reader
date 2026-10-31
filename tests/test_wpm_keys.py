"""Tests for changing the reading speed with the Up and Down arrow keys: the
step itself (core/wpm_step.py), the main window (gui/app.py) with its footer
(gui/components/footer.py), and the detached window
(gui/components/detached_window.py), which reaches the app through Canvas.

What was agreed: Up and Down make the open transcript 10 WPM faster or slower,
in the main window and in the detached window, and not while typing in a box.
On top of that: the speed lands on the same values the footer's slider stops
at, it stays within the range Settings allows, and the footer follows. In the
detached window the keys change that window's own transcript, which is not
always the one the main window has open.

The app's side is tested on stand-ins first, the same way as in
test_settings_apply.py. The tests at the end build the real app once, keep it
on screen and open a real detached window from it."""

import json

import pytest

from core.models import Transcript
from core.settings_store import WPM_RANGE
from core.wpm_step import WPM_KEY_STEP, step_wpm

from tk_helpers import settle

UP, DOWN = 1, -1


# ---- the step (core/wpm_step.py) ----

def test_a_step_is_ten_words_per_minute():
    assert WPM_KEY_STEP == 10
    assert step_wpm(300, UP) == 310
    assert step_wpm(300, DOWN) == 290


def test_a_speed_between_the_sliders_stops_goes_to_the_nearest_one_that_way():
    assert step_wpm(305, UP) == 310
    assert step_wpm(305, DOWN) == 300
    assert step_wpm(301, DOWN) == 300
    assert step_wpm(309, UP) == 310


def test_the_speed_stays_inside_the_range():
    low, high = WPM_RANGE
    assert step_wpm(high, UP) == high
    assert step_wpm(low, DOWN) == low
    assert step_wpm(high - 5, UP) == high
    assert step_wpm(low + 5, DOWN) == low
    assert step_wpm(high, DOWN) == high - 10
    assert step_wpm(low, UP) == low + 10


def test_every_step_lands_inside_the_range_on_a_multiple_of_ten():
    low, high = WPM_RANGE
    for wpm in range(low, high + 1):
        for direction in (UP, DOWN):
            stepped = step_wpm(wpm, direction)
            assert low <= stepped <= high
            assert stepped % 10 == 0


# ---- the main window (gui/app.py), on a stand-in ----

class _Recorder:
    """Keeps a note of every call made to it, by method name."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        return lambda *args: self.calls.append((name, *args))


class _App:
    """Just enough of the app for the speed keys: the open transcript, a
    footer, a store and a canvas that only keep notes, and a switch for
    whether a typing box has the keyboard. Every other method is the app's
    own, run on this stand-in."""

    def __init__(self, transcript=None, typing=False):
        self._current_transcript = transcript
        self.footer = _Recorder()
        self.store = _Recorder()
        self.canvas = _Recorder()
        self.typing = typing

    def _shortcut_should_fire(self):
        return not self.typing

    def __getattr__(self, name):
        from gui.app import RSVPApp
        method = getattr(RSVPApp, name)
        return lambda *args, **kwargs: method(self, *args, **kwargs)


def _transcript(id=1, wpm=300):
    return Transcript(id=id, title=f"T{id}", space="General", wpm=wpm)


def test_up_makes_the_open_transcript_faster_like_the_slider_does():
    app = _App(_transcript(wpm=300))
    app._handle_shortcut_wpm_up()
    assert app.footer.calls == [("set_wpm", 310)]
    assert app.store.calls == [("set_transcript_wpm", 1, 310)]
    assert app.canvas.calls == [("set_wpm", 310)]


def test_down_makes_it_slower():
    app = _App(_transcript(wpm=300))
    app._handle_shortcut_wpm_down()
    assert app.footer.calls == [("set_wpm", 290)]
    assert app.store.calls == [("set_transcript_wpm", 1, 290)]


def test_nothing_happens_with_no_transcript_open():
    app = _App(None)
    app._handle_shortcut_wpm_up()
    assert app.footer.calls == app.store.calls == app.canvas.calls == []


def test_nothing_happens_at_the_end_of_the_range():
    app = _App(_transcript(wpm=WPM_RANGE[1]))
    app._handle_shortcut_wpm_up()
    assert app.footer.calls == app.store.calls == app.canvas.calls == []


def test_the_keys_are_left_alone_while_typing_in_a_box():
    app = _App(_transcript(wpm=300), typing=True)
    app._handle_shortcut_wpm_up()
    app._handle_shortcut_wpm_down()
    assert app.store.calls == []


def test_a_change_from_the_detached_window_is_saved_to_its_transcript():
    detached = _transcript(id=1, wpm=320)
    app = _App(_transcript(id=2, wpm=450))  # the main window has another one open
    app._handle_detached_wpm_changed(detached, 320)
    assert app.store.calls == [("set_transcript_wpm", 1, 320)]
    assert app.footer.calls == []  # the footer shows the other transcript


def test_the_footer_follows_the_detached_window_when_it_shows_the_same_transcript():
    transcript = _transcript(id=1, wpm=320)
    app = _App(transcript)
    app._handle_detached_wpm_changed(transcript, 320)
    assert app.footer.calls == [("set_wpm", 320)]


# ---- the detached window (gui/components/detached_window.py), on a stand-in ----

class _Detached:
    """Just enough of the detached window for the speed keys: its transcript,
    its reader, the callback to the app, and the typing switch."""

    def __init__(self, transcript, typing=False, report=True):
        self.transcript = transcript
        self.reader_display = _Recorder()
        self.reported = []
        self.on_wpm_changed = (lambda t, wpm: self.reported.append((t.id, wpm))) if report else None
        self.typing = typing

    def _shortcut_should_fire(self):
        return not self.typing

    def __getattr__(self, name):
        from gui.components.detached_window import DetachedTranscriptWindow
        method = getattr(DetachedTranscriptWindow, name)
        return lambda *args, **kwargs: method(self, *args, **kwargs)


def test_up_in_the_detached_window_speeds_up_its_reader_and_reports_it():
    window = _Detached(_transcript(id=7, wpm=300))
    window._handle_shortcut_wpm_up()
    assert window.reader_display.calls == [("set_wpm", 310)]
    assert window.reported == [(7, 310)]


def test_down_in_the_detached_window_slows_it_down():
    window = _Detached(_transcript(id=7, wpm=300))
    window._handle_shortcut_wpm_down()
    assert window.reported == [(7, 290)]


def test_the_detached_window_leaves_the_keys_alone_while_typing():
    window = _Detached(_transcript(wpm=300), typing=True)
    window._handle_shortcut_wpm_up()
    window._handle_shortcut_wpm_down()
    assert window.reader_display.calls == []
    assert window.reported == []


def test_the_detached_window_does_nothing_at_the_end_of_the_range():
    window = _Detached(_transcript(wpm=WPM_RANGE[0]))
    window._handle_shortcut_wpm_down()
    assert window.reader_display.calls == []
    assert window.reported == []


def test_a_detached_window_nobody_listens_to_still_changes_its_reader():
    window = _Detached(_transcript(wpm=300), report=False)
    window._handle_shortcut_wpm_up()
    assert window.reader_display.calls == [("set_wpm", 310)]


# ---- the real app ----

@pytest.fixture(scope="module")
def app(tmp_path_factory, open_real_app):
    """One real app for the tests below, with two transcripts, A and B, at
    different speeds."""
    data_dir = tmp_path_factory.mktemp("rsvp_wpm_keys")
    with open_real_app(data_dir) as application:
        store = application.store
        for title, wpm in (("A", 300), ("B", 450)):
            transcript = store.add_transcript(title, store.current_space)
            store.set_transcript_text(transcript.id, f"{title.lower()}word " * 50)
            store.set_transcript_paused(transcript.id, True)
            store.set_transcript_wpm(transcript.id, wpm)
        application._refresh_transcript_list()
        application.data_dir = data_dir
        settle(application, 300)
        try:
            yield application
        finally:
            detached = application.canvas._detached_window
            if detached is not None:
                detached.close()
            settle(application, 200)


def _named(app, title):
    return next(t for t in app.store.transcripts if t.title == title)


def _saved_wpm(app):
    app.store.flush()
    data = json.loads((app.data_dir / "data.json").read_text(encoding="utf-8"))
    return {t["title"]: t["wpm"] for t in data["transcripts"]}


def test_up_and_down_are_bound_in_the_main_window(app):
    assert "_handle_shortcut_wpm_up" in app.bind("<Up>")
    assert "_handle_shortcut_wpm_down" in app.bind("<Down>")


def test_the_keys_change_the_open_transcript_its_reader_and_the_footer(app):
    a = _named(app, "A")
    app._handle_open_transcript(a)
    settle(app, 300)
    app._handle_shortcut_wpm_up()
    app._handle_shortcut_wpm_up()
    app._handle_shortcut_wpm_down()
    assert a.wpm == 310
    assert app.canvas.reader_display.session.wpm == 310
    assert app.footer.wpm_label.cget("text") == "310 WPM"
    assert app.footer.wpm_slider.get() == 310
    assert _saved_wpm(app)["A"] == 310


def test_the_detached_window_has_the_keys_and_changes_its_own_transcript(app):
    a, b = _named(app, "A"), _named(app, "B")
    app._handle_open_transcript(a)
    settle(app, 300)
    app.canvas._handle_detach()
    settle(app, 600)
    detached = app.canvas._detached_window
    assert "_handle_shortcut_wpm_up" in detached.bind("<Up>")
    assert "_handle_shortcut_wpm_down" in detached.bind("<Down>")

    start = a.wpm
    detached._handle_shortcut_wpm_up()
    assert a.wpm == start + 10
    assert detached.reader_display.session.wpm == start + 10
    assert app.footer.wpm_label.cget("text") == f"{start + 10} WPM"  # the footer shows A too

    # Now the main window opens B, and the keys in the detached window still
    # change A, not B, and leave the footer showing B.
    app._handle_open_transcript(b)
    settle(app, 300)
    detached._handle_shortcut_wpm_down()
    detached._handle_shortcut_wpm_down()
    assert a.wpm == start - 10
    assert b.wpm == 450
    assert detached.reader_display.session.wpm == start - 10
    assert app.footer.wpm_label.cget("text") == "450 WPM"
    assert _saved_wpm(app) == {"A": start - 10, "B": 450}