"""Tests for core/speakers.py: finding speaker labels, lining them up with
the reader's word numbers, and turning them into turns."""
import random
import time

import pytest

from core.parser import clean_transcript
from core.reader import ReaderSession
from core.speakers import (
    AUTO_MIN_APPEARANCES, MAX_LABEL_CHARS, UNNAMED_SPEAKER,
    LabelHit, SpeakerCandidate, SpeakerScan, SpeakerTurns,
    auto_speakers, build_turns, label_key, scan_speakers, speaker_candidates,
)
from core.tokenizer import tokenize


def _names(text):
    """The label names found in text, in order (None for a bare ">>")."""
    return [hit.name or None for hit in scan_speakers(text).hits]


def _reader_words(text):
    return tokenize(clean_transcript(text))


# --- What counts as a label ---------------------------------------------

@pytest.mark.parametrize("line, name", [
    ("Interviewer: So how did it start?", "Interviewer"),
    ("Speaker 2: In a garage.", "Speaker 2"),
    ("Q: Why?", "Q"),
    ("A: Because.", "A"),
    ("Dr. Smith: Good morning.", "Dr. Smith"),
    ("O'Brien: Hello.", "O'Brien"),
    ("O\u2019Brien: Hello.", "O\u2019Brien"),
    ("Mary-Jane: Hi.", "Mary-Jane"),
    ("Jean Luc Le Bon: Bonjour.", "Jean Luc Le Bon"),
    ("\u0418\u0432\u0430\u043d: \u041f\u0440\u0438\u0432\u0435\u0442.", "\u0418\u0432\u0430\u043d"),
    ("INTERVIEWER: Hello.", "INTERVIEWER"),
    ("\u5f20\u4e09: \u4f60\u597d", "\u5f20\u4e09"),  # a script with no capitals
    ("Speaker 2 : Hello.", "Speaker 2"),
    ("Speaker   2: Hello.", "Speaker 2"),
    ("   Bob: indented.", "Bob"),
    ("\tBob: after a tab.", "Bob"),
    ("Bob:", "Bob"),
    ("Bob:\tafter a tab.", "Bob"),
])
def test_a_label_at_the_start_of_a_line_is_found(line, name):
    assert _names(line) == [name]


@pytest.mark.parametrize("line", [
    "and Bob: hi",               # starts with a small letter
    "the answer is: yes",        # starts with a small letter
    "speaker 1: hi",             # an all-lowercase label isn't found
    "Note:hello",                # no space after the colon
    "http://example.com is up",  # a web address
    "10:30 is when we met",      # a time of day
    "2nd: second place",         # starts with a digit
    "_x: hi",                    # starts with an underscore
    "Wait, Bob: hi",             # a comma inside
    "Ready? Go: now",            # a question mark inside
    "Really! Bob: no",           # an exclamation mark inside
    "\"Bob\": quoted",           # quotes
    "(Bob): in brackets",        # brackets
    "[Bob] hello",               # the bracket form isn't supported
    "One two three four five: too many words",
    "Bob",                       # no colon at all
    ": nothing before it",
    "plain words with no label",
])
def test_these_are_not_labels(line):
    assert _names(line) == []


def test_a_label_of_exactly_the_longest_length_is_found_and_one_more_is_not():
    longest = "A" * MAX_LABEL_CHARS
    assert _names(f"{longest}: hi") == [longest]
    assert _names(f"{longest}B: hi") == []


def test_four_words_are_allowed_and_five_are_not():
    assert _names("One two three four: hi") == ["One two three four"]
    assert _names("One two three four five: hi") == []


def test_the_length_is_measured_after_spaces_are_squeezed():
    # 29 letters plus one space is 30 characters once the run of spaces
    # becomes one, so it fits.
    name = "A" * 14 + "        " + "B" * 15
    assert _names(f"{name}: hi") == ["A" * 14 + " " + "B" * 15]


def test_only_the_first_colon_ends_the_label():
    assert _names("Bob: time is 10:30: late") == ["Bob"]


# --- ">>" changes ----------------------------------------------------------

def test_a_double_arrow_is_a_change_with_no_name():
    hits = scan_speakers(">> And then what happened?").hits
    assert hits == (LabelHit(0, None, "", True),)


def test_a_double_arrow_alone_on_a_line_is_a_change():
    hits = scan_speakers("first line\n>>\nsecond line").hits
    assert hits == (LabelHit(2, None, "", True),)


def test_a_label_after_a_double_arrow_is_used_and_remembers_the_arrow():
    assert scan_speakers(">> JOHN: hi").hits == (LabelHit(0, "john", "JOHN", True),)
    assert scan_speakers(">>JOHN: hi").hits == (LabelHit(0, "john", "JOHN", True),)


def test_three_arrows_are_not_a_change():
    assert scan_speakers(">>> quoted reply").hits == ()


def test_a_double_arrow_later_in_the_line_is_not_a_change():
    assert scan_speakers("a >> b").hits == ()


# --- Lining up with the reader's words -------------------------------------

def test_each_hit_is_at_the_word_number_of_its_line():
    text = "Intro words here.\nInterviewer: So?\n\nSpeaker 2: Yes, it did.\n"
    scan = scan_speakers(text)
    words = _reader_words(text)
    assert scan.word_count == len(words) == 10
    assert [h.word_index for h in scan.hits] == [3, 5]
    assert words[3] == "Interviewer:"
    assert words[5] == "Speaker"


def test_timestamps_are_removed_first_like_the_reader_does():
    text = "[00:01:02] Bob: hi there\n00:01:05 Ann: hello\n0:07\nBob: again"
    scan = scan_speakers(text)
    words = _reader_words(text)
    assert scan.word_count == len(words)
    assert [(h.word_index, h.key) for h in scan.hits] == [(0, "bob"), (3, "ann"), (5, "bob")]
    assert [words[h.word_index] for h in scan.hits] == ["Bob:", "Ann:", "Bob:"]


def test_a_subtitle_timing_line_does_not_count_as_words():
    text = "1\n00:00:01,000 --> 00:00:04,000\nBob: hi\n"
    scan = scan_speakers(text)
    assert scan.word_count == len(_reader_words(text)) == 3
    assert scan.hits[0].word_index == 1


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_every_kind_of_line_ending_starts_a_new_line(newline):
    text = newline.join(["Bob: one", "Ann: two", "Bob: three"])
    assert [h.word_index for h in scan_speakers(text).hits] == [0, 2, 4]


def test_other_unicode_line_separators_do_not_start_a_line_but_still_split_words():
    # The reader splits words on these too, so the count must match, but
    # they're too unusual to treat as the start of a line.
    for separator in ["\u2028", "\u2029", "\x85", "\x0b", "\x0c", "\x1c"]:
        text = f"one{separator}Bob: two"
        scan = scan_speakers(text)
        assert scan.word_count == len(_reader_words(text)) == 3
        assert scan.hits == ()


def test_blank_and_whitespace_only_lines_are_skipped():
    text = "\n\n   \nBob: hi\n\t\n\u00a0\nAnn: hey"
    scan = scan_speakers(text)
    assert scan.word_count == 4
    assert [h.word_index for h in scan.hits] == [0, 2]


@pytest.mark.parametrize("text", ["", "   ", "\n\n", "\r\n\t "])
def test_empty_text_has_no_words_and_no_hits(text):
    assert scan_speakers(text) == SpeakerScan(0, ())


# Pieces the random texts are built from: labels, changes, timestamps,
# odd spaces and line endings, punctuation, other scripts and emoji.
_PIECES = [
    "Bob:", "Ann:", "Speaker 2:", "Q:", "Dr. Smith:", "INTERVIEWER:", "Note:",
    ">>", ">> JOHN:", ">>>", "word", "two words", "end.", "hi,", "10:30", "--",
    "http://x.y", "[00:01:02]", "(1:23)", "00:02:45", "0:05",
    "00:00:01,000 --> 00:00:04,000", "na\u00efve", "\u0418\u0432\u0430\u043d:",
    "\U0001F600", "\u00a0", "\u2028", "\x85", "\x0b", "\t", " ", "  ",
    "\n", "\n", "\n", "\r\n", "\r", "\n\n",
]


def _random_text(rng):
    return "".join(rng.choice(_PIECES) + rng.choice(["", " ", "\n"]) for _ in range(rng.randint(0, 40)))


def test_word_numbers_always_match_the_reader_on_random_text():
    rng = random.Random(20261110)
    for _ in range(3000):
        text = _random_text(rng)
        scan = scan_speakers(text)
        words = _reader_words(text)
        assert scan.word_count == len(words), repr(text)
        last = -1
        for hit in scan.hits:
            assert last < hit.word_index < len(words), repr(text)
            last = hit.word_index
            first_word = words[hit.word_index]
            if hit.marked:
                assert first_word.startswith(">>"), repr(text)
            else:
                assert first_word.startswith(hit.name.split()[0]), repr(text)


def test_the_word_count_matches_a_real_reader_session():
    text = "Interviewer: So, how did it start?\n[00:00:05] Speaker 2: In a garage.\n>> And then?"
    assert scan_speakers(text).word_count == ReaderSession(text).total_words


# --- Candidates and Auto ---------------------------------------------------

def test_candidates_are_listed_in_order_of_first_appearance_with_counts():
    text = "Ann: a\nBob: b\nAnn : c\nCarl: d\nBob: e\nANN: f\n>> g"
    assert speaker_candidates(scan_speakers(text)) == [
        SpeakerCandidate("ann", "Ann", 3),
        SpeakerCandidate("bob", "Bob", 2),
        SpeakerCandidate("carl", "Carl", 1),
    ]


def test_auto_switches_on_labels_that_appear_often_enough():
    candidates = [
        SpeakerCandidate("ann", "Ann", 3),
        SpeakerCandidate("bob", "Bob", AUTO_MIN_APPEARANCES),
        SpeakerCandidate("note", "Note", AUTO_MIN_APPEARANCES - 1),
    ]
    assert auto_speakers(candidates) == {"ann": "ann", "bob": "bob"}


def test_label_keys_ignore_case_and_extra_spaces():
    assert label_key("  Speaker   TWO ") == "speaker two"
    assert label_key("STRASSE") == label_key("stra\u00dfe")


# --- Turns -----------------------------------------------------------------

def _hits(*items):
    """Build a scan from (word_index, key, marked) tuples."""
    hits = tuple(LabelHit(i, key, key or "", marked) for i, key, marked in items)
    return SpeakerScan(100, hits)


def test_each_switched_on_label_starts_a_turn():
    scan = _hits((0, "ann", False), (5, "bob", False), (9, "ann", False))
    turns = build_turns(scan, {"ann": "ann", "bob": "bob"})
    assert turns == SpeakerTurns((0, 5, 9), ("ann", "bob", "ann"))


def test_a_label_that_is_not_switched_on_is_ignored():
    scan = _hits((0, "ann", False), (5, "note", False), (9, "bob", False))
    turns = build_turns(scan, {"ann": "ann", "bob": "bob"})
    assert turns == SpeakerTurns((0, 9), ("ann", "bob"))


def test_a_label_not_switched_on_after_an_arrow_is_still_an_unnamed_change():
    scan = _hits((0, "ann", False), (5, "john", True))
    turns = build_turns(scan, {"ann": "ann"})
    assert turns == SpeakerTurns((0, 5), ("ann", UNNAMED_SPEAKER))


def test_a_bare_arrow_is_always_a_change():
    scan = _hits((3, None, True))
    assert build_turns(scan, {}) == SpeakerTurns((3,), (UNNAMED_SPEAKER,))


def test_the_same_speaker_twice_in_a_row_is_one_turn():
    scan = _hits((0, "ann", False), (5, "ann", False), (9, "bob", False))
    assert build_turns(scan, {"ann": "ann", "bob": "bob"}) == SpeakerTurns((0, 9), ("ann", "bob"))


def test_merged_labels_in_a_row_are_one_turn():
    scan = _hits((0, "dr. smith", False), (5, "smith", False), (9, "ann", False))
    speaker_of = {"dr. smith": "smith", "smith": "smith", "ann": "ann"}
    assert build_turns(scan, speaker_of) == SpeakerTurns((0, 9), ("smith", "ann"))


def test_two_arrows_in_a_row_stay_two_changes():
    scan = _hits((0, None, True), (5, None, True))
    turns = build_turns(scan, {})
    assert turns == SpeakerTurns((0, 5), (UNNAMED_SPEAKER, UNNAMED_SPEAKER))


def test_an_ignored_label_between_two_of_the_same_speaker_keeps_one_turn():
    scan = _hits((0, "ann", False), (5, "note", False), (9, "ann", False))
    assert build_turns(scan, {"ann": "ann"}) == SpeakerTurns((0,), ("ann",))


def test_nothing_switched_on_means_no_turns():
    scan = _hits((0, "ann", False), (5, "bob", False))
    assert build_turns(scan, {}) == SpeakerTurns()


def test_from_text_to_turns_with_auto():
    text = "Welcome.\nAnn: hi\nBob: hey\nNote: once only\nAnn: bye\nBob: see you"
    scan = scan_speakers(text)
    turns = build_turns(scan, auto_speakers(speaker_candidates(scan)))
    assert turns == SpeakerTurns((1, 3, 8, 10), ("ann", "bob", "ann", "bob"))


# --- Looking up a speaker --------------------------------------------------

def test_who_is_speaking_at_each_word():
    turns = SpeakerTurns((2, 5, 9), ("ann", "bob", "ann"))
    assert [turns.speaker_at(i) for i in range(11)] == [
        None, None, "ann", "ann", "ann", "bob", "bob", "bob", "bob", "ann", "ann",
    ]


def test_where_turns_start():
    turns = SpeakerTurns((2, 5, 9), ("ann", "bob", "ann"))
    assert [i for i in range(11) if turns.is_turn_start(i)] == [2, 5, 9]


def test_no_turns_means_no_one_speaks_and_no_turn_starts():
    turns = SpeakerTurns()
    assert turns.speaker_at(0) is None
    assert turns.speaker_at(50) is None
    assert not turns.is_turn_start(0)


def test_a_turn_at_the_first_word():
    turns = SpeakerTurns((0,), ("ann",))
    assert turns.speaker_at(0) == "ann"
    assert turns.is_turn_start(0)
    assert not turns.is_turn_start(1)


# --- Speed -----------------------------------------------------------------

def test_a_long_transcript_is_quick():
    # About 200,000 words in 10,000 labelled lines.
    line = "Speaker {}: " + " ".join(["word"] * 19)
    text = "\n".join(line.format(i % 3) for i in range(10_000))
    started = time.perf_counter()
    scan = scan_speakers(text)
    turns = build_turns(scan, auto_speakers(speaker_candidates(scan)))
    elapsed = time.perf_counter() - started
    assert scan.word_count == 210_000
    assert len(turns.starts) == 10_000
    assert elapsed < 2.0