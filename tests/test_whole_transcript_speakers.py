"""Tests for transcript_speakers() in core/speakers.py: the speaker list a whole
transcript is read with, which a selection played on its own is read with too.

TEXT has four turns. Ann and Bob each start two lines, so Auto switches both
on, and Cat starts one, so Auto leaves her off. SELECTION is a piece of it that
starts in the middle of Ann's first turn and holds each name only once."""

from core.reader import ReaderSession
from core.speakers import AUTO_MIN_APPEARANCES, transcript_speakers

TEXT = "Ann: hi there\nBob: hello you\nCat: just once\nAnn: and so\nBob: we go"
SELECTION = "there\nBob: hello you\nAnn: and"


def test_with_no_custom_list_it_is_what_auto_finds_in_the_whole_text():
    assert transcript_speakers(TEXT) == {"ann": "Ann", "bob": "Bob"}
    assert transcript_speakers(TEXT, None) == {"ann": "Ann", "bob": "Bob"}


def test_auto_still_needs_a_name_to_appear_twice():
    # Pinned, so a change to the rule shows up here as well as in
    # test_speakers.py.
    assert AUTO_MIN_APPEARANCES == 2
    assert "cat" not in transcript_speakers(TEXT)


def test_a_custom_list_is_used_as_it_is():
    custom = {"cat": "Cat", "ann": "Annie"}
    assert transcript_speakers(TEXT, custom) == {"cat": "Cat", "ann": "Annie"}


def test_an_empty_custom_list_means_nobody_and_not_auto():
    assert transcript_speakers(TEXT, {}) == {}


def test_the_answer_is_always_a_new_dict():
    custom = {"ann": "Ann"}
    answer = transcript_speakers(TEXT, custom)
    answer["bob"] = "Bob"
    assert custom == {"ann": "Ann"}


def test_text_with_no_labels_has_no_speakers():
    assert transcript_speakers("just some words\nand some more") == {}
    assert transcript_speakers("") == {}


# --- What it's for: a selection read on its own ------------------------------

def _turns(text, custom):
    session = ReaderSession(text, wpm=300, speaker_cues_enabled=True, speaker_custom=custom)
    return session.speaker_turns


def test_on_its_own_a_selection_with_each_name_once_has_no_speakers():
    # This is why the whole transcript's list is needed at all.
    turns = _turns(SELECTION, None)
    assert turns.starts == ()


def test_with_the_whole_transcripts_list_the_selection_has_its_turns():
    # SELECTION's words: there(0) Bob:(1) hello(2) you(3) Ann:(4) and(5).
    turns = _turns(SELECTION, transcript_speakers(TEXT))
    assert turns.starts == (1, 4)
    assert turns.speakers == ("Bob", "Ann")


def test_words_before_the_first_label_in_the_selection_have_no_speaker():
    turns = _turns(SELECTION, transcript_speakers(TEXT))
    assert turns.speaker_at(0) is None
    assert turns.speaker_at(1) == "Bob"
    assert turns.speaker_at(5) == "Ann"


def test_a_custom_list_reaches_the_selection_too():
    turns = _turns(SELECTION, transcript_speakers(TEXT, {"ann": "Annie"}))
    assert turns.starts == (4,)
    assert turns.speakers == ("Annie",)
