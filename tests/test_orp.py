import pytest
from core.orp import get_orp_index, split_at_orp, ORPWord


# ---- get_orp_index: exact boundary testing ----
# Synthetic "a" * n words guarantee each length is exactly what it claims
# to be — the boundaries themselves are the entire behavior of this
# function, so they're tested without any risk of a miscounted real word
# quietly producing a wrong expected value.

def test_orp_index_length_0_returns_0():
    assert get_orp_index("") == 0

def test_orp_index_length_1_returns_0():
    assert get_orp_index("a") == 0

def test_orp_index_length_2_returns_1():
    assert get_orp_index("aa") == 1

def test_orp_index_length_5_returns_1():
    assert get_orp_index("a" * 5) == 1

def test_orp_index_length_6_returns_2():
    # One letter past the first band boundary (5 -> 6)
    assert get_orp_index("a" * 6) == 2

def test_orp_index_length_9_returns_2():
    assert get_orp_index("a" * 9) == 2

def test_orp_index_length_10_returns_3():
    # One letter past the second band boundary (9 -> 10)
    assert get_orp_index("a" * 10) == 3

def test_orp_index_length_13_returns_3():
    assert get_orp_index("a" * 13) == 3

def test_orp_index_length_14_returns_4():
    # One letter past the third band boundary (13 -> 14)
    assert get_orp_index("a" * 14) == 4

def test_orp_index_very_long_word_still_returns_4():
    # Confirms the top band has no further ceiling — everything from
    # 14 letters upward lands on the same final index.
    assert get_orp_index("a" * 50) == 4


# ---- split_at_orp: before/focus/after on real words ----

def test_split_single_letter_word():
    assert split_at_orp("I") == ORPWord(before="", focus="I", after="")

def test_split_two_letter_word():
    assert split_at_orp("to") == ORPWord(before="t", focus="o", after="")

def test_split_five_letter_word():
    assert split_at_orp("about") == ORPWord(before="a", focus="b", after="out")

def test_split_word_with_trailing_punctuation():
    # tokenize() deliberately keeps punctuation attached to its word —
    # split_at_orp treats it as just another character, same as a letter.
    assert split_at_orp("show.") == ORPWord(before="s", focus="h", after="ow.")

def test_split_reconstructs_original_word_exactly():
    # A structural guarantee that must hold for every word, regardless of
    # length or which band it falls into: the three pieces, concatenated
    # back together, always recover the original word exactly — nothing
    # dropped, nothing duplicated.
    words = ["I", "to", "about", "friendship", "understanding", "a" * 30]
    for word in words:
        result = split_at_orp(word)
        assert result.before + result.focus + result.after == word


# ---- The empty-string case — a real fix, not just documentation ----

def test_split_at_orp_raises_clear_error_on_empty_string():
    """tokenize() never produces empty tokens, so this never triggers in
    the running app — but split_at_orp("") used to raise a confusing,
    generic IndexError (indexing an empty string at position -1). It now
    raises a clear, intentional ValueError instead — a real fix this test
    suite uncovered, not a pre-existing feature."""
    with pytest.raises(ValueError):
        split_at_orp("")