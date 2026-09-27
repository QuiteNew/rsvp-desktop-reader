"""Tidies up a transcript's layout on request, for the edit view's
Normalize button.

Removes list markers (numbering and bullets) and puts each list item in
its own paragraph, keeps headings such as "Chapter 3" on their own
line, drops lines that are only a number (usually PDF page numbers),
and rejoins lines that were broken in the middle of a sentence.

It also repairs two kinds of damage that text pulled out of a PDF
often has. Combined letters such as "ﬁ" become plain letters, and a
"\ufffd" (the replacement character a PDF reader writes when it can't
tell what a letter was) right before an "i" or "l" becomes an "f",
since it's almost always the lost first half of "fi", "fl" or "ffi".
That second one is a guess, which is why it only happens here, where
the button can revert it, and not on import.

It only works with the line breaks that are already there. It never
splits a line in two, except at bullet symbols such as "•", which don't
appear in ordinary prose. That keeps it out of guessing where a
sentence ends inside a line, where "Dr.", "e.g." and "3.14" make
mistakes likely.

Line breaks don't change what gets read, since core/parser.py's
clean_transcript() flattens all whitespace first. What does change is
that list markers stop being flashed as words of their own: "1." used
to show up as a word, followed by a full sentence-end pause.

Running this on text it already produced returns that text unchanged,
so clicking Normalize on normalized text does nothing.

toggle_normalization() and can_revert() at the bottom hold the
button's click logic, so the GUI only has to show what they decide.

No GUI dependency here (see core/ vs gui/ in the project brief)."""

import re
from dataclasses import dataclass

from core.parser import expand_ligatures

BULLET_SYMBOLS = "•●○◦▪▫■□‣►▶➢➤✓✔⁃"

HEADING_WORDS = (
    "part", "chapter", "section", "book", "unit",
    "lesson", "module", "appendix", "step",
)

_BULLET_CLASS = "[" + re.escape(BULLET_SYMBOLS) + "]"

# A bullet symbol anywhere in the text starts a new line, so
# "Fruits: • Apples • Pears" ends up as one line per item.
_INLINE_BULLET = re.compile(r"[ \t]*(" + _BULLET_CLASS + r")[ \t]*")

_SPACE_RUN = re.compile(r"[ \t]+")

_LOST_F = re.compile("\ufffd(?=[il])")

# Markers that count wherever they start a line. A marker may also sit
# alone on its line, with the item's text on the next one, which is
# common in text copied out of a PDF. Numbers are capped at three
# digits so a wrapped year like "1990." isn't mistaken for one.
_CLEAR_MARKER = re.compile(
    r"^(?:" + _BULLET_CLASS + r"|[-*–]"
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


def normalize_transcript(text: str) -> str:
    """Return a normalized copy of text. See the module docstring for
    what changes and what's deliberately left alone."""
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
    return "\n\n".join("\n".join(paragraph) for paragraph in paragraphs)


def _prepare_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = expand_ligatures(text)
    text = _LOST_F.sub("f", text)
    text = _INLINE_BULLET.sub(r"\n\1 ", text)
    return [_SPACE_RUN.sub(" ", line).strip() for line in text.split("\n")]


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


def toggle_normalization(current_text: str, pre_normalize_text: str, normalized_text: str) -> NormalizationToggle:
    """What one click of the Normalize button does.

    If can_revert() says so, it brings back the saved original and
    clears the undo information. Otherwise it normalizes current_text
    and remembers the original so the next click can undo it. If
    normalizing wouldn't change anything, the text is returned as it was
    and nothing is remembered, so the button stays on Normalize."""
    if can_revert(current_text, pre_normalize_text, normalized_text):
        return NormalizationToggle(pre_normalize_text, "", "")

    original = current_text.strip()
    normalized = normalize_transcript(current_text)
    if normalized == original:
        return NormalizationToggle(original, "", "")
    return NormalizationToggle(normalized, original, normalized)