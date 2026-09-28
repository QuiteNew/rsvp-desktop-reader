import pytest
from core.timing import (
    wpm_to_delay_ms, apply_pacing_multiplier, apply_length_multiplier,
    effective_pacing_length, HYPHEN_PACING_BONUS_CHARS,
    warm_up_multiplier, apply_warm_up,
    WARM_UP_START_MULTIPLIER, WARM_UP_WORD_COUNT,
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


# apply_pacing_multiplier: PACE_NONE leaves the delay unchanged

def test_pace_none_returns_base_delay_unchanged():
    assert apply_pacing_multiplier(200, PACE_NONE) == 200


# apply_pacing_multiplier: the clause and sentence multipliers

def test_pace_clause_multiplies_by_1_5():
    assert apply_pacing_multiplier(200, PACE_CLAUSE) == 300

def test_pace_sentence_multiplies_by_2_5():
    assert apply_pacing_multiplier(200, PACE_SENTENCE) == 500

def test_pace_sentence_pause_is_longer_than_pace_clause_pause():
    base = 200
    assert apply_pacing_multiplier(base, PACE_SENTENCE) > apply_pacing_multiplier(base, PACE_CLAUSE)

def test_apply_pacing_multiplier_rounds_rather_than_truncates():
    # 89 * 1.5 is exactly 133.5. round() gives 134, because Python rounds
    # a halfway value to the nearest even number. Truncating would have
    # given 133.
    assert apply_pacing_multiplier(89, PACE_CLAUSE) == 134


# apply_pacing_multiplier: unknown pace values fall back safely

def test_apply_pacing_multiplier_unrecognized_pace_falls_back_to_base_delay():
    # Anything that isn't PACE_SENTENCE or PACE_CLAUSE, even a value that
    # doesn't come from core/punctuation.py, is treated as no extra pause
    # instead of raising. That way an unknown or future pacing value can't
    # crash playback.
    assert apply_pacing_multiplier(200, "not-a-real-pace") == 200


# apply_length_multiplier: bands 0 and 1 leave the delay unchanged

def test_length_band_0_returns_base_delay_unchanged():
    assert apply_length_multiplier(200, 0) == 200

def test_length_band_1_returns_base_delay_unchanged():
    assert apply_length_multiplier(200, 1) == 200


# apply_length_multiplier: the three active bands
# The expected values follow MEDIUM_WORD_MULTIPLIER, LONG_WORD_MULTIPLIER
# and VERY_LONG_WORD_MULTIPLIER (1.2, 1.45 and 1.7) in core/timing.py.

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


# apply_length_multiplier: band 4 and above all get the top multiplier

def test_length_band_beyond_4_still_gets_top_multiplier():
    # get_orp_index() never returns more than 4 today. The check uses >=
    # instead of a fixed upper bound so a higher value doesn't quietly
    # fall through to no extra pause. See the docstring.
    assert apply_length_multiplier(200, 5) == 340


# apply_length_multiplier: out of range bands fall back safely

def test_length_negative_band_falls_back_to_base_delay():
    assert apply_length_multiplier(200, -1) == 200


# effective_pacing_length: word length for pacing, with hyphens counted

def test_effective_pacing_length_matches_len_for_a_plain_word():
    assert effective_pacing_length("understanding") == len("understanding")

def test_effective_pacing_length_for_empty_string_is_zero():
    assert effective_pacing_length("") == 0

def test_effective_pacing_length_adds_bonus_for_one_internal_hyphen():
    assert effective_pacing_length("sub-terrain") == len("sub-terrain") + HYPHEN_PACING_BONUS_CHARS

def test_effective_pacing_length_adds_bonus_per_hyphen_for_multiple_hyphens():
    # "step-by-step" has two hyphens inside it, and each one counts, so it
    # gets two bonuses.
    assert effective_pacing_length("step-by-step") == len("step-by-step") + 2 * HYPHEN_PACING_BONUS_CHARS

def test_effective_pacing_length_is_strictly_greater_than_len_when_hyphenated():
    # Whatever HYPHEN_PACING_BONUS_CHARS is later tuned to, a hyphenated
    # word's effective length must always be more than its raw length.
    word = "well-known"
    assert effective_pacing_length(word) > len(word)


# warm_up_multiplier: the ease-in ramp, linear from the start multiplier
# down to 1.0 over WARM_UP_WORD_COUNT words. Expressed against the constants
# so the tests can't drift if those are later tuned.

def test_warm_up_multiplier_starts_at_the_start_multiplier():
    assert warm_up_multiplier(0) == WARM_UP_START_MULTIPLIER

def test_warm_up_multiplier_reaches_one_at_the_ramp_end():
    assert warm_up_multiplier(WARM_UP_WORD_COUNT) == 1.0

def test_warm_up_multiplier_stays_one_past_the_ramp_end():
    assert warm_up_multiplier(WARM_UP_WORD_COUNT + 50) == 1.0

def test_warm_up_multiplier_negative_words_clamp_to_the_start_multiplier():
    # A negative count should never speed the reader up past the target
    # rate; it clamps to the slowest (start) multiplier instead.
    assert warm_up_multiplier(-5) == WARM_UP_START_MULTIPLIER

def test_warm_up_multiplier_is_halfway_at_the_ramp_midpoint():
    # Linear ramp: halfway through the word count, the multiplier is halfway
    # between the start multiplier and 1.0.
    midpoint = WARM_UP_WORD_COUNT // 2
    expected = 1.0 + (WARM_UP_START_MULTIPLIER - 1.0) * ((WARM_UP_WORD_COUNT - midpoint) / WARM_UP_WORD_COUNT)
    assert warm_up_multiplier(midpoint) == pytest.approx(expected)

def test_warm_up_multiplier_decreases_monotonically_across_the_ramp():
    values = [warm_up_multiplier(w) for w in range(0, WARM_UP_WORD_COUNT + 1)]
    assert all(earlier >= later for earlier, later in zip(values, values[1:]))
    assert values[0] > values[-1]


# apply_warm_up: multiplies a delay by the ramp, rounded

def test_apply_warm_up_at_start_scales_by_the_start_multiplier():
    assert apply_warm_up(200, 0) == round(200 * WARM_UP_START_MULTIPLIER)

def test_apply_warm_up_after_ramp_leaves_delay_unchanged():
    assert apply_warm_up(200, WARM_UP_WORD_COUNT) == 200

def test_apply_warm_up_never_shortens_the_delay():
    # Warm-up only ever slows the start down; the returned delay is always
    # at least the delay passed in, for any point in (or past) the ramp.
    for words in range(0, WARM_UP_WORD_COUNT + 5):
        assert apply_warm_up(200, words) >= 200