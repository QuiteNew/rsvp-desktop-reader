from dataclasses import dataclass


@dataclass
class ORPWord:
    """A word split around its Optimal Recognition Point for RSVP display."""
    before: str
    focus: str
    after: str


def get_orp_index_for_length(length: int) -> int:
    """The standard RSVP length-banding heuristic, taking a character
    count directly rather than a word. Pulled out of get_orp_index()
    below so a caller that needs to band a length other than a word's
    literal len(), such as core/timing.py's effective_pacing_length(),
    which pads hyphenated compound words with extra length before
    banding them for pacing, can reuse these exact thresholds without
    duplicating them. Doing so has no effect on which letter
    get_orp_index() picks for the ORP highlight."""
    if length <= 1:
        return 0
    elif length <= 5:
        return 1
    elif length <= 9:
        return 2
    elif length <= 13:
        return 3
    else:
        return 4


def get_orp_index(word: str) -> int:
    """Return the index of a word's Optimal Recognition Point letter,
    based on word length (standard RSVP length-banding heuristic)."""
    return get_orp_index_for_length(len(word))


def split_at_orp(word: str) -> ORPWord:
    """Split a word into (before, focus letter, after) around its ORP."""
    if not word:
        raise ValueError("split_at_orp() requires a non-empty word")
    index = min(get_orp_index(word), len(word) - 1)
    return ORPWord(
        before=word[:index],
        focus=word[index],
        after=word[index + 1:],
    )