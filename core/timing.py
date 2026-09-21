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

# Multipliers applied on top of the flat per-word delay for a long word,
# when length-aware pacing is enabled (see core/reader.py's
# length_pacing_enabled). The three bands reuse the exact same length
# boundaries core/orp.py's get_orp_index() already established for
# picking a word's ORP letter (<=5, <=9, <=13, 14+) -- see
# core/reader.py for where a word's length band gets computed. The two
# shortest ORP bands (length <=5) share the same "no extra pause"
# treatment: distinguishing a 1-letter word from a 5-letter word doesn't
# earn either of them more reading time.
#
# Deliberately still gentler than the punctuation multipliers above
# (1.2-1.7x vs 1.5-2.5x) -- when both could apply to the same word,
# only the larger of the two is ever used (see core/reader.py's
# current_delay_ms(), "take the larger multiplier only"), so a long
# word's own length only adds a pause when punctuation isn't already
# providing a bigger one. In particular VERY_LONG_WORD_MULTIPLIER
# (1.7x) still stays comfortably below SENTENCE_PAUSE_MULTIPLIER
# (2.5x) above, so a sentence-ending pause always wins over even the
# longest word.
# Starting values, not tuned against real reading yet -- trivial to
# adjust, since nothing else depends on the exact numbers.
MEDIUM_WORD_MULTIPLIER = 1.2     # length band 2 (6-9 letters)
LONG_WORD_MULTIPLIER = 1.45      # length band 3 (10-13 letters)
VERY_LONG_WORD_MULTIPLIER = 1.7  # length band 4 (14+ letters)

# How many extra characters a word's INTERNAL hyphens count for when
# computing its length band for pacing (see effective_pacing_length()
# below) -- not for the ORP letter placement, which is unaffected. A
# hyphenated compound like "sub-terrain" reads more like two words
# stitched together than like a single word of the same raw character
# count, so it earns extra "effective length" per hyphen on top of its
# actual length, pushing it into a higher pacing band sooner than a
# plain word of the same length would reach. Applied per hyphen, so a
# word with two hyphens (e.g. "step-by-step") gets counted twice.
# Starting value, not tuned against real reading yet -- trivial to
# adjust, since nothing else depends on the exact number.
HYPHEN_PACING_BONUS_CHARS = 4


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


def effective_pacing_length(word: str) -> int:
    """The character length to use when banding a word for length-aware
    pacing -- its actual length, plus HYPHEN_PACING_BONUS_CHARS for each
    internal hyphen it contains. Deliberately separate from the word's
    real len(), which core/orp.py's get_orp_index() still uses unchanged
    for picking the ORP highlight letter -- this function only feeds
    core/orp.py's get_orp_index_for_length() for pacing purposes (see
    core/reader.py), so inflating it here never shifts which letter gets
    highlighted."""
    return len(word) + HYPHEN_PACING_BONUS_CHARS * word.count("-")


def apply_length_multiplier(base_delay_ms: int, length_band: int) -> int:
    """Scale a base per-word delay up for a long word. length_band is
    expected to be an ORP band index (core/orp.py's get_orp_index(),
    0-4); checked from the top down with >= / == rather than a fixed
    upper bound, so anything at or above band 4 still gets the top
    multiplier, and anything below band 2 -- 0, 1, or an unexpected
    negative value -- degrades safely to "no extra pause" rather than
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