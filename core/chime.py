"""The chime Speaker cues plays when the speaker changes: the sound itself,
which pitch each speaker gets, and how close together two chimes may be.

Everything here is pure. chime_wav() builds the bytes of a WAV file and never
writes or plays anything. The GUI writes those bytes to a file once and plays
the file, because on Windows winsound can only play a sound without holding
up the app when the sound is a file on disk (see the Speaker cues design
note).

The sound is made here rather than shipped as a recording, so there is no
licence to check, nothing extra in the repo or the download, and every pitch
is just a number.

The tone is meant to be soft: a sine wave with a quieter octave and a faint
third harmonic on top, which makes it sound like a small bell rather than a
beep. It rises over a few milliseconds instead of starting at full strength,
fades away on its own, and ends exactly at silence, so it never clicks.

No GUI dependency here (see core/ vs gui/ in the project brief)."""

import io
import math
import wave
from array import array
from typing import Iterable

from core.speakers import UNNAMED_SPEAKER

SAMPLE_RATE = 44100

# How long one chime lasts, and how loud its peak is, as a share of the
# loudest a sound file can be. winsound has no volume control, so the
# loudness is part of the file. Both are starting points chosen by ear, to be
# judged on a real machine.
CHIME_DURATION_MS = 450
CHIME_VOLUME = 0.25

# The pitches speakers get, in order of first appearance: C, D, E, G and A
# in the octave above middle C, a pentatonic scale. Any two of these sound
# fine one after the other, so whichever speakers follow each other the
# chimes never clash. A sixth speaker starts again from the first.
SPEAKER_PITCHES_HZ = (523.25, 587.33, 659.25, 783.99, 880.0)

# The one chime used for "one chime for any change", and for a ">>" change
# (no name, so no pitch of its own) when each speaker has one. It's the A
# below the speakers' notes: from the same scale, so it fits with them, but
# not the same pitch as any of them.
CHANGE_PITCH_HZ = 440.0

# The shortest time between two chimes. At a high speed with fast
# back-and-forth, a chime at every change would turn into constant noise, so
# a change that comes sooner than this after the last chime stays silent
# (the visual cue still shows it).
MIN_CHIME_GAP_MS = 400

# The shape of the sound over time: a short rise at the start so it doesn't
# click on, a natural fade (how quickly it dies away), and a final stretch
# that takes whatever is left down to exact silence.
_ATTACK_MS = 8
_DECAY_MS = 110
_END_FADE_MS = 40

# The tone's ingredients: (multiple of the pitch, strength, how much faster
# than the main tone it dies away). Higher partials fade first, the way a
# real bell's do.
_PARTIALS = ((1, 1.0, 1.0), (2, 0.25, 2.0), (3, 0.08, 3.0))

_FULL_SCALE = 32767


def chime_wav(frequency_hz: float, duration_ms: int = CHIME_DURATION_MS, volume: float = CHIME_VOLUME) -> bytes:
    """The bytes of a WAV file (mono, 16-bit, SAMPLE_RATE) holding one chime
    at this pitch. Its loudest moment is exactly volume times the loudest a
    file can be, so it never clips, and a volume of 0 gives silence. The same
    arguments always give the same bytes.

    Raises ValueError for a pitch that isn't above 0 and below half the
    sample rate (above that a file can't hold it), a length that isn't above
    0, or a volume outside 0 to 1."""
    if not 0 < frequency_hz < SAMPLE_RATE / 2:
        raise ValueError(f"A chime's pitch must be between 0 and {SAMPLE_RATE // 2} Hz, not {frequency_hz}.")
    if duration_ms <= 0:
        raise ValueError(f"A chime has to last some time, not {duration_ms} ms.")
    if not 0 <= volume <= 1:
        raise ValueError(f"A chime's volume must be between 0 and 1, not {volume}.")

    count = round(SAMPLE_RATE * duration_ms / 1000)
    attack = max(1, round(SAMPLE_RATE * _ATTACK_MS / 1000))
    end_fade = max(1, round(SAMPLE_RATE * _END_FADE_MS / 1000))
    decay_seconds = _DECAY_MS / 1000

    raw = []
    for n in range(count):
        t = n / SAMPLE_RATE
        value = 0.0
        for multiple, strength, speed in _PARTIALS:
            value += strength * math.exp(-t * speed / decay_seconds) * math.sin(2 * math.pi * frequency_hz * multiple * t)
        # The rise at the start, a half cosine from 0 to 1.
        if n < attack:
            value *= 0.5 - 0.5 * math.cos(math.pi * n / attack)
        # The last stretch, straight down to exact silence on the last sample.
        left = count - 1 - n
        if left < end_fade:
            value *= left / end_fade
        raw.append(value)

    # The loudest sample is set to a whole number first, then everything is
    # scaled to it, so the peak lands on it exactly instead of a rounding
    # step either side.
    peak = max((abs(v) for v in raw), default=0.0)
    target = round(volume * _FULL_SCALE)
    scale = target / peak if peak > 0 else 0.0
    samples = array("h", (round(v * scale) for v in raw))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        # WAV files are little-endian. array uses the machine's own order,
        # which is little-endian on every machine this app runs on, but
        # swapping on a big-endian one keeps the file right anyway.
        if array("h", [1]).tobytes() != b"\x01\x00":
            samples.byteswap()
        wav.writeframes(samples.tobytes())
    return buffer.getvalue()


def speaker_pitches(speakers: Iterable[str]) -> dict[str, float]:
    """The pitch each speaker gets, from SPEAKER_PITCHES_HZ in order of first
    appearance (pass the speakers of a session's turns, in reading order).
    A ">>" change has no name, so it gets no pitch here; chime_pitch() gives
    it the change chime. After the last pitch it starts again from the
    first."""
    pitches: dict[str, float] = {}
    for speaker in speakers:
        if speaker == UNNAMED_SPEAKER or speaker in pitches:
            continue
        pitches[speaker] = SPEAKER_PITCHES_HZ[len(pitches) % len(SPEAKER_PITCHES_HZ)]
    return pitches


def chime_pitch(sound: str, speaker: str | None, pitches: dict[str, float]) -> float | None:
    """Which pitch to play for a change to this speaker, given the sound
    setting (one of core/settings_store.py's SPEAKER_CUE_SOUNDS) and the
    pitches from speaker_pitches(), or None for no chime at all.

    "change" plays the change chime for everyone. "per_speaker" plays each
    speaker's own pitch, and the change chime for a speaker without one (a
    ">>" change). "off", or anything else, plays nothing."""
    if sound == "change":
        return CHANGE_PITCH_HZ
    if sound == "per_speaker":
        return pitches.get(speaker, CHANGE_PITCH_HZ)
    return None


class ChimeGap:
    """Keeps chimes at least min_gap_ms apart. The GUI asks allow() with the
    current time (in milliseconds, from a clock that only goes forward)
    before each chime. The time of a chime that was allowed is remembered; a
    refused one doesn't count, so the gap is always measured from the last
    chime that actually played."""

    def __init__(self, min_gap_ms: int = MIN_CHIME_GAP_MS):
        self.min_gap_ms = min_gap_ms
        self._last_ms: float | None = None

    def allow(self, now_ms: float) -> bool:
        if self._last_ms is not None and 0 <= now_ms - self._last_ms < self.min_gap_ms:
            return False
        self._last_ms = now_ms
        return True
