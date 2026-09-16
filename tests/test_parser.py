from core.parser import clean_transcript


def test_strips_bracketed_timestamp():
    raw = "[00:00:01] Welcome to the show."
    assert clean_transcript(raw) == "Welcome to the show."


def test_strips_parenthesized_timestamp():
    raw = "(1:23) Today we're talking about speed reading."
    assert clean_transcript(raw) == "Today we're talking about speed reading."


def test_strips_bare_timestamp_no_brackets():
    raw = "00:02:45 rapid serial visual presentation."
    assert clean_transcript(raw) == "rapid serial visual presentation."


def test_strips_multiple_mixed_timestamps():
    raw = "[00:00:01] Welcome to the show. (1:23) Today we're talking about RSVP."
    expected = "Welcome to the show. Today we're talking about RSVP."
    assert clean_transcript(raw) == expected


def test_collapses_internal_whitespace():
    raw = "Hello   there\n\nfriend"
    assert clean_transcript(raw) == "Hello there friend"


def test_strips_leading_and_trailing_whitespace():
    raw = "   Hello there friend   "
    assert clean_transcript(raw) == "Hello there friend"


def test_passes_through_text_with_no_timestamps():
    raw = "Just a plain sentence with no timestamps at all."
    assert clean_transcript(raw) == raw


def test_empty_string_returns_empty_string():
    assert clean_transcript("") == ""