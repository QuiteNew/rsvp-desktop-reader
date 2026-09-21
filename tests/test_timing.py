import pytest
from core.timing import wpm_to_delay_ms, apply_pacing_multiplier
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