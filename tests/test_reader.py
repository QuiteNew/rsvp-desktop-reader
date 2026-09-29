import pytest
from core.reader import ReaderSession
from core.timing import WARM_UP_START_MULTIPLIER, WARM_UP_WORD_COUNT


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


# seek_to: absolute positioning (used by the progress scrubber)

def test_seek_to_moves_to_absolute_index():
    session = ReaderSession("one two three four five", start_index=1)
    session.seek_to(3)
    assert session.index == 3


def test_seek_to_zero_from_middle():
    session = ReaderSession("one two three four", start_index=2)
    session.seek_to(0)
    assert session.index == 0


def test_seek_to_clamps_past_the_end_to_finished():
    session = ReaderSession("one two three")
    session.seek_to(99)
    assert session.index == session.total_words
    assert session.is_finished is True


def test_seek_to_clamps_negative_to_zero():
    session = ReaderSession("one two three", start_index=2)
    session.seek_to(-5)
    assert session.index == 0


def test_seek_to_current_index_is_a_no_op():
    session = ReaderSession("one two three", start_index=1)
    session.seek_to(1)
    assert session.index == 1


def test_seek_to_from_finished_unfinishes_session():
    session = ReaderSession("one two three")
    session.seek_to(99)  # jump to the end so the session is finished
    assert session.is_finished is True
    session.seek_to(1)
    assert session.is_finished is False
    assert session.index == 1


def test_seek_to_does_not_restart_the_warm_up_ramp():
    # The scrubber must leave the warm-up ramp alone, like the skip
    # buttons: seeking changes the position, not how many words have been
    # shown this session, so the pace after a seek is whatever the ramp
    # had already reached. All words here are plain and unpunctuated with
    # length pacing off, so warm-up is the only thing shaping the delay.
    session = ReaderSession(
        " ".join(f"word{i}" for i in range(30)), wpm=300, warm_up_enabled=True
    )
    session.advance()
    session.advance()
    delay_before = session.current_delay_ms()
    session.seek_to(20)
    assert session.current_delay_ms() == delay_before


# remaining_ms: estimated time left, summed from the paced per-word delays

def test_remaining_ms_plain_words_is_count_times_base():
    # base at 300 wpm is 200ms; plain words carry no pacing pause, so
    # remaining is simply words-left * base.
    session = ReaderSession("one two three four", wpm=300)
    assert session.remaining_ms() == 4 * 200

def test_remaining_ms_shrinks_as_you_advance():
    session = ReaderSession("one two three four", wpm=300)
    session.advance()
    session.advance()
    assert session.remaining_ms() == 2 * 200

def test_remaining_ms_is_zero_when_finished():
    session = ReaderSession("one two", wpm=300)
    session.advance()
    session.advance()
    assert session.is_finished is True
    assert session.remaining_ms() == 0

def test_remaining_ms_includes_sentence_pause():
    # "Stop." ends a sentence (2.5x -> 500ms at base 200), "Go" is plain
    # (200ms), so from the start the estimate is 700.
    session = ReaderSession("Stop. Go", wpm=300)
    assert session.remaining_ms() == 500 + 200

def test_remaining_ms_counts_length_pause_only_when_enabled():
    # "responsibility" is length band 4. Off, it's a plain 200ms word, so
    # remaining is 200 + 200 = 400. On, it's 1.7x -> 340, so 340 + 200 = 540.
    off = ReaderSession("responsibility here", wpm=300)
    assert off.remaining_ms() == 400
    on = ReaderSession("responsibility here", wpm=300, length_pacing_enabled=True)
    assert on.remaining_ms() == 540

def test_remaining_ms_tracks_a_live_length_pacing_toggle():
    session = ReaderSession("responsibility here", wpm=300)
    assert session.remaining_ms() == 400
    session.set_length_pacing_enabled(True)
    assert session.remaining_ms() == 540

def test_remaining_ms_scales_with_wpm():
    session = ReaderSession("one two three four", wpm=300)
    assert session.remaining_ms() == 800
    session.set_wpm(600)  # base halves to 100ms
    assert session.remaining_ms() == 400

def test_remaining_ms_ignores_warm_up():
    # Warm-up would slow the first words during playback, but the estimate
    # deliberately excludes it, so it reads the same either way.
    plain = ReaderSession("one two three four", wpm=300)
    warmed = ReaderSession("one two three four", wpm=300, warm_up_enabled=True)
    assert warmed.remaining_ms() == plain.remaining_ms()

def test_remaining_ms_updates_after_seek():
    session = ReaderSession("one two three four five six", wpm=300)
    session.seek_to(4)
    assert session.remaining_ms() == 2 * 200

def test_remaining_ms_empty_transcript_is_zero():
    session = ReaderSession("", wpm=300)
    assert session.remaining_ms() == 0


# peripheral_context: the words around the current one for the context ribbon

def test_peripheral_context_middle_window():
    session = ReaderSession("one two three four five", start_index=2)
    ctx = session.peripheral_context(before=1, after=2)
    assert ctx.before == ["two"]
    assert ctx.current == "three"
    assert ctx.after == ["four", "five"]

def test_peripheral_context_at_start_has_no_before():
    session = ReaderSession("one two three four five")
    ctx = session.peripheral_context(before=1, after=2)
    assert ctx.before == []
    assert ctx.current == "one"
    assert ctx.after == ["two", "three"]

def test_peripheral_context_near_end_truncates_after():
    session = ReaderSession("one two three four five", start_index=4)
    ctx = session.peripheral_context(before=1, after=2)
    assert ctx.before == ["four"]
    assert ctx.current == "five"
    assert ctx.after == []

def test_peripheral_context_clamps_counts_to_whats_available():
    session = ReaderSession("one two three", start_index=1)
    ctx = session.peripheral_context(before=5, after=5)
    assert ctx.before == ["one"]
    assert ctx.current == "two"
    assert ctx.after == ["three"]

def test_peripheral_context_zero_counts_gives_only_current():
    session = ReaderSession("one two three", start_index=1)
    ctx = session.peripheral_context(before=0, after=0)
    assert ctx.before == []
    assert ctx.current == "two"
    assert ctx.after == []

def test_peripheral_context_negative_counts_treated_as_zero():
    session = ReaderSession("one two three", start_index=1)
    ctx = session.peripheral_context(before=-3, after=-1)
    assert ctx.before == []
    assert ctx.current == "two"
    assert ctx.after == []

def test_peripheral_context_finished_session_is_all_empty():
    session = ReaderSession("one two")
    session.advance()
    session.advance()
    assert session.is_finished is True
    ctx = session.peripheral_context(before=1, after=2)
    assert ctx.before == []
    assert ctx.current is None
    assert ctx.after == []

def test_peripheral_context_empty_transcript_is_all_empty():
    session = ReaderSession("")
    assert session.peripheral_context(before=1, after=2) == ([], None, [])

def test_peripheral_context_keeps_punctuation_attached_to_words():
    # Leading and trailing punctuation folds into a frame's word, so the
    # ribbon shows it just as the reader does.
    session = ReaderSession("Wait, go now.", start_index=1)
    ctx = session.peripheral_context(before=1, after=1)
    assert ctx.before == ["Wait,"]
    assert ctx.current == "go"
    assert ctx.after == ["now."]

def test_peripheral_context_current_matches_current_frame_word():
    session = ReaderSession("alpha beta gamma", start_index=1)
    frame = session.current_frame()
    ctx = session.peripheral_context(before=1, after=1)
    assert ctx.current == frame.before + frame.focus + frame.after

def test_peripheral_context_does_not_move_the_position():
    session = ReaderSession("one two three four", start_index=2)
    session.peripheral_context(before=2, after=2)
    assert session.index == 2

def test_peripheral_context_tracks_position_as_it_advances():
    session = ReaderSession("one two three four five")
    session.advance()  # now on "two"
    ctx = session.peripheral_context(before=1, after=1)
    assert (ctx.before, ctx.current, ctx.after) == (["one"], "two", ["three"])


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


# current_delay_ms: warm-up (ease-in) ramp
# Expected values follow WARM_UP_START_MULTIPLIER / WARM_UP_WORD_COUNT in
# core/timing.py, so the tests can't drift if those are later tuned. All use
# plain, unpunctuated words with length pacing off, so the only multiplier in
# play is the warm-up one, except where noted.

_START = WARM_UP_START_MULTIPLIER

def test_warm_up_disabled_by_default():
    session = ReaderSession("one two", wpm=300)
    assert session.current_delay_ms() == 200

def test_warm_up_first_word_is_slowest():
    session = ReaderSession("one two three", wpm=300, warm_up_enabled=True)
    assert session.current_delay_ms() == round(200 * _START)

def test_warm_up_ramps_down_to_base_over_the_word_count():
    text = " ".join(f"word{i}" for i in range(WARM_UP_WORD_COUNT + 5))
    session = ReaderSession(text, wpm=300, warm_up_enabled=True)
    delays = []
    while not session.is_finished:
        delays.append(session.current_delay_ms())
        session.advance()
    assert delays[0] == round(200 * _START)
    assert all(earlier >= later for earlier, later in zip(delays, delays[1:]))
    assert delays[WARM_UP_WORD_COUNT] == 200  # ramp is over by here
    assert delays[-1] == 200

def test_warm_up_composes_with_sentence_pause():
    # First word ends a sentence (2.5x -> 500ms), and warm-up scales that up
    # again at the very start of the session.
    session = ReaderSession("Stop. go on", wpm=300, warm_up_enabled=True)
    assert session.current_delay_ms() == round(500 * _START)

def test_warm_up_counts_words_shown_not_transcript_index():
    # Starting mid-transcript still eases in from the first shown word, since
    # the ramp counts words shown this session, not the transcript position.
    text = " ".join(f"word{i}" for i in range(30))
    session = ReaderSession(text, wpm=300, start_index=10, warm_up_enabled=True)
    assert session.current_delay_ms() == round(200 * _START)

def test_warm_up_live_toggle_via_set_warm_up_enabled():
    session = ReaderSession("one two three", wpm=300)
    assert session.current_delay_ms() == 200
    session.set_warm_up_enabled(True)
    assert session.current_delay_ms() == round(200 * _START)

def test_warm_up_reset_restarts_the_ramp():
    text = " ".join(f"word{i}" for i in range(30))
    session = ReaderSession(text, wpm=300, warm_up_enabled=True)
    for _ in range(WARM_UP_WORD_COUNT):
        session.advance()
    assert session.current_delay_ms() == 200  # past the ramp
    session.reset()
    assert session.current_delay_ms() == round(200 * _START)  # eased in again from the top

def test_warm_up_finished_session_returns_unmultiplied_base():
    session = ReaderSession("Hi.", wpm=300, warm_up_enabled=True)
    session.advance()
    assert session.is_finished is True
    assert session.current_delay_ms() == 200