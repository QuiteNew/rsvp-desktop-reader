import pytest
from core.reader import ReaderSession


# ---- Construction and the full pipeline ----

def test_composes_parser_tokenizer_and_orp_correctly():
    # An end-to-end check that all three earlier modules are correctly
    # wired together — this is exactly what scratch_check.py used to
    # verify by hand. A timestamp should be stripped, the text tokenized
    # into words, and each word ORP-split.
    raw = "[00:00:01] Welcome to the show."
    session = ReaderSession(raw)
    assert session.total_words == 4
    first = session.current_frame()
    assert first.before + first.focus + first.after == "Welcome"


def test_default_wpm_is_300():
    session = ReaderSession("Hello there")
    assert session.wpm == 300


def test_starts_at_index_0_by_default():
    session = ReaderSession("Hello there")
    assert session.index == 0
    assert session.is_finished is False


def test_start_index_is_respected():
    session = ReaderSession("one two three four five", start_index=2)
    frame = session.current_frame()
    assert session.index == 2
    assert frame.before + frame.focus + frame.after == "three"


def test_start_index_beyond_word_count_clamps_to_finished():
    # Should land safely at "finished", not crash or go out of range.
    session = ReaderSession("one two three", start_index=99)
    assert session.index == session.total_words
    assert session.is_finished is True


def test_negative_start_index_clamps_to_zero():
    """A real gap this test suite found: start_index only had an upper
    clamp (min(start_index, total_words)), never a lower one. A negative
    start_index — which shouldn't occur through normal app use, but
    could from a hand-edited or corrupted data file — left self.index
    negative. Since Python allows negative list indexing, current_frame()
    wouldn't have crashed; it would have silently returned the wrong
    word, counted from the end of the list, with no error at all. Now
    fixed with max(0, ...) alongside the existing upper clamp."""
    session = ReaderSession("one two three", start_index=-5)
    assert session.index == 0


# ---- total_words ----

def test_total_words_matches_word_count():
    session = ReaderSession("one two three four")
    assert session.total_words == 4


def test_total_words_zero_for_empty_transcript():
    session = ReaderSession("")
    assert session.total_words == 0


# ---- is_finished ----

def test_is_finished_false_at_start():
    session = ReaderSession("one two three")
    assert session.is_finished is False


def test_is_finished_true_after_advancing_past_last_word():
    session = ReaderSession("one two")
    session.advance()
    session.advance()
    assert session.is_finished is True


def test_empty_transcript_is_immediately_finished():
    session = ReaderSession("")
    assert session.is_finished is True


# ---- current_frame ----

def test_current_frame_returns_none_when_finished():
    session = ReaderSession("one")
    session.advance()
    assert session.current_frame() is None


def test_current_frame_none_for_empty_transcript():
    session = ReaderSession("")
    assert session.current_frame() is None


def test_current_frame_advances_through_every_word_in_order():
    session = ReaderSession("one two three")
    seen = []
    while not session.is_finished:
        frame = session.current_frame()
        seen.append(frame.before + frame.focus + frame.after)
        session.advance()
    assert seen == ["one", "two", "three"]


# ---- current_delay_ms ----

def test_current_delay_ms_matches_wpm():
    session = ReaderSession("hello", wpm=300)
    assert session.current_delay_ms() == 200  # 60000 / 300


def test_current_delay_ms_updates_live_after_set_wpm():
    session = ReaderSession("hello", wpm=300)
    assert session.current_delay_ms() == 200
    session.set_wpm(600)
    assert session.current_delay_ms() == 100  # reflects the new speed immediately, not cached


# ---- current_delay_ms: punctuation-aware pacing ----

def test_current_delay_ms_applies_clause_pause_after_comma():
    session = ReaderSession("wait, go", wpm=300)
    # base delay is 200ms; "wait," ends in a clause mark -> 200 * 1.5
    assert session.current_delay_ms() == 300

def test_current_delay_ms_applies_sentence_pause_after_period():
    session = ReaderSession("Stop. Go", wpm=300)
    # base delay is 200ms; "Stop." ends in a sentence mark -> 200 * 2.5
    assert session.current_delay_ms() == 500

def test_current_delay_ms_pace_tracks_position_as_session_advances():
    # self._paces is built once, alongside self.frames, and indexed by
    # self.index the same way -- this walks all three words to confirm
    # the pause actually follows the right word as playback advances,
    # not just at a single fixed index.
    session = ReaderSession("Wait, go now.", wpm=300)
    delays = []
    while not session.is_finished:
        delays.append(session.current_delay_ms())
        session.advance()
    assert delays == [300, 200, 500]  # clause, none, sentence

def test_current_delay_ms_for_finished_session_returns_unmultiplied_base():
    # is_finished short-circuits to the flat base delay -- even though
    # the last word read ("Hi.") ends a sentence, a finished session
    # isn't pausing on any word anymore.
    session = ReaderSession("Hi.", wpm=300)
    session.advance()
    assert session.is_finished is True
    assert session.current_delay_ms() == 200

def test_current_delay_ms_for_all_punctuation_token_still_paces_correctly():
    # "..." tokenizes as its own word with no alnum core (see
    # core/punctuation.py and the "core is empty" branch in
    # ReaderSession.__init__) -- this confirms that branch still
    # classifies and paces the token correctly rather than silently
    # treating it as PACE_NONE.
    session = ReaderSession("Wait ... go", wpm=300, start_index=1)
    assert session.current_delay_ms() == 500


# ---- advance ----

def test_advance_moves_to_next_word():
    session = ReaderSession("one two three")
    session.advance()
    assert session.index == 1


def test_advance_does_nothing_once_finished():
    session = ReaderSession("one")
    session.advance()  # now finished
    session.advance()  # should be a safe no-op
    session.advance()
    assert session.index == 1
    assert session.is_finished is True


# ---- seek ----

def test_seek_forward_moves_correct_number_of_words():
    session = ReaderSession("one two three four five six")
    session.seek(3)
    assert session.index == 3


def test_seek_backward_moves_correct_number_of_words():
    session = ReaderSession("one two three four five six", start_index=4)
    session.seek(-2)
    assert session.index == 2


def test_seek_forward_clamps_at_total_words():
    session = ReaderSession("one two three")
    session.seek(100)
    assert session.index == session.total_words
    assert session.is_finished is True


def test_seek_backward_clamps_at_zero():
    session = ReaderSession("one two three", start_index=1)
    session.seek(-100)
    assert session.index == 0


def test_seek_backward_from_finished_state_unfinishes_session():
    session = ReaderSession("one two three")
    session.seek(100)  # push to finished
    assert session.is_finished is True
    session.seek(-1)
    assert session.is_finished is False
    assert session.index == session.total_words - 1


def test_seek_zero_is_a_no_op():
    session = ReaderSession("one two three", start_index=1)
    session.seek(0)
    assert session.index == 1


# ---- reset ----

def test_reset_returns_to_index_zero():
    session = ReaderSession("one two three", start_index=2)
    session.reset()
    assert session.index == 0


def test_reset_unfinishes_a_finished_session():
    session = ReaderSession("one two")
    session.advance()
    session.advance()
    assert session.is_finished is True
    session.reset()
    assert session.is_finished is False


# ---- set_wpm ----

def test_set_wpm_updates_wpm_attribute():
    session = ReaderSession("hello", wpm=300)
    session.set_wpm(450)
    assert session.wpm == 450