"""Tests for letter spacing in the reader (ReaderDisplay.set_letter_spacing).

The gap sizes themselves are tested in test_letter_spacing.py. This file checks
the wiring on the real widget: that the drawn text gets the gaps, that the focus
letter is never touched, that the fit measures the same text that is drawn, and
that nothing about the session changes when the level does.

Like the GUI smoke tests, these need a Tk display and skip when there is none.
They build their own small window rather than the whole app, because the reader
is all they need. Nothing is read from or written to the real settings.

Most tests give the reader a fixed table of gap widths (the ones measured for
Fredoka on Windows) instead of measuring the fonts of whatever machine runs the
tests. That keeps the plan, and so the expected text, the same everywhere. Two
tests at the end do measure for real, to check the measuring itself."""

import tkinter

import pytest

from core.letter_spacing import (
    GAP_UNIT_CHARS, HAIR_SPACE, LEVEL_NAMES, MAX_LEVEL, PLAIN_SPACE, build_plan, space_chunk,
)
from core.reader import ReaderSession, assemble_chunk_text

# Measured per gap between two letters, in em, for Fredoka SemiBold on Windows:
# the same table test_letter_spacing.py uses.
FIXED_WIDTHS = {
    chr(0x2008): 0.333,   # punctuation space
    chr(0x2006): 0.188,   # six-per-em space
    chr(0x2009): 0.146,   # thin space
    chr(0x200A): 0.083,   # hair space
    PLAIN_SPACE: 0.250,
}

TEXT = "reading is fun and alpha bravo charlie delta"


@pytest.fixture(scope="module")
def root():
    import customtkinter as ctk

    try:
        window = ctk.CTk()
    except tkinter.TclError as exc:
        pytest.skip(f"Tk can't start a display here: {exc}")
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def reader(root, monkeypatch):
    from gui.components.reader_display import ReaderDisplay

    monkeypatch.setattr(ReaderDisplay, "_measure_gap_widths_em", lambda self: dict(FIXED_WIDTHS))
    display = ReaderDisplay(root)
    display.pack(fill="both", expand=True)
    root.update_idletasks()
    yield display
    display.destroy()


def _load(reader, text=TEXT, chunk_size=None, start_index=0):
    """Open a paused session, so no timer is ever scheduled."""
    session = ReaderSession(
        text, start_index=start_index,
        chunk_enabled=chunk_size is not None, chunk_size=chunk_size or 2,
    )
    reader.load_session(session, start_paused=True)
    return session


def _drawn(reader):
    return (
        reader.before_label.cget("text"),
        reader.focus_label.cget("text"),
        reader.after_label.cget("text"),
    )


def _plain(session):
    return assemble_chunk_text(session.current_chunk())


def _gap_characters_removed(text):
    return "".join(char for char in text if char not in GAP_UNIT_CHARS)


# ---- Off, the default ----

def test_letter_spacing_starts_off(reader):
    assert reader.letter_spacing_level == 0
    assert reader._spacing_plan.is_off

def test_with_spacing_off_the_drawn_text_is_exactly_the_plain_text(reader):
    session = _load(reader)
    assert _drawn(reader) == _plain(session)

def test_going_back_to_off_needs_no_measuring(reader, monkeypatch):
    _load(reader)
    reader.set_letter_spacing(2)

    def fail(self):
        raise AssertionError("measured although spacing is off")

    monkeypatch.setattr(type(reader), "_measure_gap_widths_em", fail)
    monkeypatch.setattr(reader, "_gap_widths_em", None)  # forget the earlier measuring
    reader.set_letter_spacing(0)
    assert reader._spacing_plan.is_off


# ---- The drawn text ----

@pytest.mark.parametrize("level", range(1, MAX_LEVEL + 1))
def test_each_level_draws_the_text_the_plan_describes(reader, level):
    session = _load(reader)
    reader.set_letter_spacing(level)
    plan = build_plan(level, FIXED_WIDTHS)
    assert _drawn(reader) == space_chunk(*_plain(session), plan)

@pytest.mark.parametrize("level", range(1, MAX_LEVEL + 1))
def test_the_focus_letter_is_never_touched(reader, level):
    session = _load(reader)
    reader.set_letter_spacing(level)
    assert reader.focus_label.cget("text") == _plain(session)[1]

@pytest.mark.parametrize("level", range(1, MAX_LEVEL + 1))
def test_taking_the_gaps_out_gives_back_the_plain_text(reader, level):
    session = _load(reader)
    reader.set_letter_spacing(level)
    before, focus, after = _drawn(reader)
    plain_before, plain_focus, plain_after = _plain(session)
    assert _gap_characters_removed(before) == plain_before
    assert focus == plain_focus
    assert _gap_characters_removed(after) == plain_after

def test_a_spaced_word_really_has_the_gap_characters_in_it(reader):
    _load(reader)
    reader.set_letter_spacing(1)
    before, _, after = _drawn(reader)
    assert HAIR_SPACE in before
    assert HAIR_SPACE in after

def test_a_higher_level_draws_a_longer_gap_than_a_lower_one(reader):
    _load(reader)
    reader.set_letter_spacing(1)
    small = reader._spacing_plan.letter_gap_em
    reader.set_letter_spacing(3)
    large = reader._spacing_plan.letter_gap_em
    assert large > small > 0

def test_going_back_to_off_restores_the_plain_text_exactly(reader):
    session = _load(reader)
    plain = _plain(session)
    reader.set_letter_spacing(3)
    assert _drawn(reader) != plain
    reader.set_letter_spacing(0)
    assert _drawn(reader) == plain

def test_the_next_word_is_spaced_too(reader):
    session = _load(reader)
    reader.set_letter_spacing(2)
    session.advance()
    reader._show_current_frame()
    plan = build_plan(2, FIXED_WIDTHS)
    assert _drawn(reader) == space_chunk(*_plain(session), plan)

def test_a_one_letter_word_has_nothing_to_space(reader):
    session = _load(reader, text="a")
    reader.set_letter_spacing(3)
    assert _drawn(reader) == _plain(session)

def test_the_finished_message_is_not_spaced(reader):
    session = _load(reader, text="one two")
    reader.set_letter_spacing(3)
    while not session.is_finished:
        session.advance()
    reader._show_current_frame()
    assert reader.before_label.cget("text") == "(finished)"


# ---- Chunks: wider gaps between words ----

def test_in_a_chunk_the_words_are_apart_by_the_word_gap(reader):
    session = _load(reader, chunk_size=3)
    reader.set_letter_spacing(3)
    plan = build_plan(3, FIXED_WIDTHS)
    assert plan.word_gap != PLAIN_SPACE  # at Large the plain space alone is too narrow
    _, _, after = _drawn(reader)
    assert plan.word_gap in after
    assert _drawn(reader) == space_chunk(*_plain(session), plan)

def test_in_a_chunk_a_word_gap_is_wider_than_a_letter_gap(reader):
    _load(reader, chunk_size=3)
    for level in range(1, MAX_LEVEL + 1):
        reader.set_letter_spacing(level)
        plan = reader._spacing_plan
        assert plan.word_gap_em > plan.letter_gap_em


# ---- The level can be set at any time ----

def test_the_level_can_be_set_before_a_session_is_loaded(reader):
    reader.set_letter_spacing(2)
    session = _load(reader)
    plan = build_plan(2, FIXED_WIDTHS)
    assert _drawn(reader) == space_chunk(*_plain(session), plan)

def test_a_level_that_is_not_valid_is_pulled_to_the_nearest_one(reader):
    reader.set_letter_spacing(99)
    assert reader.letter_spacing_level == MAX_LEVEL
    reader.set_letter_spacing(-4)
    assert reader.letter_spacing_level == 0

@pytest.mark.parametrize("not_a_level", [None, "2", 1.5, True])
def test_something_that_is_not_a_whole_number_means_off(reader, not_a_level):
    reader.set_letter_spacing(2)
    reader.set_letter_spacing(not_a_level)
    assert reader.letter_spacing_level == 0
    assert reader._spacing_plan.is_off

def test_asking_for_the_level_that_is_already_set_does_nothing(reader, monkeypatch):
    _load(reader)
    reader.set_letter_spacing(2)
    calls = []
    monkeypatch.setattr(reader, "_recompute_fit_widest", lambda: calls.append("fit"))
    monkeypatch.setattr(reader, "_show_current_frame", lambda: calls.append("frame"))
    reader.set_letter_spacing(2)
    assert calls == []

def test_changing_the_level_leaves_the_session_alone(reader):
    session = _load(reader, start_index=3)
    reader.set_letter_spacing(2)
    reader.set_letter_spacing(3)
    assert session.index == 3
    assert reader.session is session
    assert reader._is_paused is True
    assert reader._after_id is None  # still no timer: a paused reader stays paused

def test_changing_the_level_does_not_disturb_a_session_that_is_running(reader):
    # A reader that is playing keeps its timer: the level changes what is drawn
    # and nothing else, so the next word still arrives when it was due.
    session = ReaderSession(TEXT)
    reader.load_session(session)
    try:
        timer = reader._after_id
        assert timer is not None
        reader.set_letter_spacing(2)
        reader.set_letter_spacing(3)
        assert reader._after_id == timer
        assert session.index == 0
        assert reader._is_paused is False
    finally:
        reader._cancel_pending()

def test_the_level_stays_when_another_session_is_loaded(reader):
    _load(reader)
    reader.set_letter_spacing(2)
    session = _load(reader, text="something entirely different")
    plan = build_plan(2, FIXED_WIDTHS)
    assert _drawn(reader) == space_chunk(*_plain(session), plan)

def test_the_gap_characters_are_measured_once_not_for_every_change(reader, monkeypatch):
    measured = []

    def counting(self):
        measured.append(1)
        return dict(FIXED_WIDTHS)

    monkeypatch.setattr(type(reader), "_measure_gap_widths_em", counting)
    _load(reader)
    for level in (1, 2, 3, 0, 2, 1, 3):
        reader.set_letter_spacing(level)
    assert len(measured) == 1

def test_the_gap_characters_are_measured_again_if_the_font_changes(reader, monkeypatch):
    measured = []

    def counting(self):
        measured.append(1)
        return dict(FIXED_WIDTHS)

    monkeypatch.setattr(type(reader), "_measure_gap_widths_em", counting)
    reader.set_letter_spacing(1)
    reader.word_font.configure(family="Courier")
    reader.set_letter_spacing(2)
    assert len(measured) == 2


# ---- The fit measures what is drawn ----

def test_the_widest_chunk_is_measured_with_the_spacing_in_it(reader):
    _load(reader, text="reading")
    reader.set_letter_spacing(2)
    plan = build_plan(2, FIXED_WIDTHS)
    # One chunk only, so the widest chunk is the one on screen: what the fit
    # measured is exactly what was drawn.
    assert reader._fit_widest == _drawn(reader)
    assert plan.letter_gap in reader._fit_widest[0]

def test_the_widest_chunk_is_still_found_among_many_with_spacing_on(reader):
    # More chunks than the fit shortlists, with the one long word buried in the
    # middle, so finding it depends on the shortlist and not on there being few.
    words = ["go"] * 20 + ["extraordinarily"] + ["go"] * 5
    _load(reader, text=" ".join(words))
    reader.set_letter_spacing(2)
    before, focus, after = reader._fit_widest
    assert _gap_characters_removed(before + focus + after) == "extraordinarily"

def test_a_wider_level_needs_more_room_per_unit_of_font_size(reader):
    _load(reader)
    needs = []
    for level in range(MAX_LEVEL + 1):
        reader.set_letter_spacing(level)
        needs.append(reader._fit_required_per_size)
    assert needs == sorted(needs)
    assert needs[-1] > needs[0]

def test_the_reach_on_each_side_grows_with_the_spacing(reader):
    _load(reader, text="reading")
    reader.set_letter_spacing(0)
    plain_left, plain_right = reader._fit_left_reach_per_size, reader._fit_right_reach_per_size
    reader.set_letter_spacing(3)
    assert reader._fit_left_reach_per_size > plain_left
    assert reader._fit_right_reach_per_size > plain_right

def test_turning_spacing_off_gives_back_the_original_fit(reader):
    _load(reader)
    plain = (reader._fit_required_per_size, reader._fit_left_reach_per_size, reader._fit_right_reach_per_size)
    reader.set_letter_spacing(3)
    reader.set_letter_spacing(0)
    assert (reader._fit_required_per_size, reader._fit_left_reach_per_size, reader._fit_right_reach_per_size) == plain

def test_the_render_size_never_goes_above_the_chosen_size_or_below_the_floor(reader):
    _load(reader)
    reader.set_font_size(60)
    for level in range(MAX_LEVEL + 1):
        reader.set_letter_spacing(level)
        size = reader.word_font.cget("size")
        assert round(60 * reader.FIT_FLOOR_RATIO) <= size <= 60

def test_the_chosen_word_size_is_left_alone(reader):
    _load(reader)
    reader.set_font_size(60)
    reader.set_letter_spacing(3)
    assert reader._chosen_font_size == 60


# ---- Measuring the real font ----
# These two use the real measuring, so they only check what has to be true of
# any font, not particular numbers.

def test_measured_widths_cover_the_plain_space_and_every_gap_character(root):
    from gui.components.reader_display import ReaderDisplay

    display = ReaderDisplay(root)
    try:
        widths = display._measure_gap_widths_em()
    finally:
        display.destroy()
    assert set(widths) == {PLAIN_SPACE, *GAP_UNIT_CHARS}
    for char, width in widths.items():
        assert 0 <= width < 1.5, f"{char!r} measured {width} em"
    assert widths[PLAIN_SPACE] > 0

def test_a_spaced_word_measures_wider_in_the_real_font_than_the_plain_one(root):
    from gui.components.reader_display import ReaderDisplay

    display = ReaderDisplay(root)
    try:
        session = ReaderSession("reading")
        display.load_session(session, start_paused=True)
        plain_need = display._fit_required_per_size
        display.set_letter_spacing(MAX_LEVEL)
        spaced_need = display._fit_required_per_size
        top = display._spacing_plan
    finally:
        display.destroy()
    assert not top.is_off, "no gap character measured as usable in this font"
    assert spaced_need > plain_need

def test_every_level_has_a_name_in_core(reader):
    assert len(LEVEL_NAMES) == MAX_LEVEL + 1