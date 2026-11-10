"""Works out who is speaking in a labelled transcript, for Speaker cues.

A transcript like this one has speakers:

    Interviewer: So how did it start?
    Speaker 2: In a garage, believe it or not.

A label is a short name at the very start of a line, followed by a colon
and then a space or the end of the line. "Interviewer:", "Speaker 2:",
"Q:" and "Dr. Smith:" all count. A colon with no space after it
doesn't, which keeps "http://..." and "Note:hello" out, and a time such
as "10:30" starts with a digit, so it can't be a label either.

A label can't start with a small letter. Without that rule, any short
start of a sentence before a colon would count ("and Bob: hi", "the
answer is: yes"). Scripts that have no capitals, such as Chinese or
Arabic, aren't affected. The price is that an all-lowercase label
("bob: no") isn't found, and Normalize would join such a line onto the
one before it anyway.

YouTube captions mark a change of speaker with ">>" at the start of a
line and give no name. That counts as a change, with no name attached,
unless a label follows it (">> JOHN: hi"), in which case the label is
used and the ">>" is remembered as a fallback.

The reader never sees line breaks: ReaderSession runs the text through
clean_transcript(), which squeezes all whitespace, line breaks
included, into single spaces before it splits the words. So this
module reads the raw text line by line instead, and counts words
exactly the way the reader does, so a label's position here is the
same word number the reader uses. scan_speakers() also returns how
many words it counted, so the caller can check the two agree before
trusting the positions (they always should, but a mismatch must never
put a cue on the wrong word).

The label word itself stays in the text. "Interviewer:" is still
flashed as a word, so word numbers, saved positions and bookmarks are
the same with Speaker cues on or off.

How it is used, in three steps:

1. scan_speakers(raw_text) finds every label and every ">>".
2. speaker_candidates(scan) lists the speakers found, with how often
   each one appears. auto_speakers() picks the ones that appear at
   least AUTO_MIN_APPEARANCES times, which keeps a stray "Note:" or
   "Example:" out. A speaker who speaks only once is still listed, so
   the user can switch them on by hand.
3. build_turns(scan, speaker_of) turns the labels into turns, given
   which labels are switched on and who each one is. Mapping two labels
   to the same speaker merges them ("Dr. Smith" and "Smith").

No GUI dependency here (see core/ vs gui/ in the project brief)."""

import bisect
import re
from dataclasses import dataclass
from typing import Mapping

from core.parser import strip_timestamps

# The speaker given to a turn that starts with ">>" and has no label we
# use. Real label keys always start with a letter, so this can't clash
# with one.
UNNAMED_SPEAKER = ">>"

# A label this long or longer is more likely the start of a sentence
# than a name.
MAX_LABEL_CHARS = 30
MAX_LABEL_WORDS = 4

# In Auto, a label has to appear at least this many times to count as a
# speaker. Real speakers almost always speak more than once.
AUTO_MIN_APPEARANCES = 2

# A label: a letter first, then letters, digits, spaces, dots,
# apostrophes (straight or curly) and hyphens, then a colon with a space
# or the end of the line after it. Commas, question marks and the like
# aren't allowed, so "Wait, Bob:" or "Ready? Go:" don't count. A space
# before the colon is fine ("Speaker 2 :"), since some transcripts are
# typed that way: it's part of the match and gets squeezed out of the
# name.
_LABEL = re.compile(r"([^\W\d_][\w .'\u2019-]*):(?=\s|$)")

# ">>" at the start of a line, but not ">>>" (that's more likely quoted
# text from an email than a caption).
_CHANGE_MARK = re.compile(r">>(?!>)\s*")

# Only these end a line for the purpose of finding labels. Every one of
# them is also whitespace to str.split(), so splitting here never
# changes which words the reader sees.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


@dataclass(frozen=True)
class LabelHit:
    """One line that starts with a label or a ">>".

    word_index is the reader's word number of the line's first word.
    key is the label in a form that matches however it was typed
    (spaces squeezed, case ignored), or None when the line starts with
    ">>" and no label. name is the label as written, with spaces
    squeezed ("" when there's no label). marked is True when the line
    started with ">>"."""
    word_index: int
    key: str | None
    name: str
    marked: bool


@dataclass(frozen=True)
class SpeakerScan:
    """What scan_speakers() found: every hit in reading order, and how
    many words it counted in the whole text."""
    word_count: int
    hits: tuple[LabelHit, ...]


@dataclass(frozen=True)
class SpeakerCandidate:
    """A speaker found in the text: its key, its name as first written,
    and how many lines it starts."""
    key: str
    name: str
    appearances: int


@dataclass(frozen=True)
class SpeakerTurns:
    """Who is speaking where. starts[i] is the word number a turn begins
    at, and speakers[i] is who speaks in it (UNNAMED_SPEAKER for a ">>"
    turn). starts is sorted and has no repeats. Words before the first
    turn belong to no one."""
    starts: tuple[int, ...] = ()
    speakers: tuple[str, ...] = ()

    def speaker_at(self, word_index: int) -> str | None:
        """Who is speaking at this word, or None before the first turn."""
        i = bisect.bisect_right(self.starts, word_index) - 1
        return self.speakers[i] if i >= 0 else None

    def is_turn_start(self, word_index: int) -> bool:
        """Whether a new turn begins at this word."""
        i = bisect.bisect_left(self.starts, word_index)
        return i < len(self.starts) and self.starts[i] == word_index


def label_key(name: str) -> str:
    """The form used to match labels, so "INTERVIEWER", "Interviewer"
    and "Interviewer " are one speaker."""
    return " ".join(name.split()).casefold()


def _read_label(text: str) -> str | None:
    """The label at the start of text, as written with spaces squeezed,
    or None if text doesn't start with one."""
    match = _LABEL.match(text)
    if match is None:
        return None
    name = " ".join(match.group(1).split())
    if name[0].islower():
        return None
    if len(name) > MAX_LABEL_CHARS or len(name.split()) > MAX_LABEL_WORDS:
        return None
    return name


def scan_speakers(raw_text: str) -> SpeakerScan:
    """Find every line that starts with a label or a ">>", with the word
    number (as the reader counts) of that line's first word."""
    # Timestamps go first, over the whole text, exactly as
    # clean_transcript() does, so both see the same words.
    text = strip_timestamps(raw_text)
    hits = []
    word_count = 0
    for line in _LINE_BREAK.split(text):
        words_in_line = len(line.split())
        rest = line.lstrip()
        change = _CHANGE_MARK.match(rest)
        if change is not None:
            rest = rest[change.end():]
        name = _read_label(rest)
        if name is not None:
            hits.append(LabelHit(word_count, label_key(name), name, change is not None))
        elif change is not None:
            hits.append(LabelHit(word_count, None, "", True))
        word_count += words_in_line
    return SpeakerScan(word_count, tuple(hits))


def speaker_candidates(scan: SpeakerScan) -> list[SpeakerCandidate]:
    """Every label found, in order of first appearance, with how many
    lines it starts and its name as first written."""
    names: dict[str, str] = {}
    counts: dict[str, int] = {}
    for hit in scan.hits:
        if hit.key is None:
            continue
        names.setdefault(hit.key, hit.name)
        counts[hit.key] = counts.get(hit.key, 0) + 1
    return [SpeakerCandidate(key, names[key], counts[key]) for key in names]


def auto_speakers(candidates: list[SpeakerCandidate]) -> dict[str, str]:
    """What Auto switches on: every label that appears at least
    AUTO_MIN_APPEARANCES times, each its own speaker. Shaped for
    build_turns()."""
    return {c.key: c.key for c in candidates if c.appearances >= AUTO_MIN_APPEARANCES}


def build_turns(scan: SpeakerScan, speaker_of: Mapping[str, str]) -> SpeakerTurns:
    """Turn the hits into turns.

    speaker_of maps each label key that's switched on to the speaker it
    belongs to. A label that isn't in it is ignored, as if it were
    ordinary text, except that a ">>" in front of it still marks an
    unnamed change. A turn by the same named speaker as the one before
    it isn't a change, so it's folded into that one (a speaker's answer
    split over two labelled paragraphs, or two merged labels in a row).
    Two ">>" in a row stay two changes, since there's no telling whether
    it's the same person."""
    starts: list[int] = []
    speakers: list[str] = []
    for hit in scan.hits:
        speaker = speaker_of.get(hit.key) if hit.key is not None else None
        if speaker is None:
            if not hit.marked:
                continue
            speaker = UNNAMED_SPEAKER
        if speakers and speaker == speakers[-1] and speaker != UNNAMED_SPEAKER:
            continue
        starts.append(hit.word_index)
        speakers.append(speaker)
    return SpeakerTurns(tuple(starts), tuple(speakers))