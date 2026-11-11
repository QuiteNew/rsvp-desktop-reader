"""Tests for core/chime.py: the chime's sound file in each style, the pattern
of notes each speaker gets, which notes a change plays, and the wait between
chimes.

What a chime sounds like can only be judged by ear. These tests check what
can be measured: that it's a proper WAV file of the right length, as loud as
asked and never louder, silent at both ends so it doesn't click, with its
notes at the right pitches and times, and fading away."""

import io
import math
import time
import wave
from array import array

import pytest

from core.chime import (
    CHANGE_PATTERN, CHIME_STYLES, CHIME_VOLUME, MIN_CHIME_GAP_MS, NOTE_STEP_MS, SAMPLE_RATE, SPEAKER_PATTERNS,
    ChimeGap, chime_length_ms, chime_notes, chime_wav, speaker_patterns,
)
from core.settings_store import SPEAKER_CUE_SOUNDS
from core.speakers import UNNAMED_SPEAKER

C5, E5, G5, C6, A4 = 523.25, 659.25, 783.99, 1046.5, 440.0


def _read(data):
    """(channels, sample width, rate, samples) of a WAV file's bytes."""
    with wave.open(io.BytesIO(data), "rb") as wav:
        params = (wav.getnchannels(), wav.getsampwidth(), wav.getframerate())
        frames = wav.readframes(wav.getnframes())
    samples = array("h")
    samples.frombytes(frames)
    if array("h", [1]).tobytes() != b"\x01\x00":
        samples.byteswap()
    return (*params, samples)


def _samples(*args, **kwargs):
    return _read(chime_wav(*args, **kwargs))[3]


def _strength_at(samples, frequency_hz):
    """How strongly a pitch is present in the samples (one bin of a Fourier
    transform, worked out directly)."""
    real = imaginary = 0.0
    step = 2 * math.pi * frequency_hz / SAMPLE_RATE
    for n, value in enumerate(samples):
        real += value * math.cos(step * n)
        imaginary += value * math.sin(step * n)
    return math.hypot(real, imaginary)


def _rms(samples):
    return math.sqrt(sum(v * v for v in samples) / len(samples)) if samples else 0.0


def _ms(milliseconds):
    return round(SAMPLE_RATE * milliseconds / 1000)


# ---- The values the chimes are made with ----

def test_the_tuning_values():
    # Pinned as plain numbers, so a change to any of them shows up here.
    assert SAMPLE_RATE == 44100
    assert CHIME_VOLUME == 0.25
    assert NOTE_STEP_MS == 120
    assert MIN_CHIME_GAP_MS == 400
    assert CHIME_STYLES == ("bell", "soft", "glass", "wood")

def test_the_speaker_patterns():
    assert SPEAKER_PATTERNS == (
        (523.25,),                  # one note
        (523.25, 783.99),           # two going up
        (783.99, 523.25),           # two going down
        (1046.5,),                  # one higher note
        (523.25, 659.25, 783.99),   # three going up
    )
    assert CHANGE_PATTERN == (440.0,)

def test_every_speaker_pattern_is_different_and_none_is_the_change_chime():
    assert len(set(SPEAKER_PATTERNS)) == 5
    assert CHANGE_PATTERN not in SPEAKER_PATTERNS

def test_the_change_chime_is_lower_than_every_speaker_note():
    assert all(CHANGE_PATTERN[0] < note for pattern in SPEAKER_PATTERNS for note in pattern)

@pytest.mark.parametrize("style, note_ms", [("bell", 450), ("soft", 500), ("glass", 700), ("wood", 300)])
def test_how_long_a_chime_lasts(style, note_ms):
    assert chime_length_ms((C5,), style) == note_ms
    assert chime_length_ms((C5, G5), style) == note_ms + 120
    assert chime_length_ms((C5, E5, G5), style) == note_ms + 240

def test_the_default_style_is_bell():
    assert chime_length_ms((C5,)) == 450
    assert chime_wav((C5,)) == chime_wav((C5,), "bell")


# ---- The sound file ----

@pytest.mark.parametrize("style", CHIME_STYLES)
@pytest.mark.parametrize("notes", [(C5,), (C5, G5), (C5, E5, G5)])
def test_it_is_a_mono_sixteen_bit_wav_of_the_right_length(style, notes):
    channels, width, rate, samples = _read(chime_wav(notes, style))
    assert (channels, width, rate) == (1, 2, 44100)
    assert len(samples) == _ms(chime_length_ms(notes, style))

@pytest.mark.parametrize("volume", [0.25, 0.5, 0.1, 1.0, 0.123, 0.777])
@pytest.mark.parametrize("style", CHIME_STYLES)
def test_the_loudest_moment_is_exactly_the_volume_asked_for(style, volume):
    samples = _samples((C5, E5, G5), style, volume=volume)
    assert max(abs(v) for v in samples) == round(volume * 32767)

def test_the_default_volume_is_a_quarter_of_full_scale():
    assert max(abs(v) for v in _samples((C5,))) == 8192

def test_a_volume_of_zero_is_silence():
    samples = _samples((C5, G5), volume=0)
    assert len(samples) == _ms(570)
    assert not any(samples)

@pytest.mark.parametrize("style", CHIME_STYLES)
@pytest.mark.parametrize("notes", [CHANGE_PATTERN, *SPEAKER_PATTERNS])
def test_it_starts_and_ends_in_silence_so_it_does_not_click(style, notes):
    samples = _samples(notes, style)
    peak = max(abs(v) for v in samples)
    assert samples[0] == 0
    assert samples[-1] == 0
    # It lands gently: the last millisecond is nearly silent.
    assert max(abs(v) for v in samples[-44:]) < peak * 0.01

@pytest.mark.parametrize("style, attack_ms", [("bell", 8), ("soft", 15), ("glass", 6), ("wood", 2)])
def test_each_note_rises_instead_of_starting_at_full_strength(style, attack_ms):
    samples = _samples((C5,), style)
    rise = _ms(attack_ms)
    # Half way through the rise the sound is still well below where the
    # rise ends.
    assert max(abs(v) for v in samples[:rise // 2]) < max(abs(v) for v in samples[:rise + 1])
    assert abs(samples[1]) < 8192 * 0.05

@pytest.mark.parametrize("style", CHIME_STYLES)
def test_a_single_note_sounds_at_its_pitch(style):
    samples = _samples((C5,), style)
    at_pitch = _strength_at(samples, C5)
    assert at_pitch > 3 * _strength_at(samples, C5 * 0.8)
    assert at_pitch > 3 * _strength_at(samples, C5 * 1.25)
    assert at_pitch > _strength_at(samples, 2 * C5)

@pytest.mark.parametrize("style", CHIME_STYLES)
def test_the_notes_of_a_pattern_come_in_order(style):
    samples = _samples((C5, G5), style)
    step = _ms(NOTE_STEP_MS)
    before_second = samples[:step]
    # Before the second note starts, only the first one is sounding.
    assert _strength_at(before_second, C5) > 5 * _strength_at(before_second, G5)
    # After it starts, the second one is there too...
    after = samples[step:step + step]
    assert _strength_at(after, G5) > _strength_at(before_second, G5) * 5
    # ...and the first one keeps ringing under it rather than being cut off.
    # (It keeps 11 to 60 percent of its strength, depending on the style.)
    assert _strength_at(after, C5) > _strength_at(before_second, C5) * 0.05

def test_going_up_and_going_down_are_different_sounds():
    up = _samples((C5, G5))
    down = _samples((G5, C5))
    step = _ms(NOTE_STEP_MS)
    assert _strength_at(up[:step], C5) > _strength_at(up[:step], G5)
    assert _strength_at(down[:step], G5) > _strength_at(down[:step], C5)

@pytest.mark.parametrize("style", CHIME_STYLES)
def test_it_fades_away(style):
    samples = _samples((C5,), style)
    tenth = len(samples) // 10
    loudness = [_rms(samples[i * tenth:(i + 1) * tenth]) for i in range(1, 10)]
    assert loudness == sorted(loudness, reverse=True)
    assert loudness[-1] < loudness[0] / 10

def test_wood_dies_away_faster_than_glass():
    wood = _samples((C5,), "wood")
    glass = _samples((C5,), "glass")
    window = _ms(200)
    # How much is left 200 ms in, against the first 50 ms.
    def left(samples):
        return _rms(samples[window:window + _ms(50)]) / _rms(samples[:_ms(50)])
    assert left(wood) < left(glass) / 3

def test_the_styles_sound_different():
    sounds = {chime_wav((C5,), style) for style in CHIME_STYLES}
    assert len(sounds) == len(CHIME_STYLES)

def test_glass_has_a_partial_that_bell_does_not():
    glass = _samples((C5,), "glass")
    bell = _samples((C5,), "bell")
    assert _strength_at(glass, C5 * 2.76) > 5 * _strength_at(bell, C5 * 2.76)
    # It sits at 2.76 times the pitch, not on a whole multiple, which is
    # what makes glass sound like glass.
    assert _strength_at(glass, C5 * 2.76) > 20 * _strength_at(glass, C5 * 3)

@pytest.mark.parametrize("style", ["bell", "wood"])
def test_the_higher_partial_fades_faster_than_the_main_tone(style):
    samples = _samples((C5,), style)
    multiple = {"bell": 2, "wood": 4}[style]
    early = samples[:_ms(50)]
    late = samples[_ms(100):_ms(150)]
    share_early = _strength_at(early, C5 * multiple) / _strength_at(early, C5)
    share_late = _strength_at(late, C5 * multiple) / _strength_at(late, C5)
    assert share_late < share_early / 2

def test_soft_is_a_plain_tone_with_no_octave():
    soft = _samples((C5,), "soft")
    bell = _samples((C5,), "bell")
    assert _strength_at(soft, 2 * C5) < _strength_at(bell, 2 * C5) / 10

def test_the_same_chime_is_the_same_bytes_every_time():
    assert chime_wav((C5, G5), "glass") == chime_wav((C5, G5), "glass")

def test_every_speaker_gets_a_different_sound():
    sounds = {chime_wav(p) for p in SPEAKER_PATTERNS + (CHANGE_PATTERN,)}
    assert len(sounds) == 6

def test_making_the_longest_one_is_quick():
    started = time.perf_counter()
    chime_wav((C5, E5, G5), "glass")
    assert time.perf_counter() - started < 2.0


# ---- What it refuses ----

def test_an_unknown_style_is_refused():
    with pytest.raises(ValueError):
        chime_wav((C5,), "trumpet")

def test_no_notes_is_refused():
    with pytest.raises(ValueError):
        chime_wav(())

@pytest.mark.parametrize("volume", [-0.1, 1.01, 2])
def test_a_volume_outside_zero_to_one_is_refused(volume):
    with pytest.raises(ValueError):
        chime_wav((C5,), volume=volume)

@pytest.mark.parametrize("note", [0, -440])
def test_a_note_that_is_not_above_zero_is_refused(note):
    with pytest.raises(ValueError):
        chime_wav((C5, note))

@pytest.mark.parametrize("style, highest_multiple", [("bell", 3), ("soft", 1), ("glass", 5.40), ("wood", 10)])
def test_a_note_too_high_for_the_style_is_refused(style, highest_multiple):
    # Its highest partial has to stay under half the sample rate.
    limit = SAMPLE_RATE / 2 / highest_multiple
    chime_wav((limit - 1,), style)
    with pytest.raises(ValueError):
        chime_wav((limit,), style)


# ---- The pattern each speaker gets ----

def test_speakers_get_patterns_in_order_of_first_appearance():
    assert speaker_patterns(["Ann", "Bob", "Ann", "Carl", "Bob"]) == {
        "Ann": (C5,), "Bob": (C5, G5), "Carl": (G5, C5),
    }

def test_an_unnamed_change_gets_no_pattern_of_its_own():
    assert speaker_patterns([UNNAMED_SPEAKER, "Ann", UNNAMED_SPEAKER, "Bob"]) == {"Ann": (C5,), "Bob": (C5, G5)}

def test_a_sixth_speaker_starts_again_from_the_first_pattern():
    patterns = speaker_patterns(["A", "B", "C", "D", "E", "F", "G"])
    assert [patterns[s] for s in "ABCDEFG"] == list(SPEAKER_PATTERNS) + [SPEAKER_PATTERNS[0], SPEAKER_PATTERNS[1]]

def test_no_speakers_means_no_patterns():
    assert speaker_patterns([]) == {}


# ---- Which notes a change plays ----

PATTERNS = {"Ann": (C5,), "Bob": (C5, G5)}

def test_off_plays_nothing():
    assert chime_notes("off", "Ann", PATTERNS) is None

def test_one_chime_for_any_change_plays_the_change_chime_for_everyone():
    for speaker in ["Ann", "Bob", UNNAMED_SPEAKER, "Nobody", None]:
        assert chime_notes("change", speaker, PATTERNS) == (A4,)

def test_a_chime_per_speaker_plays_their_own_pattern():
    assert chime_notes("per_speaker", "Ann", PATTERNS) == (C5,)
    assert chime_notes("per_speaker", "Bob", PATTERNS) == (C5, G5)

def test_a_chime_per_speaker_plays_the_change_chime_for_an_unnamed_change():
    assert chime_notes("per_speaker", UNNAMED_SPEAKER, PATTERNS) == (A4,)
    assert chime_notes("per_speaker", "Nobody", PATTERNS) == (A4,)

@pytest.mark.parametrize("sound", ["", "loud", "Change", None, 1])
def test_an_unknown_sound_setting_plays_nothing(sound):
    assert chime_notes(sound, "Ann", PATTERNS) is None

def test_every_sound_setting_is_handled():
    # The settings store's choices and this module's names must agree, or a
    # choice would quietly play nothing.
    results = {sound: chime_notes(sound, "Ann", PATTERNS) for sound in SPEAKER_CUE_SOUNDS}
    assert results == {"off": None, "change": (A4,), "per_speaker": (C5,)}


# ---- The wait between chimes ----

def test_the_first_chime_is_always_allowed():
    assert ChimeGap().allow(0)

def test_a_chime_too_soon_after_a_short_one_is_refused():
    gap = ChimeGap()
    assert gap.allow(1000, length_ms=300)
    assert not gap.allow(1001)
    assert not gap.allow(1399)

def test_after_a_short_chime_the_minimum_gap_is_enough():
    gap = ChimeGap()
    assert gap.allow(1000, length_ms=300)
    assert gap.allow(1400)

def test_a_long_chime_is_never_cut_off():
    gap = ChimeGap()
    assert gap.allow(1000, length_ms=940)
    assert not gap.allow(1400)
    assert not gap.allow(1939)
    assert gap.allow(1940)

def test_a_chime_with_no_length_given_holds_the_minimum_gap():
    gap = ChimeGap()
    assert gap.allow(0)
    assert not gap.allow(399)
    assert gap.allow(400)

def test_a_refused_chime_does_not_move_the_wait():
    gap = ChimeGap()
    assert gap.allow(1000, length_ms=450)
    assert not gap.allow(1300, length_ms=940)
    # Measured from the chime that played (1000 + 450), not the refused one.
    assert gap.allow(1450)

def test_the_wait_counts_from_the_latest_chime_that_played():
    gap = ChimeGap()
    assert gap.allow(0, length_ms=450)
    assert gap.allow(500, length_ms=300)
    assert not gap.allow(800)
    assert gap.allow(900)

def test_a_clock_that_went_backwards_does_not_silence_the_chimes():
    gap = ChimeGap()
    assert gap.allow(5000, length_ms=940)
    assert gap.allow(100)

def test_the_minimum_gap_can_be_set():
    gap = ChimeGap(min_gap_ms=50)
    assert gap.min_gap_ms == 50
    assert gap.allow(0)
    assert not gap.allow(49)
    assert gap.allow(50)

def test_the_default_minimum_gap():
    assert ChimeGap().min_gap_ms == 400
