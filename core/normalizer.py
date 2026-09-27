"""Tidies up a transcript's layout on request, for the edit view's
Normalize button.

Removes list markers (numbering and bullets) and puts each list item in
its own paragraph, keeps headings such as "Chapter 3" on their own
line, drops lines that are only a number (usually PDF page numbers),
and rejoins lines that were broken in the middle of a sentence.

It removes timestamps, using core/parser.py's TIMESTAMP_PATTERN so it
agrees with reading and importing: any in square brackets or
parentheses ("[00:01:23]", "(1:23)"), full hour:minute:second ones
("00:02:45"), subtitle timing lines, and a bare "0:05" alone on its
line. A "10:30" inside a sentence is left alone, since that's usually a
time of day. A line that held nothing but a timestamp is dropped,
rather than being left behind as a blank line that would split a
paragraph.

It also repairs two kinds of damage that text pulled out of a PDF
often has. Combined letters such as "ﬁ" become plain letters, and a
"\ufffd" (the replacement character a PDF reader writes when it can't
tell what a letter was) right before an "i" or "l" becomes an "f",
since it's almost always the lost first half of "fi", "fl" or "ffi".
That second one is a guess, which is why it only happens here, where
the button can revert it, and not on import.

It mostly works with the line breaks that are already there. It only
splits a line in two where a list clearly continues inside it: at
bullet symbols such as "•" and checkboxes such as "[X]", which don't
appear in ordinary prose, and at numbering that counts up in order
within the line ("1. ... 2. ... 3."). A single "version 2." never
forms such a run, so it's left alone. Otherwise it stays out of
guessing where a sentence ends inside a line, where "Dr.", "e.g." and
"3.14" make mistakes likely.

Line breaks don't change what gets read, since core/parser.py's
clean_transcript() flattens all whitespace first. What does change is
that list markers stop being flashed as words of their own: "1." used
to show up as a word, followed by a full sentence-end pause.

Running this on text it already produced returns that text unchanged,
so clicking Normalize on normalized text does nothing.

When split_long_paragraphs is on (a Settings toggle, off by default),
a final step breaks a wall of prose into paragraphs at sentence ends,
purely so the edit box is readable; it never changes what gets read.

toggle_normalization() and can_revert() at the bottom hold the
button's click logic, so the GUI only has to show what they decide.

No GUI dependency here (see core/ vs gui/ in the project brief)."""

import re
from dataclasses import dataclass

from core.parser import expand_ligatures, strip_timestamps

BULLET_SYMBOLS = "•●○◦▪▫■□‣►▶➢➤✓✔⁃"

HEADING_WORDS = (
    "part", "chapter", "section", "book", "unit",
    "lesson", "module", "appendix", "step",
)

_BULLET_CLASS = "[" + re.escape(BULLET_SYMBOLS) + "]"

# A bullet symbol anywhere in the text starts a new line, so
# "Fruits: • Apples • Pears" ends up as one line per item.
_INLINE_BULLET = re.compile(r"[ \t]*(" + _BULLET_CLASS + r")[ \t]*")

# A checkbox, "[X]", "[x]" or "[ ]". Like a bullet symbol it starts a new
# line wherever it appears, but only when text follows it. One with
# nothing after it but closing punctuation ("...the end [X].") is simply
# removed, since it would otherwise become an empty item.
_CHECKBOX = r"\[[ xX]\]"
_INLINE_CHECKBOX = re.compile(r"[ \t]*(" + _CHECKBOX + r")[ \t]+(?=\S)")
_TRAILING_CHECKBOX = re.compile(r"[ \t]*" + _CHECKBOX + r"(?=[.!?,;:]*[ \t]*$)", re.MULTILINE)

# A number used as a list marker inside a line: "2." or "2)", standing
# on its own between spaces. The lookarounds keep "3.14", "v2." and
# "(2)" out.
_INLINE_NUMBER = re.compile(r"(?<!\S)(\d{1,3})([.)])(?=\s|$)")

# A number right after one of these is a reference ("p. 12.", "Fig. 3.",
# "Vol. 2."), not a list marker, so it's never split off or removed.
_REFERENCE_ABBREVIATIONS = re.compile(
    r"(?i)(?:^|\s)(?:p|pp|no|nos|vol|ch|chap|fig|figs|sec|eq|art|para|pt)\.\s*$"
)

# How many times normalize_transcript() may repeat its pass. Splitting a
# numbered run happens before broken lines are joined back up, so the
# joining can occasionally line up a new run that only a second pass
# would split. Repeating until nothing changes means one click always
# does everything a second click would. Two passes are almost always
# enough; the cap only guards against looping forever.
_MAX_PASSES = 5

_SPACE_RUN = re.compile(r"[ \t]+")

# A paragraph is only broken up when it's at least this long. Below it,
# and for any paragraph of two sentences or fewer, the text is left as
# it is. Splitting closes the current paragraph once it passes this
# length and starts the next sentence in a new one, so paragraphs come
# out roughly this size and a little over.
_LONG_PARAGRAPH_CHARS = 400

# Words that end in a period without ending a sentence, so a split must
# not happen after them. Stored without the trailing dot and lowercased;
# the ones with an internal dot ("e.g", "u.s") are matched whole.
_ABBREVIATIONS = frozenset({
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc",
    "e.g", "i.e", "cf", "al", "inc", "ltd", "co", "corp", "vol", "no",
    "pp", "p", "fig", "eq", "ch", "a.m", "p.m", "u.s", "u.k", "ph.d",
})

# A candidate sentence end: one or more of . ! ? , then any closing
# quotes or brackets, then a space, then the next sentence's first
# character (an opening quote or a capital). The first group is the
# run of end marks, checked below so an ellipsis "..." isn't treated
# as an end.
_SENTENCE_END_CANDIDATE = re.compile(
    r'([.!?]+)["\'”’)\]]*\s+(?=["\'“‘([]*[A-Z])'
)
# The word sitting right before the end mark, used to spot an
# abbreviation or a single initial ("J.").
_WORD_BEFORE_END = re.compile(r'([A-Za-z][A-Za-z.]*)$')

_LOST_F = re.compile("\ufffd(?=[il])")

# Markers that count wherever they start a line. A marker may also sit
# alone on its line, with the item's text on the next one, which is
# common in text copied out of a PDF. Numbers are capped at three
# digits so a wrapped year like "1990." isn't mistaken for one.
_CLEAR_MARKER = re.compile(
    r"^(?:" + _BULLET_CLASS + r"|" + _CHECKBOX + r"|[-*–]"
    r"|\d{1,3}(?:\.\d{1,3})*[.):]"
    r"|\(\d{1,3}\)|\[\d{1,3}\])(?:\s+|$)"
)

# These two kinds are only trusted when at least two lines use the same
# kind, since a single one is easy to confuse with real text:
# "A. Smith said", "I. M. Pei", "3.14 is roughly pi".
_LETTER_MARKER = re.compile(
    r"^(?:[A-Za-z][.)]|\([A-Za-z]\)"
    r"|[ivxlcdm]+[.)]|[IVXLCDM]+[.)]|\((?:[ivxlcdm]+|[IVXLCDM]+)\))\s+(?=\S)"
)
# A section number ("1.1 Scope") is followed by a word. Requiring a
# letter after it keeps rows of numbers, such as chart axis labels
# ("0.50 0.25 0.00") copied out of a PDF, from being read as markers.
_DECIMAL_MARKER = re.compile(r"^\d{1,3}(?:\.\d{1,3})+\s+(?=[^\W\d_])")

# The heading word can be in any case; the number after it can be
# digits ("2.1"), an uppercase roman numeral ("IV") or a single capital
# letter ("Appendix A").
_HEADING = re.compile(
    r"^(?i:" + "|".join(HEADING_WORDS) + r")\s+"
    r"(?:\d+(?:\.\d+)*|[IVXLCDM]+|[A-Z])(?=$|[\s:.)\-])"
)

_NUMBER_ONLY = re.compile(r"^\d+$")

# A line ending in one of these (optionally followed by closing quotes
# or brackets) is treated as a finished sentence and never joined to
# the next line.
_SENTENCE_END = re.compile(r"[.!?…:][\"'”’)\]]*$")
_CLAUSE_END = re.compile(r"[,;]$")
_HYPHEN_BREAK = re.compile(r"[A-Za-z]-$")


def normalize_transcript(text: str, split_long_paragraphs: bool = False) -> str:
    """Return a normalized copy of text. See the module docstring for
    what changes and what's deliberately left alone. When
    split_long_paragraphs is on, a wall of prose is also broken into
    paragraphs at sentence ends."""
    result = _normalize_once(text, split_long_paragraphs)
    for _ in range(_MAX_PASSES - 1):
        again = _normalize_once(result, split_long_paragraphs)
        if again == result:
            break
        result = again
    return result


def _normalize_once(text: str, split_long_paragraphs: bool = False) -> str:
    lines = _prepare_lines(text)
    letter_markers_trusted = _count_matches(_LETTER_MARKER, lines) >= 2
    decimal_markers_trusted = _count_matches(_DECIMAL_MARKER, lines) >= 2

    paragraphs: list[list[str]] = []
    current: list[str] = []
    waiting_for_item_text = False

    def finish_paragraph() -> None:
        nonlocal current
        if current:
            paragraphs.append(current)
            current = []

    for line in lines:
        if not line:
            # A blank line ends the paragraph, unless a marker sat alone
            # on an earlier line and its text hasn't arrived yet.
            if not waiting_for_item_text:
                finish_paragraph()
            continue

        if _NUMBER_ONLY.match(line):
            continue

        if _HEADING.match(line):
            finish_paragraph()
            paragraphs.append([line])
            waiting_for_item_text = False
            continue

        marker_end = _marker_end(line, letter_markers_trusted, decimal_markers_trusted)
        if marker_end:
            finish_paragraph()
            item_text = line[marker_end:].strip()
            if item_text:
                current.append(item_text)
                waiting_for_item_text = False
            else:
                waiting_for_item_text = True
            continue

        waiting_for_item_text = False
        if current and _should_join(current[-1], line):
            current[-1] = _join(current[-1], line)
        else:
            current.append(line)

    finish_paragraph()
    if split_long_paragraphs:
        paragraphs = _break_up_long_paragraphs(paragraphs)
    return "\n\n".join("\n".join(paragraph) for paragraph in paragraphs)


def _prepare_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = expand_ligatures(text)
    text = _LOST_F.sub("f", text)
    text = _INLINE_BULLET.sub(r"\n\1 ", text)
    text = _TRAILING_CHECKBOX.sub("", text)
    text = _INLINE_CHECKBOX.sub(r"\n\1 ", text)

    lines = []
    for line in text.split("\n"):
        without_timestamps = strip_timestamps(line)
        if line.strip() and not without_timestamps.strip():
            # Nothing but a timestamp: drop the line entirely, so it
            # doesn't turn into a blank line that splits a paragraph.
            continue
        lines.extend(_split_numbered_run(without_timestamps).split("\n"))
    return [_SPACE_RUN.sub(" ", line).strip() for line in lines]


def _split_numbered_run(line: str) -> str:
    """Put a line break before each marker of a numbered list that runs
    inside the line: "Steps: 1. Mix 2. Bake" becomes "Steps:", "1. Mix"
    and "2. Bake". A run has to start at 1 and count up by one with the
    same closing mark, and has to reach at least 2, so a lone number
    with a period in ordinary prose never splits anything. "1. 2. 3."
    and "1) 2) 3)" are separate runs, and a new run can start again at
    1 later in the same line."""
    split_points = []
    for mark in ".)":
        run: list[int] = []
        expected = 1
        for match in _INLINE_NUMBER.finditer(line):
            if match.group(2) != mark:
                continue
            if _REFERENCE_ABBREVIATIONS.search(line[:match.start()]):
                continue
            number = int(match.group(1))
            if number == expected:
                run.append(match.start())
                expected += 1
            else:
                if len(run) >= 2:
                    split_points.extend(run)
                run, expected = ([match.start()], 2) if number == 1 else ([], 1)
        if len(run) >= 2:
            split_points.extend(run)

    for position in sorted(split_points, reverse=True):
        line = line[:position] + "\n" + line[position:]
    return line


def _break_up_long_paragraphs(paragraphs: list[list[str]]) -> list[list[str]]:
    """Break each long paragraph into several at sentence ends. A
    paragraph's lines are joined into one string first, so a wall pasted
    as many physical lines (the usual shape of text copied from a PDF or
    web page) is handled, not just one that happens to be a single line.
    The reflowed paragraphs replace the original only when the join is at
    least _LONG_PARAGRAPH_CHARS long and actually splits into more than
    one; anything shorter, or that stays a single paragraph (two
    sentences or fewer, or one long sentence), is passed through
    unchanged with its own lines intact."""
    result: list[list[str]] = []
    for paragraph in paragraphs:
        joined = " ".join(paragraph)
        if len(joined) >= _LONG_PARAGRAPH_CHARS:
            chunks = _split_into_paragraphs(joined)
            if len(chunks) > 1:
                result.extend([chunk] for chunk in chunks)
                continue
        result.append(paragraph)
    return result


def _split_into_paragraphs(line: str) -> list[str]:
    """Group the sentences of one long line into paragraphs, starting a
    new one each time the current paragraph passes _LONG_PARAGRAPH_CHARS.
    A line of two sentences or fewer is returned unchanged, so there's
    always something real to split."""
    sentences = _split_sentences(line)
    if len(sentences) < 3:
        return [line]
    paragraphs = []
    current = ""
    for sentence in sentences:
        current = sentence if not current else current + " " + sentence
        if len(current) >= _LONG_PARAGRAPH_CHARS:
            paragraphs.append(current)
            current = ""
    if current:
        paragraphs.append(current)
    return paragraphs


def _split_sentences(line: str) -> list[str]:
    """Split a line into sentences at real sentence ends. Joining the
    result back with single spaces reproduces the line. A candidate end
    is skipped when it's an ellipsis, or when the word before it is an
    abbreviation ("Dr.", "e.g.") or a single initial ("J."), so the
    split errs toward leaving text together rather than cutting it in
    the wrong place."""
    starts = []
    for match in _SENTENCE_END_CANDIDATE.finditer(line):
        marks = match.group(1)
        if set(marks) == {"."} and len(marks) >= 2:
            continue  # an ellipsis, not a sentence end
        word = _WORD_BEFORE_END.search(line[:match.start()])
        if word:
            token = word.group(1).lower().rstrip(".")
            if len(token) == 1 or token in _ABBREVIATIONS:
                continue
        starts.append(match.end())

    if not starts:
        return [line]
    sentences = []
    cut = 0
    for start in starts:
        sentences.append(line[cut:start].strip())
        cut = start
    sentences.append(line[cut:].strip())
    return sentences


def _count_matches(pattern: re.Pattern, lines: list[str]) -> int:
    return sum(1 for line in lines if pattern.match(line))


def _marker_end(line: str, letter_markers_trusted: bool, decimal_markers_trusted: bool) -> int:
    """Where the list marker at the start of line ends, or 0 if the
    line doesn't start with one."""
    candidates = (
        (_CLEAR_MARKER, True),
        (_LETTER_MARKER, letter_markers_trusted),
        (_DECIMAL_MARKER, decimal_markers_trusted),
    )
    for pattern, trusted in candidates:
        if trusted:
            match = pattern.match(line)
            if match:
                return match.end()
    return 0


def _starts_lowercase_or_digit(line: str) -> bool:
    stripped = line.lstrip("\"'“‘([")
    return bool(stripped) and (stripped[0].islower() or stripped[0].isdigit())


def _should_join(previous: str, line: str) -> bool:
    """Whether line continues the sentence previous left unfinished.
    A comma or semicolon at the end of previous always means it does.
    Otherwise it has to start with a lowercase letter or a digit, so a
    title line like "Introduction" isn't glued onto the text below it."""
    if _SENTENCE_END.search(previous):
        return False
    if _CLAUSE_END.search(previous):
        return True
    return _starts_lowercase_or_digit(line)


def _join(previous: str, line: str) -> str:
    # A word split across lines with a hyphen ("infor-" + "mation") is
    # joined without a space. The hyphen stays, since there's no way to
    # tell that apart from a real compound like "well-" + "known".
    if _HYPHEN_BREAK.search(previous) and _starts_lowercase_or_digit(line):
        return previous + line
    return previous + " " + line


@dataclass(frozen=True)
class NormalizationToggle:
    """The result of one click of the Normalize button: the text to
    show in the edit box, and the undo information to save with the
    transcript (see core/models.py)."""
    text: str
    pre_normalize_text: str
    normalized_text: str


def can_revert(current_text: str, pre_normalize_text: str, normalized_text: str) -> bool:
    """Whether the button should offer to revert: an original is saved
    and the edit box still holds exactly what normalizing produced. Any
    edit since then breaks the match. Whitespace at either end is
    ignored, since the edit box adds a trailing newline and saved drafts
    are stripped."""
    return bool(pre_normalize_text) and current_text.strip() == normalized_text


def toggle_normalization(
    current_text: str, pre_normalize_text: str, normalized_text: str,
    split_long_paragraphs: bool = False,
) -> NormalizationToggle:
    """What one click of the Normalize button does.

    If can_revert() says so, it brings back the saved original and
    clears the undo information. Otherwise it normalizes current_text
    and remembers the original so the next click can undo it. If
    normalizing wouldn't change anything, the text is returned as it was
    and nothing is remembered, so the button stays on Normalize.

    split_long_paragraphs is passed straight to normalize_transcript()."""
    if can_revert(current_text, pre_normalize_text, normalized_text):
        return NormalizationToggle(pre_normalize_text, "", "")

    original = current_text.strip()
    normalized = normalize_transcript(current_text, split_long_paragraphs)
    if normalized == original:
        return NormalizationToggle(original, "", "")
    return NormalizationToggle(normalized, original, normalized)