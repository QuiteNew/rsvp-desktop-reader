from core.punctuation import PACE_SENTENCE, PACE_CLAUSE

# Multipliers applied on top of the flat per-word delay when a word's
# punctuation marks a sentence or clause boundary. See core/punctuation.py
# for how a word's pacing class gets decided, and core/reader.py for
# where this gets called from.
#
# These are multipliers rather than a flat number of added milliseconds
# because a flat +200ms would be nearly invisible at 1000 WPM (a ~60ms
# base delay per word) and disproportionately huge at 100 WPM (~600ms
# base). A multiplier keeps the pause feeling the same relative size
# across the whole speed range Settings allows (see WPM_RANGE in
# settings_store.py).
#
# Starting values that haven't been tuned against real reading yet,
# and trivial to adjust since nothing else depends on the exact numbers.
SENTENCE_PAUSE_MULTIPLIER = 2.5
CLAUSE_PAUSE_MULTIPLIER = 1.5

# Multipliers applied on top of the flat per-word delay for a long
# word, when length-aware pacing is enabled (see core/reader.py's
# length_pacing_enabled). The three bands reuse the same length
# boundaries core/orp.py's get_orp_index() already uses for the ORP
# letter (<=5, <=9, <=13, 14+). The two shortest bands share the same
# "no extra pause" treatment, since a 1-letter word doesn't need more
# reading time than a 5-letter one.
#
# Kept gentler than the punctuation multipliers above (1.2-1.7x vs
# 1.5-2.5x), because only the larger of the two ever applies to the
# same word (see core/reader.py's current_delay_ms()). That keeps
# VERY_LONG_WORD_MULTIPLIER safely below SENTENCE_PAUSE_MULTIPLIER, so
# a sentence-ending pause always wins over even the longest word.
#
# Starting values that haven't been tuned against real reading yet,
# and trivial to adjust since nothing else depends on the exact numbers.
MEDIUM_WORD_MULTIPLIER = 1.2     # length band 2 (6-9 letters)
LONG_WORD_MULTIPLIER = 1.45      # length band 3 (10-13 letters)
VERY_LONG_WORD_MULTIPLIER = 1.7  # length band 4 (14+ letters)

# How many extra characters a word's internal hyphens count for when
# computing its length band for pacing (see effective_pacing_length()
# below). Doesn't affect ORP letter placement, which stays unchanged.
# A hyphenated compound like "sub-terrain" reads more like two words
# stitched together than a single word of the same length, so it earns
# extra effective length per hyphen, pushing it into a higher pacing
# band sooner. Applied per hyphen, so "step-by-step" counts twice.
#
# A starting value that hasn't been tuned against real reading yet,
# and trivial to adjust since nothing else depends on the exact number.
HYPHEN_PACING_BONUS_CHARS = 4


def wpm_to_delay_ms(wpm: int) -> int:
    """Convert a words-per-minute rate into a per-word delay in milliseconds."""
    if wpm <= 0:
        raise ValueError("WPM must be greater than zero")
    return round(60000 / wpm)


def apply_pacing_multiplier(base_delay_ms: int, pace: str) -> int:
    """Scale a base per-word delay up for a word that ends a sentence or
    clause. pace is expected to be PACE_SENTENCE, PACE_CLAUSE, or
    PACE_NONE (core/punctuation.py). Anything else, including PACE_NONE,
    is treated as "no extra pause" rather than raising, so an
    unrecognized or future pacing value degrades safely instead of
    crashing playback."""
    if pace == PACE_SENTENCE:
        return round(base_delay_ms * SENTENCE_PAUSE_MULTIPLIER)
    if pace == PACE_CLAUSE:
        return round(base_delay_ms * CLAUSE_PAUSE_MULTIPLIER)
    return base_delay_ms


def effective_pacing_length(word: str) -> int:
    """The character length to use when banding a word for length-aware
    pacing: its actual length, plus HYPHEN_PACING_BONUS_CHARS for each
    internal hyphen. Kept separate from the word's real len(), which
    core/orp.py's get_orp_index() still uses unchanged for the ORP
    highlight letter. This function only feeds get_orp_index_for_length()
    for pacing (see core/reader.py), so inflating it here never shifts
    which letter gets highlighted."""
    return len(word) + HYPHEN_PACING_BONUS_CHARS * word.count("-")


def apply_length_multiplier(base_delay_ms: int, length_band: int) -> int:
    """Scale a base per-word delay up for a long word. length_band is
    expected to be an ORP band index (core/orp.py's get_orp_index(),
    0-4), checked from the top down with >= and == rather than a fixed
    upper bound. That way anything at or above band 4 still gets the top
    multiplier, and anything below band 2, including an unexpected
    negative value, degrades safely to "no extra pause" rather than
    raising."""
    if length_band >= 4:
        return round(base_delay_ms * VERY_LONG_WORD_MULTIPLIER)
    if length_band == 3:
        return round(base_delay_ms * LONG_WORD_MULTIPLIER)
    if length_band == 2:
        return round(base_delay_ms * MEDIUM_WORD_MULTIPLIER)
    return base_delay_ms


if __name__ == "__main__":
    for test_wpm in [200, 300, 400, 600]:
        delay = wpm_to_delay_ms(test_wpm)
        print(f"{test_wpm} WPM -> {delay} ms per word")