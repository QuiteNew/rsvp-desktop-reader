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

A transcript keeps the user's own picks, if any, in
Transcript.speaker_custom, already shaped for build_turns().
clean_custom_speakers() makes a saved one safe to use.
transcript_speakers() gives the list a whole transcript is read with,
which is also the one a selection played on its own is read with.
speaker_rows() and speakers_to_save() are the two ends of the speaker
list in the Configure speaker cues window: what it shows, and what it
saves.

No GUI dependency here (see core/ vs gui/ in the project brief)."""

import bisect
import re
from dataclasses import dataclass
from typing import Iterable, Mapping

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


def clean_custom_speakers(value) -> dict[str, str] | None:
    """A transcript's Custom speaker list (Transcript.speaker_custom) made
    safe to use, for when it comes from a save file, an import or the
    Settings window.

    None means Auto and stays None. So does anything that isn't a dict at
    all, so a damaged value falls back to Auto rather than to no speakers.
    Inside a dict, an entry is kept only when its key is a label key the
    way label_key() makes it, and its name, with spaces squeezed, is 1 to
    MAX_LABEL_CHARS characters long. Anything else is dropped on its own,
    so one bad entry doesn't cost the rest. An empty dict stays empty:
    Custom with every speaker switched off is a real choice. The answer is
    always a new dict, never the one passed in."""
    if not isinstance(value, dict):
        return None
    cleaned = {}
    for key, name in value.items():
        if not isinstance(key, str) or not key or key != label_key(key):
            continue
        if not isinstance(name, str):
            continue
        name = " ".join(name.split())
        if 0 < len(name) <= MAX_LABEL_CHARS:
            cleaned[key] = name
    return cleaned


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
    AUTO_MIN_APPEARANCES times, each its own speaker, named the way it was
    first written. That's the same shape a Custom list has (label key to
    the name shown), so either one goes straight into build_turns(), and a
    speaker is known by the name shown in both."""
    return {c.key: c.name for c in candidates if c.appearances >= AUTO_MIN_APPEARANCES}


@dataclass(frozen=True)
class SpeakerRow:
    """One line of the speaker list in the Configure speaker cues window: a
    label found in the transcript, how many lines it starts, whether it's
    ticked (switched on) and the name it's shown with."""
    key: str
    label: str
    appearances: int
    ticked: bool
    name: str


def speaker_rows(raw_text: str, custom: Mapping[str, str] | None = None) -> list[SpeakerRow]:
    """The rows the window shows for a transcript: every label found in
    raw_text, the ones seen only once included, in order of first
    appearance. A row is ticked and named the way the transcript's own list
    has it, or the way Auto would when it has no list of its own (None).
    A row that isn't in the list shows its label as its name, ready to be
    ticked."""
    candidates = speaker_candidates(scan_speakers(raw_text))
    chosen = dict(custom) if custom is not None else auto_speakers(candidates)
    return [
        SpeakerRow(c.key, c.name, c.appearances, c.key in chosen, chosen.get(c.key, c.name))
        for c in candidates
    ]


def speaker_row_name(row: SpeakerRow) -> str:
    """The name a row is saved with: what was typed, with its spaces
    squeezed and cut to MAX_LABEL_CHARS, or the label itself when the box
    was left empty. Two rows saved with the same name are one speaker."""
    name = " ".join(row.name.split())[:MAX_LABEL_CHARS].rstrip()
    return name or row.label


def speakers_to_save(rows: Iterable[SpeakerRow]) -> dict[str, str] | None:
    """What the window saves as the transcript's speaker list
    (Transcript.speaker_custom): every ticked row, by its key, with
    speaker_row_name() as the name.

    When that's exactly what Auto picks anyway, the answer is None
    (Automatic) and not a Custom list that happens to match. So ticking a
    box and unticking it again leaves the transcript on Automatic, and it
    keeps following the text if the text changes later."""
    rows = list(rows)
    chosen = {row.key: speaker_row_name(row) for row in rows if row.ticked}
    auto = {row.key: row.label for row in rows if row.appearances >= AUTO_MIN_APPEARANCES}
    return None if chosen == auto else chosen


def transcript_speakers(raw_text: str, custom: Mapping[str, str] | None = None) -> dict[str, str]:
    """The speaker list a whole transcript is read with: its own Custom
    list when it has one (even an empty one), otherwise what Auto finds in
    raw_text.

    A selection played on its own (right-click Play or Detach) is read
    with this list, worked out from the whole transcript, and not with
    one worked out from the selection alone. A short selection often
    holds each label only once, so Auto would switch none of them on,
    even though the whole transcript shows they're speakers. Handed to
    ReaderSession as its speaker_custom, this list makes a label in the
    selection count exactly the way it does when the whole transcript is
    read.

    Always a new dict, so changing it never changes the transcript's
    own."""
    if custom is not None:
        return dict(custom)
    return auto_speakers(speaker_candidates(scan_speakers(raw_text)))


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