"""The chime Speaker cues plays when the speaker changes: what it sounds like,
which pattern of notes each speaker gets, and how close together two chimes
may be.

Everything here is pure. chime_wav() builds the bytes of a WAV file and never
writes or plays anything. The GUI writes those bytes to a file once and plays
the file, because on Windows winsound can only play a sound without holding
up the app when the sound is a file on disk (see the Speaker cues design
note).

The sound is made here rather than shipped as a recording, so there is no
licence to check, nothing extra in the repo or the download, and every pitch
is just a number.

There are a few styles to pick from (CHIME_STYLES), each a different tone:
a small bell, a plain soft tone, a brighter glass, and a short knock of wood.
Every note rises over a few milliseconds instead of starting at full
strength, fades away on its own, and the whole chime ends exactly at silence,
so it never clicks.

Speakers are told apart by the shape of their chime as well as its pitch:
one note, two going up, two going down, one higher note, three going up. A
shape is much easier to recognise without thinking than a small change of
pitch, which is what the first version had and why it was changed.

No GUI dependency here (see core/ vs gui/ in the project brief)."""

import io
import math
import wave
from array import array
from typing import Iterable, NamedTuple, Sequence

from core.speakers import UNNAMED_SPEAKER

SAMPLE_RATE = 44100

# How loud a chime's loudest moment is, as a share of the loudest a sound
# file can be. winsound has no volume control, so the loudness is part of
# the file. A starting point chosen by ear.
CHIME_VOLUME = 0.25

# The time from one note of a pattern to the next.
NOTE_STEP_MS = 120

# Notes, in Hz: C, E, G and C an octave up, with the A below them for the
# change chime. They all come from one scale (C major pentatonic), so any of
# them sound fine together and one after the other.
_A4 = 440.0
_C5 = 523.25
_E5 = 659.25
_G5 = 783.99
_C6 = 1046.5

# The pattern each speaker gets, in order of first appearance. A sixth
# speaker starts again from the first.
SPEAKER_PATTERNS = (
    (_C5,),            # one note
    (_C5, _G5),        # two notes going up
    (_G5, _C5),        # two notes going down
    (_C6,),            # one note, an octave higher
    (_C5, _E5, _G5),   # three notes going up
)

# The pattern for "one chime for any change", and for a ">>" change (no
# name, so no pattern of its own) when each speaker has one. A single note
# below all the speakers' notes, so it doesn't sound like any of them.
CHANGE_PATTERN = (_A4,)

# The shortest time between the starts of two chimes. At a high speed with
# fast back-and-forth, a chime at every change would turn into constant
# noise, so a change that comes sooner than this stays silent (the visual
# cue still shows it). See ChimeGap, which also waits for a longer chime to
# finish.
MIN_CHIME_GAP_MS = 400


class ChimeStyle(NamedTuple):
    """How one style sounds. partials are the tone's ingredients:
    (multiple of the note's pitch, strength, how much faster than the main
    tone it dies away), so higher ones fade first, the way a real bell's do.
    decay_ms is how quickly the note dies away, attack_ms how long it takes
    to rise, and note_ms how long each note lasts in all."""
    partials: tuple[tuple[float, float, float], ...]
    decay_ms: float
    attack_ms: float
    note_ms: int


# The styles, in the order the Settings window lists them. The first is the
# default. Their names are what settings.json stores.
CHIME_STYLES = ("bell", "soft", "glass", "wood")

_STYLES = {
    # A small bell: a sine with a quieter octave and a faint third harmonic.
    "bell": ChimeStyle(((1, 1.0, 1.0), (2, 0.25, 2.0), (3, 0.08, 3.0)), 110, 8, 450),
    # A plain, rounded tone: just the sine, rising slowly.
    "soft": ChimeStyle(((1, 1.0, 1.0),), 150, 15, 500),
    # Glass: brighter, with partials that aren't whole multiples, and rings
    # a little longer.
    "glass": ChimeStyle(((1, 1.0, 1.0), (2.76, 0.20, 1.4), (5.40, 0.06, 2.0)), 220, 6, 700),
    # Wood: a short knock, like a marimba, gone almost at once.
    "wood": ChimeStyle(((1, 1.0, 1.0), (4, 0.35, 3.0), (10, 0.05, 6.0)), 55, 2, 300),
}

# The last stretch of every note, taken down to exact silence.
_END_FADE_MS = 40

_FULL_SCALE = 32767


def chime_length_ms(notes: Sequence[float], style: str = CHIME_STYLES[0]) -> int:
    """How long a chime of these notes lasts in this style, from the start of
    the first note to the end of the last one."""
    return _STYLES[style].note_ms + NOTE_STEP_MS * (len(notes) - 1)


def chime_wav(notes: Sequence[float], style: str = CHIME_STYLES[0], volume: float = CHIME_VOLUME) -> bytes:
    """The bytes of a WAV file (mono, 16-bit, SAMPLE_RATE) holding one chime:
    these notes, NOTE_STEP_MS apart, in this style. Its loudest moment is
    exactly volume times the loudest a file can be, so it never clips, and a
    volume of 0 gives silence. The same arguments always give the same bytes.

    Raises ValueError for no notes, an unknown style, a volume outside 0 to
    1, or a note that isn't above 0 or whose highest partial in this style
    would be at or above half the sample rate (a file can't hold that)."""
    if style not in _STYLES:
        raise ValueError(f"There is no chime style called {style!r}.")
    if not notes:
        raise ValueError("A chime needs at least one note.")
    if not 0 <= volume <= 1:
        raise ValueError(f"A chime's volume must be between 0 and 1, not {volume}.")
    sound = _STYLES[style]
    highest_multiple = max(multiple for multiple, _, _ in sound.partials)
    for note in notes:
        if not 0 < note * highest_multiple < SAMPLE_RATE / 2:
            raise ValueError(f"A {style} chime can't hold a note of {note} Hz.")

    total = round(SAMPLE_RATE * chime_length_ms(notes, style) / 1000)
    note_length = round(SAMPLE_RATE * sound.note_ms / 1000)
    step = round(SAMPLE_RATE * NOTE_STEP_MS / 1000)
    attack = max(1, round(SAMPLE_RATE * sound.attack_ms / 1000))
    end_fade = max(1, round(SAMPLE_RATE * _END_FADE_MS / 1000))
    decay_seconds = sound.decay_ms / 1000

    raw = [0.0] * total
    for index, note in enumerate(notes):
        start = index * step
        for n in range(min(note_length, total - start)):
            t = n / SAMPLE_RATE
            value = 0.0
            for multiple, strength, speed in sound.partials:
                value += strength * math.exp(-t * speed / decay_seconds) * math.sin(2 * math.pi * note * multiple * t)
            # The rise at the start of the note, a half cosine from 0 to 1.
            if n < attack:
                value *= 0.5 - 0.5 * math.cos(math.pi * n / attack)
            # The note's last stretch, straight down to exact silence.
            left = note_length - 1 - n
            if left < end_fade:
                value *= left / end_fade
            raw[start + n] += value

    # The loudest sample is set to a whole number first, then everything is
    # scaled to it, so the peak lands on it exactly instead of a rounding
    # step either side. Every style's notes last hundreds of milliseconds,
    # so there is always a peak to scale by.
    peak = max(abs(v) for v in raw)
    target = round(volume * _FULL_SCALE)
    scale = target / peak
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


def speaker_patterns(speakers: Iterable[str]) -> dict[str, tuple[float, ...]]:
    """The pattern each speaker gets, from SPEAKER_PATTERNS in order of first
    appearance (pass the speakers of a session's turns, in reading order). A
    ">>" change has no name, so it gets no pattern here; chime_notes() gives
    it the change chime. After the last pattern it starts again from the
    first."""
    patterns: dict[str, tuple[float, ...]] = {}
    for speaker in speakers:
        if speaker == UNNAMED_SPEAKER or speaker in patterns:
            continue
        patterns[speaker] = SPEAKER_PATTERNS[len(patterns) % len(SPEAKER_PATTERNS)]
    return patterns


def chime_notes(sound: str, speaker: str | None, patterns: dict[str, tuple[float, ...]]) -> tuple[float, ...] | None:
    """Which notes to play for a change to this speaker, given the sound
    setting (one of core/settings_store.py's SPEAKER_CUE_SOUNDS) and the
    patterns from speaker_patterns(), or None for no chime at all.

    "change" plays the change chime for everyone. "per_speaker" plays each
    speaker's own pattern, and the change chime for a speaker without one (a
    ">>" change). "off", or anything else, plays nothing."""
    if sound == "change":
        return CHANGE_PATTERN
    if sound == "per_speaker":
        return patterns.get(speaker, CHANGE_PATTERN)
    return None


class ChimeGap:
    """Keeps chimes from piling up or cutting each other off. The GUI asks
    allow() with the current time (in milliseconds, from a clock that only
    goes forward) and the length of the chime it wants to play. A chime is
    refused while the last one that played is still sounding, and within
    min_gap_ms of its start even if it was shorter than that: playing a new
    sound stops the old one mid-note on Windows, which clicks. A refused
    chime doesn't count, so the wait is always measured from the last chime
    that actually played."""

    def __init__(self, min_gap_ms: int = MIN_CHIME_GAP_MS):
        self.min_gap_ms = min_gap_ms
        self._last_ms: float | None = None
        self._hold_ms = 0

    def allow(self, now_ms: float, length_ms: int = 0) -> bool:
        if self._last_ms is not None and 0 <= now_ms - self._last_ms < self._hold_ms:
            return False
        self._last_ms = now_ms
        self._hold_ms = max(self.min_gap_ms, length_ms)
        return True
