import pytest
from core.timing import (
    wpm_to_delay_ms, apply_pacing_multiplier, apply_length_multiplier,
    effective_pacing_length, HYPHEN_PACING_BONUS_CHARS,
)
from core.punctuation import PACE_NONE, PACE_CLAUSE, PACE_SENTENCE


def test_300_wpm_gives_200ms():
    assert wpm_to_delay_ms(300) == 200


def test_200_wpm_gives_300ms():
    assert wpm_to_delay_ms(200) == 300


def test_400_wpm_gives_150ms():
    assert wpm_to_delay_ms(400) == 150


def test_600_wpm_gives_100ms():
    assert wpm_to_delay_ms(600) == 100


def test_minimum_app_wpm_100_gives_600ms():
    assert wpm_to_delay_ms(100) == 600


def test_maximum_app_wpm_1000_gives_60ms():
    assert wpm_to_delay_ms(1000) == 60


def test_rounds_rather_than_truncates():
    assert wpm_to_delay_ms(700) == 86


def test_zero_wpm_raises_value_error():
    with pytest.raises(ValueError):
        wpm_to_delay_ms(0)


def test_negative_wpm_raises_value_error():
    with pytest.raises(ValueError):
        wpm_to_delay_ms(-50)


def test_higher_wpm_gives_shorter_delay():
    assert wpm_to_delay_ms(600) < wpm_to_delay_ms(300)


# ---- apply_pacing_multiplier: PACE_NONE leaves the delay unchanged ----

def test_pace_none_returns_base_delay_unchanged():
    assert apply_pacing_multiplier(200, PACE_NONE) == 200


# ---- apply_pacing_multiplier: the two documented multipliers ----

def test_pace_clause_multiplies_by_1_5():
    assert apply_pacing_multiplier(200, PACE_CLAUSE) == 300

def test_pace_sentence_multiplies_by_2_5():
    assert apply_pacing_multiplier(200, PACE_SENTENCE) == 500

def test_pace_sentence_pause_is_longer_than_pace_clause_pause():
    base = 200
    assert apply_pacing_multiplier(base, PACE_SENTENCE) > apply_pacing_multiplier(base, PACE_CLAUSE)

def test_apply_pacing_multiplier_rounds_rather_than_truncates():
    # 89 * 1.5 == 133.5 exactly -- round() takes this to 134 (Python
    # rounds a halfway value to the nearest even integer); a truncating
    # implementation would have given 133 instead.
    assert apply_pacing_multiplier(89, PACE_CLAUSE) == 134


# ---- apply_pacing_multiplier: unrecognized pace values degrade safely ----

def test_apply_pacing_multiplier_unrecognized_pace_falls_back_to_base_delay():
    # Anything that isn't PACE_SENTENCE or PACE_CLAUSE -- including a
    # value that doesn't come from core/punctuation.py at all -- is
    # treated as "no extra pause" rather than raising, so an
    # unrecognized or future pacing value can't crash playback.
    assert apply_pacing_multiplier(200, "not-a-real-pace") == 200


# ---- apply_length_multiplier: bands 0 and 1 leave the delay unchanged ----

def test_length_band_0_returns_base_delay_unchanged():
    assert apply_length_multiplier(200, 0) == 200

def test_length_band_1_returns_base_delay_unchanged():
    assert apply_length_multiplier(200, 1) == 200


# ---- apply_length_multiplier: the three active bands ----
# Values updated alongside MEDIUM/LONG/VERY_LONG_WORD_MULTIPLIER's
# general raise (1.15/1.3/1.5 -> 1.2/1.45/1.7) -- see core/timing.py.

def test_length_band_2_multiplies_by_1_2():
    assert apply_length_multiplier(200, 2) == 240

def test_length_band_3_multiplies_by_1_45():
    assert apply_length_multiplier(200, 3) == 290

def test_length_band_4_multiplies_by_1_7():
    assert apply_length_multiplier(200, 4) == 340

def test_length_multiplier_increases_with_band():
    base = 200
    assert (
        apply_length_multiplier(base, 1)
        < apply_length_multiplier(base, 2)
        < apply_length_multiplier(base, 3)
        < apply_length_multiplier(base, 4)
    )


# ---- apply_length_multiplier: bands at or above 4 all get the top multiplier ----

def test_length_band_beyond_4_still_gets_top_multiplier():
    # get_orp_index() never actually returns anything above 4 today, but
    # this is checked with >= rather than a fixed upper bound specifically
    # so a value beyond that doesn't silently fall through to "no extra
    # pause" -- see the docstring.
    assert apply_length_multiplier(200, 5) == 340


# ---- apply_length_multiplier: unrecognized/out-of-range bands degrade safely ----

def test_length_negative_band_falls_back_to_base_delay():
    assert apply_length_multiplier(200, -1) == 200


# ---- effective_pacing_length: hyphen-aware effective length for pacing ----

def test_effective_pacing_length_matches_len_for_a_plain_word():
    assert effective_pacing_length("understanding") == len("understanding")

def test_effective_pacing_length_for_empty_string_is_zero():
    assert effective_pacing_length("") == 0

def test_effective_pacing_length_adds_bonus_for_one_internal_hyphen():
    assert effective_pacing_length("sub-terrain") == len("sub-terrain") + HYPHEN_PACING_BONUS_CHARS

def test_effective_pacing_length_adds_bonus_per_hyphen_for_multiple_hyphens():
    # "step-by-step" has two internal hyphens -- each one counts, so this
    # gets two bonuses, not one.
    assert effective_pacing_length("step-by-step") == len("step-by-step") + 2 * HYPHEN_PACING_BONUS_CHARS

def test_effective_pacing_length_is_strictly_greater_than_len_when_hyphenated():
    # A structural guarantee: whatever HYPHEN_PACING_BONUS_CHARS is tuned
    # to later, a hyphenated word's effective length must never come out
    # equal to or below its own raw length.
    word = "well-known"
    assert effective_pacing_length(word) > len(word)