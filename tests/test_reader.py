import pytest
from core.reader import ReaderSession


# Construction and the full pipeline

def test_composes_parser_tokenizer_and_orp_correctly():
    # An end to end check that the parser, tokenizer and ORP modules are
    # wired together correctly. The timestamp should be stripped, the text
    # split into words, and each word split at its ORP.
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
    # Should land safely on finished instead of crashing or going out of range.
    session = ReaderSession("one two three", start_index=99)
    assert session.index == session.total_words
    assert session.is_finished is True


def test_negative_start_index_clamps_to_zero():
    """A negative start_index shouldn't happen in normal use, but it could
    come from a hand edited or corrupted data file. Python allows negative
    list indexing, so without the max(0, ...) clamp current_frame() wouldn't
    crash. It would quietly return the wrong word, counted from the end of
    the list."""
    session = ReaderSession("one two three", start_index=-5)
    assert session.index == 0


# total_words

def test_total_words_matches_word_count():
    session = ReaderSession("one two three four")
    assert session.total_words == 4


def test_total_words_zero_for_empty_transcript():
    session = ReaderSession("")
    assert session.total_words == 0


# is_finished

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


# current_frame

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


# current_delay_ms

def test_current_delay_ms_matches_wpm():
    session = ReaderSession("hello", wpm=300)
    assert session.current_delay_ms() == 200  # 60000 / 300


def test_current_delay_ms_updates_live_after_set_wpm():
    session = ReaderSession("hello", wpm=300)
    assert session.current_delay_ms() == 200
    session.set_wpm(600)
    assert session.current_delay_ms() == 100  # uses the new speed right away, nothing is cached


# current_delay_ms: pauses after punctuation

def test_current_delay_ms_applies_clause_pause_after_comma():
    session = ReaderSession("wait, go", wpm=300)
    # The base delay is 200ms and "wait," ends in a clause mark, so 200 * 1.5
    assert session.current_delay_ms() == 300

def test_current_delay_ms_applies_sentence_pause_after_period():
    session = ReaderSession("Stop. Go", wpm=300)
    # The base delay is 200ms and "Stop." ends in a sentence mark, so 200 * 2.5
    assert session.current_delay_ms() == 500

def test_current_delay_ms_pace_tracks_position_as_session_advances():
    # self._paces is built once next to self.frames and indexed by
    # self.index the same way. This walks all three words to make sure the
    # pause follows the right word as playback moves on, not just at one
    # fixed index.
    session = ReaderSession("Wait, go now.", wpm=300)
    delays = []
    while not session.is_finished:
        delays.append(session.current_delay_ms())
        session.advance()
    assert delays == [300, 200, 500]  # clause, none, sentence

def test_current_delay_ms_for_finished_session_returns_unmultiplied_base():
    # A finished session returns the plain base delay. The last word ("Hi.")
    # ends a sentence, but once finished there's no word left to pause on.
    session = ReaderSession("Hi.", wpm=300)
    session.advance()
    assert session.is_finished is True
    assert session.current_delay_ms() == 200

def test_current_delay_ms_for_all_punctuation_token_still_paces_correctly():
    # "..." becomes its own word with no letters or digits in it. See
    # core/punctuation.py and the empty core branch in
    # ReaderSession.__init__. This makes sure that branch still gives the
    # token a sentence pause instead of quietly treating it as PACE_NONE.
    session = ReaderSession("Wait ... go", wpm=300, start_index=1)
    assert session.current_delay_ms() == 500


# current_delay_ms: slowing down for long words

def test_length_pacing_disabled_by_default():
    session = ReaderSession("responsibility here", wpm=300)
    assert session.current_delay_ms() == 200  # no slowdown, even for a 14 letter word

def test_length_pacing_enabled_slows_a_long_word():
    session = ReaderSession("responsibility here", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 340  # base 200 * 1.7 (length band 4)

def test_length_pacing_enabled_leaves_a_short_word_unaffected():
    session = ReaderSession("go now", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 200

def test_length_pacing_enabled_applies_medium_band():
    session = ReaderSession("reading now", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 240  # base 200 * 1.2 (length band 2, "reading" has 7 letters)

def test_length_pacing_takes_the_larger_multiplier_not_both():
    """When a word is long and also ends a sentence or clause, only the
    larger of the two pauses applies. They don't stack. "friendship," is
    length band 3 (1.45x, 290ms) and ends in a clause mark (1.5x, 300ms),
    so the clause pause wins because it's bigger."""
    session = ReaderSession("friendship, right", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 300

def test_length_pacing_sentence_pause_still_wins_over_a_very_long_word():
    # "responsibility." is length band 4 (1.7x, 340ms) and ends a sentence
    # (2.5x, 500ms), so the sentence pause wins.
    session = ReaderSession("responsibility. Right", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 500

def test_length_pacing_can_now_beat_a_clause_pause_for_a_very_long_word():
    # VERY_LONG_WORD_MULTIPLIER (1.7x) is bigger than
    # CLAUSE_PAUSE_MULTIPLIER (1.5x). "responsibility" is length band 4
    # (340ms), which beats its own trailing comma (300ms). This checks that
    # max() picks the length pause here and isn't stuck on punctuation.
    session = ReaderSession("responsibility, right", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 340

def test_hyphen_bonus_can_tip_length_pacing_past_a_clause_pause():
    # By its raw length of 10, "well-known," would be band 3 (1.45x,
    # 290ms), which is less than its comma's clause pause (1.5x, 300ms),
    # so punctuation would normally win. The hyphen bonus raises its
    # effective length to 14, which is band 4 (1.7x, 340ms), so the word's
    # length wins instead. This is the case hyphen aware pacing was added
    # for, where a hyphenated word gets more time than its raw length alone
    # would give it.
    session = ReaderSession("well-known, right", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 340

def test_length_pacing_live_toggle_via_set_length_pacing_enabled():
    session = ReaderSession("responsibility here", wpm=300)
    assert session.current_delay_ms() == 200
    session.set_length_pacing_enabled(True)
    assert session.current_delay_ms() == 340

def test_length_pacing_for_finished_session_returns_unmultiplied_base():
    session = ReaderSession("responsibility.", wpm=300, length_pacing_enabled=True)
    session.advance()
    assert session.is_finished is True
    assert session.current_delay_ms() == 200


# current_delay_ms: extra length for hyphenated words

def test_hyphenated_word_reaches_a_higher_band_than_its_raw_length_alone():
    # "sub-terrain" is 11 characters including the hyphen, which alone is
    # band 3 (1.45x, 290ms). The hyphen bonus adds 4 characters, for an
    # effective length of 15, which is band 4 (1.7x, 340ms).
    session = ReaderSession("sub-terrain here", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 340

def test_plain_word_of_the_same_raw_length_does_not_get_the_hyphen_bonus():
    # "comfortable" is also 11 characters but has no hyphen, so it stays in
    # band 3. That shows the bonus only applies to hyphenated words.
    session = ReaderSession("comfortable here", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 290

def test_multiple_hyphens_each_add_their_own_bonus():
    # "step-by-step" has two hyphens inside it and both count, giving an
    # effective length of 12 + 2*4 = 20. That's well past band 4's 14
    # letter start, so it gets the same top multiplier one hyphen would.
    session = ReaderSession("step-by-step here", wpm=300, length_pacing_enabled=True)
    assert session.current_delay_ms() == 340

def test_hyphen_bonus_does_not_apply_when_length_pacing_is_disabled():
    session = ReaderSession("sub-terrain here", wpm=300)
    assert session.current_delay_ms() == 200


# advance

def test_advance_moves_to_next_word():
    session = ReaderSession("one two three")
    session.advance()
    assert session.index == 1


def test_advance_does_nothing_once_finished():
    session = ReaderSession("one")
    session.advance()  # now finished
    session.advance()  # should do nothing
    session.advance()
    assert session.index == 1
    assert session.is_finished is True


# seek

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
    session.seek(100)  # jump to the end so the session is finished
    assert session.is_finished is True
    session.seek(-1)
    assert session.is_finished is False
    assert session.index == session.total_words - 1


def test_seek_zero_is_a_no_op():
    session = ReaderSession("one two three", start_index=1)
    session.seek(0)
    assert session.index == 1


# reset

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


# set_wpm

def test_set_wpm_updates_wpm_attribute():
    session = ReaderSession("hello", wpm=300)
    session.set_wpm(450)
    assert session.wpm == 450