"""Tests for core/letter_spacing.py, the pure part of the reader's letter
spacing: picking the gap characters for a level from measured widths, and
putting the gaps into the text of a flash."""

import pytest

from core.letter_spacing import (
    GAP_UNIT_CHARS, HAIR_SPACE, LEVEL_GAP_EM, LEVEL_NAMES, MAX_GAP_CHARS, MAX_LEVEL, NO_SPACING,
    PLAIN_SPACE, PUNCTUATION_SPACE, SIX_PER_EM_SPACE, THIN_SPACE, WORD_GAP_RATIO,
    SpacingPlan, build_plan, choose_gap, clamp_level, gap_width_em, space_chunk, space_text,
)

HAIR, SIX, THIN, PUNCT = HAIR_SPACE, SIX_PER_EM_SPACE, THIN_SPACE, PUNCTUATION_SPACE
ALL_GAP_CHARS = set(GAP_UNIT_CHARS)

# Widths in em, from the Windows probe run on 17.10.2026 (a 48px font, so each
# one is good to about a hundredth of an em). They stand in for real fonts here
# so the tests don't need a window.
FREDOKA = {HAIR: 0.083, SIX: 0.188, THIN: 0.146, PUNCT: 0.333, PLAIN_SPACE: 0.250}
QUICKSAND = {HAIR: 0.104, SIX: 0.167, THIN: 0.208, PUNCT: 0.250, PLAIN_SPACE: 0.271}
OPENDYSLEXIC = {HAIR: 0.062, SIX: 0.167, THIN: 0.125, PUNCT: 0.312, PLAIN_SPACE: 0.854}
OPENDYSLEXIC_BOLD = {HAIR: 0.083, SIX: 0.188, THIN: 0.146, PUNCT: 0.333, PLAIN_SPACE: 0.854}
REAL_FONTS = [FREDOKA, QUICKSAND, OPENDYSLEXIC, OPENDYSLEXIC_BOLD]

# A made-up font where every gap character is easy to add up.
EASY = {HAIR: 0.05, SIX: 0.10, THIN: 0.20, PUNCT: 0.30, PLAIN_SPACE: 0.25}


def _strip_gaps(text):
    for char in ALL_GAP_CHARS:
        text = text.replace(char, "")
    return text


# ---- The levels ----

def test_there_is_a_name_and_a_gap_for_every_level():
    assert len(LEVEL_NAMES) == len(LEVEL_GAP_EM) == MAX_LEVEL + 1

def test_level_zero_is_off_with_no_gap():
    assert LEVEL_NAMES[0] == "Off"
    assert LEVEL_GAP_EM[0] == 0

def test_each_level_asks_for_a_wider_gap_than_the_one_before():
    for narrower, wider in zip(LEVEL_GAP_EM, LEVEL_GAP_EM[1:]):
        assert narrower < wider

def test_the_gap_characters_are_all_distinct_single_characters():
    assert len(set(GAP_UNIT_CHARS)) == len(GAP_UNIT_CHARS)
    assert all(len(char) == 1 for char in GAP_UNIT_CHARS)

def test_a_plain_space_is_not_one_of_the_gap_characters():
    assert PLAIN_SPACE not in GAP_UNIT_CHARS


# ---- clamp_level ----

@pytest.mark.parametrize("level, expected", [(0, 0), (1, 1), (MAX_LEVEL, MAX_LEVEL)])
def test_a_level_inside_the_range_is_kept(level, expected):
    assert clamp_level(level) == expected

def test_a_level_outside_the_range_is_pulled_in():
    assert clamp_level(-4) == 0
    assert clamp_level(MAX_LEVEL + 10) == MAX_LEVEL

@pytest.mark.parametrize("junk", [None, "2", 1.5, True, False, [], {}])
def test_anything_that_is_not_a_whole_number_means_off(junk):
    assert clamp_level(junk) == 0


# ---- gap_width_em ----

def test_a_gap_is_as_wide_as_its_characters_added_up():
    assert gap_width_em(HAIR + THIN, EASY) == pytest.approx(0.25)

def test_an_empty_gap_has_no_width():
    assert gap_width_em("", EASY) == 0

def test_a_character_with_no_measured_width_counts_as_nothing():
    assert gap_width_em(HAIR + "x", EASY) == pytest.approx(0.05)


# ---- choose_gap ----

def test_an_exact_match_is_found():
    assert gap_width_em(choose_gap(0.30, EASY), EASY) == pytest.approx(0.30)

def test_two_characters_can_add_up_to_the_target():
    gap = choose_gap(0.25, EASY)
    assert gap_width_em(gap, EASY) == pytest.approx(0.25)

def test_the_closest_combination_wins_when_nothing_is_exact():
    gap = choose_gap(0.12, EASY)
    assert gap_width_em(gap, EASY) == pytest.approx(0.10)

def test_a_tie_goes_to_the_gap_with_fewer_characters():
    # 0.10 is one six-per-em space or two hair spaces. One character is simpler.
    assert choose_gap(0.10, EASY) == SIX

def test_a_target_of_zero_or_less_gives_no_gap():
    assert choose_gap(0, EASY) == ""
    assert choose_gap(-0.3, EASY) == ""

def test_a_target_smaller_than_half_the_narrowest_character_gives_no_gap():
    assert choose_gap(0.02, EASY) == ""

def test_no_usable_characters_means_no_gap():
    assert choose_gap(0.2, {}) == ""
    assert choose_gap(0.2, {HAIR: 0.0, SIX: 0.0}) == ""

def test_a_character_too_narrow_to_be_real_is_ignored():
    widths = {HAIR: 0.001, SIX: 0.10}
    assert choose_gap(0.10, widths) == SIX

def test_a_missing_glyph_never_turns_into_a_long_run_of_invisible_characters():
    # A character that measures as almost nothing would otherwise be repeated
    # to "add up" to a tiny target.
    assert choose_gap(0.003, {HAIR: 0.001}) == ""

def test_only_the_gap_characters_are_used():
    widths = dict(EASY)
    widths["x"] = 0.15
    assert set(choose_gap(0.15, widths)) <= ALL_GAP_CHARS

def test_the_gap_never_has_more_characters_than_allowed():
    assert len(choose_gap(5.0, EASY)) <= MAX_GAP_CHARS
    assert len(choose_gap(5.0, EASY, max_chars=2)) <= 2

def test_the_same_input_always_gives_the_same_gap():
    assert choose_gap(0.22, FREDOKA) == choose_gap(0.22, FREDOKA)


# ---- build_plan ----

def test_level_zero_changes_nothing():
    plan = build_plan(0, FREDOKA)
    assert plan.is_off
    assert plan.letter_gap == ""
    assert plan.word_gap == PLAIN_SPACE

def test_level_zero_still_reports_the_width_of_a_plain_space():
    assert build_plan(0, FREDOKA).word_gap_em == pytest.approx(0.25)

def test_the_no_spacing_plan_changes_nothing():
    assert NO_SPACING.is_off
    assert space_chunk("ab", "c", "de fg", NO_SPACING) == ("ab", "c", "de fg")

def test_a_level_that_is_out_of_range_is_clamped():
    assert build_plan(99, FREDOKA).level == MAX_LEVEL
    assert build_plan(-1, FREDOKA).level == 0
    assert build_plan("high", FREDOKA).level == 0

def test_a_font_with_no_usable_gap_characters_changes_nothing():
    plan = build_plan(2, {PLAIN_SPACE: 0.25})
    assert plan.is_off
    assert plan.level == 2

@pytest.mark.parametrize("widths", REAL_FONTS)
def test_every_level_lands_close_to_the_gap_it_asks_for(widths):
    for level in range(1, MAX_LEVEL + 1):
        plan = build_plan(level, widths)
        assert abs(plan.letter_gap_em - LEVEL_GAP_EM[level]) <= 0.04, (level, plan)

@pytest.mark.parametrize("widths", REAL_FONTS)
def test_a_higher_level_always_gives_a_wider_letter_gap(widths):
    gaps = [build_plan(level, widths).letter_gap_em for level in range(MAX_LEVEL + 1)]
    assert gaps == sorted(gaps)
    assert len(set(gaps)) == len(gaps)

@pytest.mark.parametrize("widths", REAL_FONTS)
def test_the_word_gap_stays_clearly_wider_than_the_letter_gap(widths):
    for level in range(1, MAX_LEVEL + 1):
        plan = build_plan(level, widths)
        assert plan.word_gap_em >= WORD_GAP_RATIO * plan.letter_gap_em - 0.04, (level, plan)

@pytest.mark.parametrize("widths", REAL_FONTS)
def test_the_word_gap_is_a_plain_space_with_gap_characters_after_it(widths):
    for level in range(1, MAX_LEVEL + 1):
        word_gap = build_plan(level, widths).word_gap
        assert word_gap[0] == PLAIN_SPACE
        assert set(word_gap[1:]) <= ALL_GAP_CHARS

def test_a_wide_plain_space_needs_nothing_added_to_the_word_gap():
    # OpenDyslexic's own space is about 0.85 em, wider than twice any level.
    for level in range(1, MAX_LEVEL + 1):
        assert build_plan(level, OPENDYSLEXIC).word_gap == PLAIN_SPACE

def test_a_narrow_plain_space_gets_extra_room_at_the_larger_levels():
    assert len(build_plan(MAX_LEVEL, FREDOKA).word_gap) > 1

def test_the_reported_widths_match_the_strings():
    plan = build_plan(2, QUICKSAND)
    assert plan.letter_gap_em == pytest.approx(gap_width_em(plan.letter_gap, QUICKSAND))
    assert plan.word_gap_em == pytest.approx(gap_width_em(plan.word_gap, QUICKSAND))

def test_a_plan_cannot_be_changed_after_it_is_made():
    with pytest.raises(Exception):
        build_plan(1, EASY).level = 3


# ---- space_text ----

def _plan(letter_gap="-", word_gap="_"):
    """A plan with easy-to-read stand-in gaps, so the tests can see exactly where
    each one lands."""
    return SpacingPlan(1, letter_gap, word_gap, 0.0, 0.0)

def test_the_letter_gap_goes_between_every_two_characters():
    assert space_text("word", _plan()) == "w-o-r-d"

def test_nothing_is_added_at_the_ends_of_a_word():
    spaced = space_text("ab", _plan())
    assert not spaced.startswith("-")
    assert not spaced.endswith("-")

def test_a_single_character_is_left_alone():
    assert space_text("a", _plan()) == "a"

def test_empty_text_stays_empty():
    assert space_text("", _plan()) == ""

def test_the_word_gap_replaces_the_space_between_words():
    assert space_text("ab cd", _plan()) == "a-b_c-d"

def test_no_letter_gap_is_added_next_to_a_word_gap():
    spaced = space_text("a b", _plan())
    assert spaced == "a_b"

def test_a_leading_space_becomes_a_word_gap():
    assert space_text(" ab", _plan()) == "_a-b"

def test_punctuation_is_spaced_like_a_letter():
    assert space_text("hi,", _plan()) == "h-i-,"

def test_text_is_unchanged_when_the_plan_is_off():
    assert space_text("some words here", NO_SPACING) == "some words here"

def test_taking_the_gaps_out_gives_back_the_original_text():
    plan = build_plan(MAX_LEVEL, FREDOKA)
    for text in ("reading", "a b c", " lead", "two words, here.", "x"):
        assert _strip_gaps(space_text(text, plan)).replace(PLAIN_SPACE, "") == text.replace(PLAIN_SPACE, "")


# ---- space_chunk ----

def test_the_focus_letter_is_never_changed():
    assert space_chunk("rea", "d", "ing", _plan())[1] == "d"

def test_the_focus_text_is_returned_exactly_as_given():
    # In practice it is one letter, but the rule is that it is never touched.
    assert space_chunk("x", "ab", "y", _plan())[1] == "ab"

def test_before_and_after_are_spaced_and_the_junctions_get_a_gap():
    assert space_chunk("rea", "d", "ing", _plan()) == ("r-e-a-", "d", "-i-n-g")

def test_a_word_that_starts_with_its_focus_letter_has_no_gap_on_the_left():
    assert space_chunk("", "t", "he", _plan()) == ("", "t", "-h-e")

def test_a_word_that_ends_with_its_focus_letter_has_no_gap_on_the_right():
    assert space_chunk("th", "e", "", _plan()) == ("t-h-", "e", "")

def test_a_one_letter_word_gets_no_gaps_at_all():
    assert space_chunk("", "a", "", _plan()) == ("", "a", "")

def test_a_chunk_spaces_each_of_its_trailing_words():
    assert space_chunk("", "t", "he cat", _plan()) == ("", "t", "-h-e_c-a-t")

def test_a_one_letter_first_word_leaves_the_room_to_the_word_gap():
    # The after text starts with the plain space between "a" and "cat", so the
    # word gap is the room, and no letter gap is added on top of it.
    assert space_chunk("", "a", " cat", _plan()) == ("", "a", "_c-a-t")

def test_a_chunk_that_is_off_comes_back_exactly_as_it_went_in():
    assert space_chunk("rea", "d", "ing and more", NO_SPACING) == ("rea", "d", "ing and more")

def test_the_before_text_never_gets_a_word_gap_it_did_not_have():
    # before is the front of the first word only, so it has no spaces in it.
    before, _, _ = space_chunk("abc", "d", "ef", _plan())
    assert "_" not in before

def test_the_letters_stay_in_order_for_real_plans():
    for widths in REAL_FONTS:
        plan = build_plan(2, widths)
        before, focus, after = space_chunk("rea", "d", "ing and more", plan)
        shown = (before + focus + after).replace(PLAIN_SPACE, "")
        assert _strip_gaps(shown) == "readingandmore"

def test_a_realistic_chunk_gets_wider_as_the_level_goes_up():
    widths = []
    for level in range(MAX_LEVEL + 1):
        before, focus, after = space_chunk("rea", "d", "ing and more", build_plan(level, QUICKSAND))
        widths.append(len(before + focus + after))
    assert widths == sorted(widths)
    assert widths[0] < widths[-1]