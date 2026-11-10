"""Tests for core/chime.py: the chime's sound file, the pitch each speaker
gets, which pitch a change plays, and the minimum gap between chimes.

What the chime sounds like can only be judged by ear. These tests check what
can be measured: that it's a proper WAV file of the right length, as loud as
asked and never louder, silent at both ends so it doesn't click, at the pitch
asked for, and fading away."""

import io
import math
import time
import wave
from array import array

import pytest

from core.chime import (
    CHANGE_PITCH_HZ, CHIME_DURATION_MS, CHIME_VOLUME, MIN_CHIME_GAP_MS, SAMPLE_RATE, SPEAKER_PITCHES_HZ,
    ChimeGap, chime_pitch, chime_wav, speaker_pitches,
)
from core.settings_store import SPEAKER_CUE_SOUNDS
from core.speakers import UNNAMED_SPEAKER


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


# ---- The settings the chime is made with ----

def test_the_tuning_values():
    # Pinned as plain numbers, so a change to any of them shows up here.
    assert SAMPLE_RATE == 44100
    assert CHIME_DURATION_MS == 450
    assert CHIME_VOLUME == 0.25
    assert MIN_CHIME_GAP_MS == 400
    assert SPEAKER_PITCHES_HZ == (523.25, 587.33, 659.25, 783.99, 880.0)
    assert CHANGE_PITCH_HZ == 440.0

def test_the_speaker_pitches_rise_and_the_change_chime_is_none_of_them():
    assert list(SPEAKER_PITCHES_HZ) == sorted(set(SPEAKER_PITCHES_HZ))
    assert CHANGE_PITCH_HZ not in SPEAKER_PITCHES_HZ


# ---- The sound file ----

def test_it_is_a_mono_sixteen_bit_wav_of_the_right_length():
    channels, width, rate, samples = _read(chime_wav(CHANGE_PITCH_HZ))
    assert (channels, width, rate) == (1, 2, 44100)
    assert len(samples) == round(44100 * 450 / 1000) == 19845

@pytest.mark.parametrize("duration_ms", [1, 100, 1000])
def test_the_length_follows_the_duration(duration_ms):
    samples = _read(chime_wav(CHANGE_PITCH_HZ, duration_ms=duration_ms))[3]
    assert len(samples) == round(SAMPLE_RATE * duration_ms / 1000)

@pytest.mark.parametrize("volume", [0.25, 0.5, 0.1, 1.0, 0.123, 0.777])
def test_the_loudest_moment_is_exactly_the_volume_asked_for(volume):
    samples = _read(chime_wav(CHANGE_PITCH_HZ, volume=volume))[3]
    assert max(abs(v) for v in samples) == round(volume * 32767)

def test_the_default_volume_is_a_quarter_of_full_scale():
    samples = _read(chime_wav(CHANGE_PITCH_HZ))[3]
    assert max(abs(v) for v in samples) == 8192

@pytest.mark.parametrize("duration_ms, samples", [(0.01, 0), (0.02, 1)])
def test_a_chime_too_short_to_hold_any_sound_is_silent_rather_than_an_error(duration_ms, samples):
    # One sample or none at all: there's nothing to scale, so it must not
    # divide by a loudness of zero.
    result = _read(chime_wav(CHANGE_PITCH_HZ, duration_ms=duration_ms))[3]
    assert len(result) == samples
    assert not any(result)

def test_a_volume_of_zero_is_silence():
    samples = _read(chime_wav(CHANGE_PITCH_HZ, volume=0))[3]
    assert len(samples) == 19845
    assert not any(samples)

@pytest.mark.parametrize("pitch", [CHANGE_PITCH_HZ, *SPEAKER_PITCHES_HZ])
def test_it_starts_and_ends_in_silence_so_it_does_not_click(pitch):
    samples = _read(chime_wav(pitch))[3]
    assert samples[0] == 0
    assert samples[-1] == 0
    # It rises gently: the first millisecond stays far below the peak.
    assert max(abs(v) for v in samples[:44]) < 8192 * 0.05
    # And it lands gently: the last millisecond is nearly silent.
    assert max(abs(v) for v in samples[-44:]) < 8192 * 0.01

@pytest.mark.parametrize("pitch", [CHANGE_PITCH_HZ, *SPEAKER_PITCHES_HZ])
def test_it_sounds_at_the_pitch_asked_for(pitch):
    samples = _read(chime_wav(pitch))[3]
    at_pitch = _strength_at(samples, pitch)
    # Stronger than its own octave and third harmonic, which are only there
    # to colour it...
    assert at_pitch > 3 * _strength_at(samples, 2 * pitch)
    assert at_pitch > 10 * _strength_at(samples, 3 * pitch)
    # ...and than a pitch a little way off either side.
    assert at_pitch > 10 * _strength_at(samples, pitch * 0.8)
    assert at_pitch > 10 * _strength_at(samples, pitch * 1.25)

def test_it_has_a_quiet_octave_on_top():
    samples = _read(chime_wav(CHANGE_PITCH_HZ))[3]
    octave = _strength_at(samples, 2 * CHANGE_PITCH_HZ)
    assert octave > 10 * _strength_at(samples, 1.5 * CHANGE_PITCH_HZ)

def test_it_fades_away():
    samples = _read(chime_wav(CHANGE_PITCH_HZ))[3]
    tenth = len(samples) // 10
    loudness = [_rms(samples[i * tenth:(i + 1) * tenth]) for i in range(10)]
    assert loudness == sorted(loudness, reverse=True)
    assert loudness[-1] < loudness[0] / 20

def test_the_same_chime_is_the_same_bytes_every_time():
    assert chime_wav(587.33) == chime_wav(587.33)

def test_different_pitches_are_different_sounds():
    assert len({chime_wav(p) for p in SPEAKER_PITCHES_HZ + (CHANGE_PITCH_HZ,)}) == 6

def test_making_one_is_quick():
    started = time.perf_counter()
    chime_wav(CHANGE_PITCH_HZ)
    assert time.perf_counter() - started < 1.0

@pytest.mark.parametrize("pitch", [0, -440, 22050, 30000])
def test_a_pitch_a_file_cannot_hold_is_refused(pitch):
    with pytest.raises(ValueError):
        chime_wav(pitch)

@pytest.mark.parametrize("duration_ms", [0, -100])
def test_a_chime_with_no_length_is_refused(duration_ms):
    with pytest.raises(ValueError):
        chime_wav(CHANGE_PITCH_HZ, duration_ms=duration_ms)

@pytest.mark.parametrize("volume", [-0.1, 1.01, 2])
def test_a_volume_outside_zero_to_one_is_refused(volume):
    with pytest.raises(ValueError):
        chime_wav(CHANGE_PITCH_HZ, volume=volume)

def test_the_highest_pitch_a_file_can_hold_still_works():
    samples = _read(chime_wav(22049))[3]
    assert max(abs(v) for v in samples) <= 8192


# ---- The pitch each speaker gets ----

def test_speakers_get_pitches_in_order_of_first_appearance():
    assert speaker_pitches(["Ann", "Bob", "Ann", "Carl", "Bob"]) == {
        "Ann": 523.25, "Bob": 587.33, "Carl": 659.25,
    }

def test_an_unnamed_change_gets_no_pitch_of_its_own():
    assert speaker_pitches([UNNAMED_SPEAKER, "Ann", UNNAMED_SPEAKER, "Bob"]) == {"Ann": 523.25, "Bob": 587.33}

def test_a_sixth_speaker_starts_again_from_the_first_pitch():
    pitches = speaker_pitches(["A", "B", "C", "D", "E", "F", "G"])
    assert [pitches[s] for s in "ABCDEFG"] == [523.25, 587.33, 659.25, 783.99, 880.0, 523.25, 587.33]

def test_no_speakers_means_no_pitches():
    assert speaker_pitches([]) == {}


# ---- Which pitch a change plays ----

PITCHES = {"Ann": 523.25, "Bob": 587.33}

def test_off_plays_nothing():
    assert chime_pitch("off", "Ann", PITCHES) is None

def test_one_chime_for_any_change_plays_the_change_chime_for_everyone():
    for speaker in ["Ann", "Bob", UNNAMED_SPEAKER, "Nobody", None]:
        assert chime_pitch("change", speaker, PITCHES) == 440.0

def test_a_chime_per_speaker_plays_their_own_pitch():
    assert chime_pitch("per_speaker", "Ann", PITCHES) == 523.25
    assert chime_pitch("per_speaker", "Bob", PITCHES) == 587.33

def test_a_chime_per_speaker_plays_the_change_chime_for_an_unnamed_change():
    assert chime_pitch("per_speaker", UNNAMED_SPEAKER, PITCHES) == 440.0
    assert chime_pitch("per_speaker", "Nobody", PITCHES) == 440.0

@pytest.mark.parametrize("sound", ["", "loud", "Change", None, 1])
def test_an_unknown_sound_setting_plays_nothing(sound):
    assert chime_pitch(sound, "Ann", PITCHES) is None

def test_every_sound_setting_is_handled():
    # The settings store's choices and this module's names must agree, or a
    # choice would quietly play nothing.
    results = {sound: chime_pitch(sound, "Ann", PITCHES) for sound in SPEAKER_CUE_SOUNDS}
    assert results == {"off": None, "change": 440.0, "per_speaker": 523.25}


# ---- The gap between chimes ----

def test_the_first_chime_is_always_allowed():
    assert ChimeGap().allow(0)

def test_a_chime_too_soon_after_the_last_is_refused():
    gap = ChimeGap()
    assert gap.allow(1000)
    assert not gap.allow(1001)
    assert not gap.allow(1399)

def test_a_chime_exactly_the_gap_later_is_allowed():
    gap = ChimeGap()
    assert gap.allow(1000)
    assert gap.allow(1400)

def test_a_refused_chime_does_not_move_the_gap():
    gap = ChimeGap()
    assert gap.allow(1000)
    assert not gap.allow(1300)
    # 1400 is 400 after the last chime that played, though only 100 after
    # the refused one.
    assert gap.allow(1400)

def test_the_gap_counts_from_the_latest_chime_that_played():
    gap = ChimeGap()
    assert gap.allow(0)
    assert gap.allow(500)
    assert not gap.allow(800)
    assert gap.allow(900)

def test_a_clock_that_went_backwards_does_not_silence_the_chimes():
    gap = ChimeGap()
    assert gap.allow(5000)
    assert gap.allow(100)

def test_the_gap_can_be_set():
    gap = ChimeGap(min_gap_ms=50)
    assert gap.min_gap_ms == 50
    assert gap.allow(0)
    assert not gap.allow(49)
    assert gap.allow(50)

def test_the_default_gap():
    assert ChimeGap().min_gap_ms == 400
