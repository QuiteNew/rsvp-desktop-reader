from core.punctuation import PACE_SENTENCE, PACE_CLAUSE

# Multipliers applied on top of the flat per-word delay when a word's
# punctuation marks a sentence or clause boundary -- see
# core/punctuation.py for how a word's pacing class gets decided, and
# core/reader.py for where this actually gets called from.
#
# Multipliers, not a flat number of added milliseconds, because a flat
# +200ms would be nearly invisible at 1000 WPM (a ~60ms base delay per
# word) and disproportionately huge at 100 WPM (~600ms base) -- a
# multiplier keeps the pause feeling the same relative size across the
# whole speed range Settings allows (see WPM_RANGE in settings_store.py).
# Starting values, not tuned against real reading yet -- trivial to
# adjust, since nothing else depends on the exact numbers.
SENTENCE_PAUSE_MULTIPLIER = 2.5
CLAUSE_PAUSE_MULTIPLIER = 1.5


def wpm_to_delay_ms(wpm: int) -> int:
    """Convert a words-per-minute rate into a per-word delay in milliseconds."""
    if wpm <= 0:
        raise ValueError("WPM must be greater than zero")
    return round(60000 / wpm)


def apply_pacing_multiplier(base_delay_ms: int, pace: str) -> int:
    """Scale a base per-word delay up for a word that ends a sentence or
    clause. pace is expected to be PACE_SENTENCE / PACE_CLAUSE / PACE_NONE
    (core/punctuation.py); anything else -- including PACE_NONE -- is
    treated as "no extra pause" rather than raising, so an unrecognized
    or future pacing value degrades safely instead of crashing playback."""
    if pace == PACE_SENTENCE:
        return round(base_delay_ms * SENTENCE_PAUSE_MULTIPLIER)
    if pace == PACE_CLAUSE:
        return round(base_delay_ms * CLAUSE_PAUSE_MULTIPLIER)
    return base_delay_ms


if __name__ == "__main__":
    for test_wpm in [200, 300, 400, 600]:
        delay = wpm_to_delay_ms(test_wpm)
        print(f"{test_wpm} WPM -> {delay} ms per word")