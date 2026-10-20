"""Where the bold word starts go in a Tk text widget.

core/bold_starts.py says which characters of a text are bold, counted the way
Python counts. A Tk text widget names a place as "line.column" instead, with the
first line being line 1, so this module turns one into the other. Like the rest
of core/, it never touches a widget.

A column in Tk is not always a Python position. Tk 8.6, the version that comes
with Python 3.13 on Windows, counts a character outside the Basic Multilingual
Plane (an emoji, for one) as two columns. Tk 9 counts it as one. The widget
asks Tk which it is and passes the answer in as astral_width, so a bold stretch
after an emoji still lands on the right letters.

A very long line is the other thing to know about. Tk takes time that grows with
the square of the number of tags in one line: a line of 1,000 words takes about
0.1 seconds to bold, 3,000 words about 0.8 seconds and 12,000 words about 8
seconds, however the tags are added. A pasted transcript that is one long
paragraph would freeze the window, so lines over MAX_BOLD_LINE are left plain."""

import re

from core.bold_starts import bold_ranges

# Every character outside the Basic Multilingual Plane.
_ASTRAL = re.compile(f"[{chr(0x10000)}-{chr(0x10FFFF)}]")

# The longest line, in characters, that gets bold word starts. About 650 words,
# which Tk bolds in roughly 30 milliseconds, so typing in such a line still
# feels immediate. Ordinary paragraphs are far below it.
MAX_BOLD_LINE = 4000


def tk_spans(text: str, astral_width: int = 1, first_line: int = 1,
             max_line: int | None = None) -> list[tuple[int, int, int]]:
    """The bold stretches of `text` as (line, start_column, end_column), in the
    order they appear. The end is exclusive, like a Tk "line.column" range end.

    `text` is split on "\\n" only, which is all Tk treats as a line break (not
    the other separators Python's splitlines() knows). first_line numbers its
    first line, for a piece cut out of the middle of a longer text. astral_width
    is how many columns Tk gives one character outside the Basic Multilingual
    Plane: 2 for Tk 8.6, 1 for Tk 9. A line longer than max_line characters (as
    Python counts them) has no stretches at all; None means no limit."""
    spans = []
    for number, line in enumerate(text.split("\n"), first_line):
        if max_line is not None and len(line) > max_line:
            continue
        ranges = bold_ranges(line)
        if astral_width != 1 and ranges and _ASTRAL.search(line):
            ranges = [(_to_tk_column(line, start, astral_width), _to_tk_column(line, end, astral_width))
                      for start, end in ranges]
        spans.extend((number, start, end) for start, end in ranges)
    return spans


def has_long_line(text: str, max_line: int = MAX_BOLD_LINE) -> bool:
    """Whether any line of `text` is longer than max_line characters, so that
    tk_spans() given the same limit leaves it plain."""
    return any(len(line) > max_line for line in text.split("\n"))


def _to_tk_column(line: str, offset: int, astral_width: int) -> int:
    """The Tk column of the character at `offset` in `line`: each astral
    character before it takes up astral_width columns instead of one."""
    return offset + (astral_width - 1) * len(_ASTRAL.findall(line, 0, offset))