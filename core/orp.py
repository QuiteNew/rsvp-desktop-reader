from dataclasses import dataclass


@dataclass
class ORPWord:
    """A word split around its Optimal Recognition Point for RSVP display."""
    before: str
    focus: str
    after: str


def get_orp_index(word: str) -> int:
    """Return the index of a word's Optimal Recognition Point letter,
    based on word length (standard RSVP length-banding heuristic)."""
    length = len(word)
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


def split_at_orp(word: str) -> ORPWord:
    """Split a word into (before, focus letter, after) around its ORP."""
    index = min(get_orp_index(word), len(word) - 1)
    return ORPWord(
        before=word[:index],
        focus=word[index],
        after=word[index + 1:],
    )


if __name__ == "__main__":
    test_words = ["I", "the", "reading", "wonderful", "extraordinary"]
    for w in test_words:
        r = split_at_orp(w)
        print(f"{w:>15} -> before='{r.before}' focus='{r.focus}' after='{r.after}'")