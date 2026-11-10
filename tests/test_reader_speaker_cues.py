"""Tests for Speaker cues in the reading engine (core/reader.py's
ReaderSession): who speaks where, the pause before a new speaker, chunks that
never run into the next speaker, and turning cues on and off in place.

How labels are found is tested in test_speakers.py. With cues off, the
existing reader tests in test_reader.py and the others still cover reading
exactly as it was."""

import pytest

import core.reader as reader_module
from core.reader import ReaderSession
from core.speakers import UNNAMED_SPEAKER, SpeakerScan, SpeakerTurns
from core.timing import (
    CLAUSE_PAUSE_MULTIPLIER, SENTENCE_PAUSE_MULTIPLIER, SPEAKER_PAUSE_MULTIPLIER, wpm_to_delay_ms,
)

# 300 WPM: a plain word is 200 ms, a clause 300, a sentence end 500 and the
# speaker pause 700.
WPM = 300
BASE = wpm_to_delay_ms(WPM)
PLAIN = BASE
CLAUSE = round(BASE * CLAUSE_PAUSE_MULTIPLIER)
SENTENCE = round(BASE * SENTENCE_PAUSE_MULTIPLIER)
SPEAKER = round(BASE * SPEAKER_PAUSE_MULTIPLIER)

# Words: 0 Interviewer: 1 So 2 how 3 start? | 4 Speaker 5 2: 6 In 7 a
# 8 garage | 9 Interviewer: 10 Really. | 11 Speaker 12 2: 13 Yes
TEXT = "Interviewer: So how start?\nSpeaker 2: In a garage\nInterviewer: Really.\nSpeaker 2: Yes"


def _session(text=TEXT, **kwargs):
    kwargs.setdefault("wpm", WPM)
    return ReaderSession(text, **kwargs)


def _delays(session):
    """Every word's delay, read through the public API from the start (warm-up
    off, chunking off)."""
    session.reset()
    delays = []
    while not session.is_finished:
        delays.append(session.current_delay_ms())
        session.advance()
    return delays


def _speakers(session):
    session.reset()
    speakers = []
    while not session.is_finished:
        speakers.append(session.current_speaker)
        session.advance()
    return speakers


# ---- Off by default ----

def test_cues_are_off_by_default():
    session = _session()
    assert session.speaker_cues_enabled is False
    assert session.speaker_custom is None
    assert session.speaker_turns == SpeakerTurns()
    assert session.current_speaker is None

def test_with_cues_off_a_labelled_text_reads_as_it_always_did():
    assert _delays(_session()) == [
        CLAUSE, PLAIN, PLAIN, SENTENCE,
        PLAIN, CLAUSE, PLAIN, PLAIN, PLAIN,
        CLAUSE, SENTENCE,
        PLAIN, CLAUSE, PLAIN,
    ]

def test_with_cues_off_a_custom_list_changes_nothing():
    plain = _session()
    with_list = _session(speaker_custom={"interviewer": "Ann"})
    assert _delays(with_list) == _delays(plain)
    assert with_list.speaker_turns == SpeakerTurns()


# ---- Who speaks where ----

def test_the_turns_with_cues_on():
    session = _session(speaker_cues_enabled=True)
    assert session.speaker_turns == SpeakerTurns(
        (0, 4, 9, 11), ("Interviewer", "Speaker 2", "Interviewer", "Speaker 2"))

def test_the_current_speaker_follows_the_reading():
    session = _session(speaker_cues_enabled=True)
    assert _speakers(session) == ["Interviewer"] * 4 + ["Speaker 2"] * 5 + ["Interviewer"] * 2 + ["Speaker 2"] * 3

def test_the_current_speaker_follows_a_seek():
    session = _session(speaker_cues_enabled=True)
    session.seek_to(7)
    assert session.current_speaker == "Speaker 2"
    session.seek(-4)
    assert session.current_speaker == "Interviewer"

def test_there_is_no_current_speaker_once_finished():
    session = _session(speaker_cues_enabled=True)
    session.seek_to(session.total_words)
    assert session.is_finished
    assert session.current_speaker is None

def test_words_before_the_first_label_have_no_speaker():
    session = _session("Welcome back.\nAnn: hi\nBob: hey\nAnn: bye\nBob: ok", speaker_cues_enabled=True)
    assert _speakers(session)[:3] == [None, None, "Ann"]

def test_a_double_arrow_is_an_unnamed_speaker():
    session = _session("Ann: hi there\n>> who is that\nAnn: me", speaker_cues_enabled=True)
    assert session.speaker_turns.speakers == ("Ann", UNNAMED_SPEAKER, "Ann")

def test_a_label_seen_only_once_is_not_a_speaker_in_auto():
    session = _session("Ann: hi\nNote: once\nAnn: again", speaker_cues_enabled=True)
    assert session.speaker_turns == SpeakerTurns((0,), ("Ann",))

def test_a_text_without_labels_has_no_turns():
    session = _session("Just some plain words. Nothing more.", speaker_cues_enabled=True)
    assert session.speaker_turns == SpeakerTurns()
    assert _delays(session) == _delays(_session("Just some plain words. Nothing more."))


# ---- The transcript's own list (Custom) ----

def test_a_custom_list_names_and_picks_the_speakers():
    session = _session(speaker_cues_enabled=True, speaker_custom={"interviewer": "Ann", "speaker 2": "Bob"})
    assert session.speaker_turns.speakers == ("Ann", "Bob", "Ann", "Bob")

def test_a_label_left_out_of_a_custom_list_is_ignored():
    session = _session(speaker_cues_enabled=True, speaker_custom={"interviewer": "Ann"})
    assert session.speaker_turns == SpeakerTurns((0,), ("Ann",))

def test_a_custom_list_can_merge_two_labels():
    text = "Dr. Smith: a\nSmith: b\nAnn: c\nSmith: d"
    session = _session(text, speaker_cues_enabled=True,
                       speaker_custom={"dr. smith": "Smith", "smith": "Smith", "ann": "Ann"})
    assert session.speaker_turns == SpeakerTurns((0, 5, 7), ("Smith", "Ann", "Smith"))

def test_a_custom_list_can_switch_on_a_label_seen_only_once():
    session = _session("Ann: hi\nNote: once\nAnn: again", speaker_cues_enabled=True,
                       speaker_custom={"ann": "Ann", "note": "Note"})
    assert session.speaker_turns.speakers == ("Ann", "Note", "Ann")

def test_an_empty_custom_list_switches_every_speaker_off():
    session = _session(speaker_cues_enabled=True, speaker_custom={})
    assert session.speaker_turns == SpeakerTurns()

def test_a_damaged_custom_list_falls_back_to_auto():
    session = _session(speaker_cues_enabled=True, speaker_custom=["not", "a", "dict"])
    assert session.speaker_custom is None
    assert session.speaker_turns.speakers == ("Interviewer", "Speaker 2", "Interviewer", "Speaker 2")

def test_a_custom_list_is_cleaned_and_copied():
    custom = {"interviewer": "  Ann ", "Bad Key": "X"}
    session = _session(speaker_cues_enabled=True, speaker_custom=custom)
    custom["speaker 2"] = "Bob"
    assert session.speaker_custom == {"interviewer": "Ann"}


# ---- The pause before a new speaker ----

def test_the_last_word_of_each_turn_gets_the_speaker_pause():
    assert _delays(_session(speaker_cues_enabled=True)) == [
        CLAUSE, PLAIN, PLAIN, SPEAKER,        # "start?" ends a turn: longer than its sentence pause
        PLAIN, CLAUSE, PLAIN, PLAIN, SPEAKER,  # "garage" ends a turn with no punctuation at all
        CLAUSE, SPEAKER,                       # "Really." ends a turn
        PLAIN, CLAUSE, PLAIN,                  # the last word of the text has no next speaker
    ]

def test_the_pause_falls_before_the_first_speaker_too():
    session = _session("Welcome back\nAnn: hi\nBob: hey\nAnn: bye\nBob: ok", speaker_cues_enabled=True)
    assert _delays(session)[:3] == [PLAIN, SPEAKER, CLAUSE]

def test_a_text_that_starts_with_a_label_has_no_pause_before_it():
    assert _delays(_session(speaker_cues_enabled=True))[0] == CLAUSE

def test_the_same_speaker_twice_in_a_row_gets_no_pause():
    session = _session("Ann: one\nAnn: two\nBob: three\nBob: four", speaker_cues_enabled=True)
    assert _delays(session) == [CLAUSE, PLAIN, CLAUSE, SPEAKER, CLAUSE, PLAIN, CLAUSE, PLAIN]

def test_an_ignored_label_gets_no_pause():
    session = _session(speaker_cues_enabled=True, speaker_custom={"interviewer": "Ann"})
    assert _delays(session) == _delays(_session())

def test_the_speaker_pause_wins_over_length_pacing():
    text = "Ann: extraordinarily\nBob: hi\nAnn: no\nBob: ok"
    session = _session(text, speaker_cues_enabled=True, length_pacing_enabled=True)
    assert _delays(session)[1] == SPEAKER

def test_the_warm_up_ramp_slows_the_speaker_pause_too():
    plain = _session(speaker_cues_enabled=True)
    warm = _session(speaker_cues_enabled=True, warm_up_enabled=True)
    for _ in range(3):
        warm.advance()
        plain.advance()
    assert plain.current_delay_ms() == SPEAKER
    assert warm.current_delay_ms() > SPEAKER

def test_the_speaker_pause_is_seven_hundred_ms_at_three_hundred_wpm():
    # Pinned as plain numbers, so a change to the multiplier shows up here.
    assert SPEAKER_PAUSE_MULTIPLIER == 3.5
    assert _delays(_session(speaker_cues_enabled=True))[3] == 700

def test_a_turn_end_keeps_its_own_pause_when_that_is_longer(monkeypatch):
    # Today the speaker pause is longer than any other, so "the longer of the
    # two" only shows if it's made shorter than a sentence end.
    monkeypatch.setattr(reader_module, "SPEAKER_PAUSE_MULTIPLIER", 2.0)
    delays = _delays(_session(speaker_cues_enabled=True))
    assert delays[3] == SENTENCE          # "start?" keeps its longer sentence pause
    assert delays[8] == round(BASE * 2.0)  # "garage" had no pause, so it gets the speaker one

def test_delays_round_the_same_way_as_before_at_an_awkward_speed():
    # At 617 WPM the base delay is 97 ms, so the pauses land on halves and
    # rounding matters: 97 x 1.5 = 145.5, 97 x 2.5 = 242.5, 97 x 3.5 = 339.5.
    base = wpm_to_delay_ms(617)
    assert base == 97
    off = _delays(_session(wpm=617))
    on = _delays(_session(wpm=617, speaker_cues_enabled=True))
    assert off[:4] == [round(97 * 1.5), 97, 97, round(97 * 2.5)] == [146, 97, 97, 242]
    assert on[3] == round(97 * 3.5) == 340

def test_a_higher_speed_keeps_the_same_proportion():
    session = _session(speaker_cues_enabled=True, wpm=600)
    session.seek_to(3)
    assert session.current_delay_ms() == round(wpm_to_delay_ms(600) * SPEAKER_PAUSE_MULTIPLIER)


# ---- The time-left estimate ----

def _expected_remaining(multipliers):
    return round(BASE * sum(multipliers))

def test_the_time_left_counts_the_speaker_pauses():
    session = _session(speaker_cues_enabled=True)
    s, c, p = SPEAKER_PAUSE_MULTIPLIER, CLAUSE_PAUSE_MULTIPLIER, 1.0
    multipliers = [c, p, p, s, p, c, p, p, s, c, s, p, c, p]
    assert session.remaining_ms() == _expected_remaining(multipliers)
    session.seek_to(9)
    assert session.remaining_ms() == _expected_remaining(multipliers[9:])

def test_the_time_left_with_length_pacing_counts_them_too():
    text = "Ann: extraordinarily\nBob: hi\nAnn: no\nBob: ok"
    on = _session(text, speaker_cues_enabled=True, length_pacing_enabled=True)
    off = _session(text, length_pacing_enabled=True)
    # Three turn ends ("extraordinarily", "hi", "no"); the first one's long-word
    # pause gives way to the speaker pause, the other two were plain words.
    extra = (SPEAKER_PAUSE_MULTIPLIER - 1.7) + 2 * (SPEAKER_PAUSE_MULTIPLIER - 1.0)
    assert on.remaining_ms() == round(off.remaining_ms() + BASE * extra)

def test_the_time_left_matches_the_reading_itself():
    session = _session(speaker_cues_enabled=True)
    assert session.remaining_ms() == sum(_delays(session))


# ---- Chunks never run into the next speaker ----

@pytest.mark.parametrize("mode, size, target", [("fixed", 5, 30), ("adaptive", 2, 60)])
def test_a_chunk_stops_at_the_end_of_a_turn(mode, size, target):
    text = "Ann: one two\nBob: three four five six\nAnn: seven\nBob: eight"
    on = _session(text, speaker_cues_enabled=True, chunk_enabled=True,
                  chunk_size=size, chunk_mode=mode, chunk_char_target=target)
    starts = set(on.speaker_turns.starts)
    for start, end in on.chunk_ranges():
        assert not any(start < turn <= end - 1 for turn in starts), (start, end)
    off = _session(text, chunk_enabled=True, chunk_size=size, chunk_mode=mode, chunk_char_target=target)
    assert on.chunk_ranges() != off.chunk_ranges()

def test_a_chunk_ends_on_the_pause_and_keeps_the_wpm_exact():
    # Each speaker appears twice, or Auto wouldn't count them.
    text = "Ann: one two\nBob: three\nAnn: four\nBob: five"
    session = _session(text, speaker_cues_enabled=True, chunk_enabled=True, chunk_size=5)
    assert session.chunk_ranges() == [(0, 3), (3, 5), (5, 7), (7, 9)]
    assert session.current_chunk_delay_ms() == CLAUSE + PLAIN + SPEAKER

def test_set_chunking_keeps_the_turn_rule():
    text = "Ann: one two\nBob: three four\nAnn: five\nBob: six"
    session = _session(text, speaker_cues_enabled=True)
    session.set_chunking(True, 5)
    assert session.chunk_ranges() == [(0, 3), (3, 6), (6, 8), (8, 10)]


# ---- Turning cues on and off in place ----

def test_turning_cues_on_mid_reading_keeps_the_place():
    session = _session()
    session.seek_to(7)
    session.set_speaker_cues(True)
    assert session.index == 7
    assert session.current_speaker == "Speaker 2"
    assert _delays(session) == _delays(_session(speaker_cues_enabled=True))

def test_turning_cues_off_again_is_exactly_like_never_having_them():
    session = _session(speaker_cues_enabled=True, chunk_enabled=True, chunk_size=4)
    session.set_speaker_cues(False)
    fresh = _session(chunk_enabled=True, chunk_size=4)
    assert session.chunk_ranges() == fresh.chunk_ranges()
    assert session.remaining_ms() == fresh.remaining_ms()
    assert session.speaker_turns == SpeakerTurns()
    session.set_chunking(False, 4)
    fresh.set_chunking(False, 4)
    assert _delays(session) == _delays(fresh)

def test_a_new_list_takes_effect_in_place():
    session = _session(speaker_cues_enabled=True)
    session.set_speaker_cues(True, {"interviewer": "Ann", "speaker 2": "Bob"})
    assert session.speaker_custom == {"interviewer": "Ann", "speaker 2": "Bob"}
    assert session.speaker_turns.speakers == ("Ann", "Bob", "Ann", "Bob")
    session.set_speaker_cues(True, None)
    assert session.speaker_custom is None
    assert session.speaker_turns.speakers == ("Interviewer", "Speaker 2", "Interviewer", "Speaker 2")

def test_the_list_given_in_place_is_cleaned():
    session = _session(speaker_cues_enabled=True)
    session.set_speaker_cues(True, "damaged")
    assert session.speaker_custom is None

def test_turning_cues_on_snaps_to_the_start_of_the_new_chunk():
    text = "Ann: one two\nBob: three four\nAnn: five\nBob: six"
    session = _session(text, chunk_enabled=True, chunk_size=5)
    assert session.chunk_ranges()[0] == (0, 5)
    session.seek_to(4)
    assert session.index == 0
    session.index = 4  # a word in the middle of what will become two chunks
    session.set_speaker_cues(True)
    assert session.chunk_ranges()[:2] == [(0, 3), (3, 6)]
    assert session.index == 3

def test_changing_cues_does_not_restart_the_warm_up():
    session = _session(warm_up_enabled=True)
    for _ in range(5):
        session.advance()
    before = session._words_shown
    session.set_speaker_cues(True)
    assert session._words_shown == before

def test_a_finished_session_stays_finished():
    session = _session()
    session.seek_to(session.total_words)
    session.set_speaker_cues(True)
    assert session.is_finished
    assert session.index == session.total_words


# ---- The safety check on word counts ----

def test_no_turns_if_the_speaker_scan_ever_disagrees_with_the_reader(monkeypatch):
    real_scan = reader_module.scan_speakers

    def off_by_one(raw_text):
        scan = real_scan(raw_text)
        return SpeakerScan(scan.word_count + 1, scan.hits)

    monkeypatch.setattr(reader_module, "scan_speakers", off_by_one)
    session = _session(speaker_cues_enabled=True)
    assert session.speaker_turns == SpeakerTurns()
    assert _delays(session) == _delays(_session())


# ---- Text that changes how words count ----

def test_timestamps_and_blank_lines_do_not_move_the_turns():
    text = "[00:00:01] Ann: hello there\n\n00:00:04 Bob: hi\n0:07\nAnn: bye\nBob: ok"
    session = _session(text, speaker_cues_enabled=True)
    assert session.speaker_turns.starts == (0, 3, 5, 7)
    assert [session.frames[i].before + session.frames[i].focus + session.frames[i].after
            for i in session.speaker_turns.starts] == ["Ann:", "Bob:", "Ann:", "Bob:"]
