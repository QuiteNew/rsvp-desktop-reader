"""Tests for moving the reader to another place in the text: dragging the
progress bar, and jumping to a bookmark (gui/components/reader_display.py,
scrub_move(), scrub_end() and jump_to()).

The rules, as the code has them:

  - While the bar is dragged, reading holds still on the word under the thumb,
    and every new word is reported so it gets saved.
  - On letting go, reading stays paused if "Pause after using the scrubber" is
    on, or if it was already paused when the drag began. Otherwise it carries
    on from the new word.
  - A click on the bar that didn't move it changes nothing.
  - A bookmark jump always lands paused on the bookmarked word.
  - Moving around isn't reading: no words are counted for it, and time spent
    paused after it isn't counted as reading time.

These run the reader on its own, on the shared hidden root.
test_seeking_in_the_windows.py checks what the main and detached windows show
and save. The time checks swap the reader's clock for one the test moves by
hand, so they're exact and don't depend on how fast the machine is. Nothing
here lets Tk run its timers unless the test says so, so reading only moves on
when a test lets it."""

import pytest

from core.reader import ReaderSession

from tk_helpers import settle

WORDS = [f"w{i}" for i in range(120)]
TEXT = " ".join(WORDS)


class FakeClock:
    """Stands in for the time module inside the reader. Time only passes
    when a test moves it on."""

    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    import gui.components.reader_display as reader_display

    fake = FakeClock()
    monkeypatch.setattr(reader_display, "time", fake)
    return fake


@pytest.fixture
def reader(root):
    """A reader on the shared root that writes down what it reports: the
    positions in reader.positions, and each (words read, active seconds)
    report in reader.stats."""
    from gui.components.reader_display import ReaderDisplay

    positions, stats = [], []
    display = ReaderDisplay(
        root,
        on_position_changed=positions.append,
        on_session_stats=lambda words, seconds: stats.append((words, seconds)),
    )
    display.positions, display.stats = positions, stats
    display.pack(fill="both", expand=True)
    root.update_idletasks()
    yield display
    # Nothing must be left to advance a word in a later test.
    display._cancel_pending()
    display.destroy()


def _load(reader, paused=False):
    reader.load_session(ReaderSession(TEXT), start_paused=paused)
    reader.positions.clear()
    return reader.session


def _shown(reader):
    """The word the reader has on screen, put back together from its three
    parts (before the focus letter, the focus letter, after it)."""
    return "".join(label.cget("text") for label in (reader.before_label, reader.focus_label, reader.after_label))


def _is_waiting_to_advance(reader):
    return reader._after_id is not None


def _read_on_until(reader, index, timeout_ms=5000):
    """Let Tk run until reading has passed the given word. Fails if it
    doesn't get there in time."""
    waited = 0
    while reader.session.index <= index and waited < timeout_ms:
        settle(reader, 50)
        waited += 50
    assert reader.session.index > index, "reading didn't carry on"


# ---- dragging the bar ----

def test_a_drag_holds_reading_on_the_word_under_the_thumb(reader):
    _load(reader)
    assert _is_waiting_to_advance(reader)

    assert reader.scrub_move(10) is True
    assert not _is_waiting_to_advance(reader)
    assert _shown(reader) == "w10"

    assert reader.scrub_move(25) is True
    assert _shown(reader) == "w25"
    assert reader.positions == [10, 25]

    settle(reader, 400)
    assert reader.session.index == 25, "reading moved on under the thumb"


def test_letting_go_stays_paused_when_the_setting_is_on(reader):
    _load(reader)
    reader.scrub_move(30)

    assert reader.scrub_end() is True
    assert not _is_waiting_to_advance(reader)
    settle(reader, 400)
    assert reader.session.index == 30


def test_letting_go_carries_on_when_the_setting_is_off_and_it_was_playing(reader):
    """The second move finds reading already held by the first. What counts
    is whether it was playing when the drag began."""
    reader.set_scrub_pause(False)
    _load(reader)
    reader.scrub_move(10)
    reader.scrub_move(30)

    assert reader.scrub_end() is False
    assert _is_waiting_to_advance(reader)
    _read_on_until(reader, 30)


def test_letting_go_stays_paused_when_it_was_paused_before_the_drag(reader):
    reader.set_scrub_pause(False)
    _load(reader, paused=True)
    reader.scrub_move(30)

    assert reader.scrub_end() is True
    assert not _is_waiting_to_advance(reader)


@pytest.mark.parametrize("paused", [False, True], ids=["playing", "paused"])
def test_a_click_on_the_bar_that_did_not_move_it_changes_nothing(reader, paused):
    _load(reader, paused=paused)
    reader.skip(5)

    assert reader.scrub_end() is paused
    assert _is_waiting_to_advance(reader) is not paused
    assert reader.session.index == 5


def test_each_drag_starts_afresh(reader):
    """A drag that began while playing, then a click without a drag, then a
    drag that began while paused: only the first one carries on."""
    reader.set_scrub_pause(False)
    _load(reader)
    reader.scrub_move(10)
    assert reader.scrub_end() is False

    reader.toggle_pause()
    assert reader.scrub_end() is True
    reader.scrub_move(50)
    assert reader.scrub_end() is True
    assert not _is_waiting_to_advance(reader)


# ---- jumping to a bookmark ----

@pytest.mark.parametrize("paused", [False, True], ids=["playing", "paused"])
def test_a_bookmark_jump_lands_paused_on_the_bookmarked_word(reader, paused):
    _load(reader, paused=paused)

    assert reader.jump_to(42) is True
    assert _shown(reader) == "w42"
    assert reader.positions == [42]
    assert not _is_waiting_to_advance(reader)
    settle(reader, 400)
    assert reader.session.index == 42


def test_with_nothing_loaded_seeking_does_nothing(reader):
    assert reader.session is None
    reader.scrub_move(10)
    reader.scrub_end()
    reader.jump_to(10)
    assert reader.positions == []
    assert reader.stats == []


# ---- what counts as reading ----

def test_time_paused_after_a_drag_is_not_reading_time(reader, clock):
    """Playing for 10 seconds, then dragging for 15 and sitting paused for 15
    more: 10 seconds of reading, and no words, however far the drag went."""
    _load(reader)
    clock.now = 10
    reader.scrub_move(80)
    clock.now = 25
    reader.scrub_end()
    clock.now = 40

    reader.finalize_session()
    assert reader.stats == [(0, 10.0)]


def test_reading_time_picks_up_again_when_letting_go_carries_on(reader, clock):
    """Playing for 10 seconds, dragging for 15, then playing again for 15:
    25 seconds of reading."""
    reader.set_scrub_pause(False)
    _load(reader)
    clock.now = 10
    reader.scrub_move(80)
    clock.now = 25
    reader.scrub_end()
    clock.now = 40

    reader.finalize_session()
    assert reader.stats == [(0, 25.0)]


def test_time_after_a_bookmark_jump_is_not_reading_time(reader, clock):
    _load(reader)
    clock.now = 10
    reader.jump_to(80)
    clock.now = 30

    reader.finalize_session()
    assert reader.stats == [(0, 10.0)]


def test_only_the_words_read_after_a_drag_count(reader, clock):
    """A drag 60 words ahead, then reading on for a few: only those few are
    counted."""
    reader.set_scrub_pause(False)
    _load(reader)
    reader.scrub_move(60)
    reader.scrub_end()
    _read_on_until(reader, 62)
    read_on = reader.session.index - 60

    reader.finalize_session()
    assert reader.stats == [(read_on, 0.0)]