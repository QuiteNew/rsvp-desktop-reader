from core.parser import clean_transcript, clean_transcript_keep_lines, expand_ligatures


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


# clean_transcript_keep_lines: same cleanup, but line breaks survive

def test_keep_lines_keeps_single_line_breaks():
    assert clean_transcript_keep_lines("First line.\nSecond line.") == "First line.\nSecond line."


def test_keep_lines_strips_timestamps_on_each_line():
    raw = "[00:00:01] Welcome to the show.\n(1:23) Today we're talking."
    assert clean_transcript_keep_lines(raw) == "Welcome to the show.\nToday we're talking."


def test_keep_lines_collapses_spaces_and_tabs_within_a_line():
    assert clean_transcript_keep_lines("Hello   there\t\tfriend") == "Hello there friend"


def test_keep_lines_trims_each_line():
    assert clean_transcript_keep_lines("   First.   \n   Second.   ") == "First.\nSecond."


def test_keep_lines_cuts_runs_of_blank_lines_down_to_one():
    assert clean_transcript_keep_lines("First.\n\n\n\nSecond.") == "First.\n\nSecond."


def test_keep_lines_treats_whitespace_only_lines_as_blank():
    assert clean_transcript_keep_lines("First.\n   \n\t\nSecond.") == "First.\n\nSecond."


def test_keep_lines_line_left_empty_by_a_timestamp_disappears():
    assert clean_transcript_keep_lines("[00:00:01]\nHello.") == "Hello."


def test_keep_lines_converts_windows_line_endings():
    assert clean_transcript_keep_lines("First.\r\nSecond.") == "First.\nSecond."


def test_keep_lines_empty_string_returns_empty_string():
    assert clean_transcript_keep_lines("") == ""


def test_keep_lines_expands_combined_letters():
    assert clean_transcript_keep_lines("\ufb01nd the \ufb02ow") == "find the flow"


# expand_ligatures

def test_expand_ligatures_handles_every_combined_letter():
    assert expand_ligatures("\ufb00\ufb01\ufb02\ufb03\ufb04\ufb05\ufb06") == "fffiflffifflstst"


def test_expand_ligatures_inside_words():
    assert expand_ligatures("e\ufb03cient and o\ufb00er") == "efficient and offer"


def test_expand_ligatures_leaves_other_special_characters_alone():
    # Only the fixed list is touched, unlike a general Unicode cleanup.
    assert expand_ligatures("½ x² wait…") == "½ x² wait…"