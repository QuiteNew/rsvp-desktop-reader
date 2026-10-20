"""Where the bold word starts go in a Tk text widget.

core/bold_starts.py says which characters of a text are bold, counted the way
Python counts. A Tk text widget names a place as "line.column" instead, with the
first line being line 1, so this module turns one into the other. It also works
out which lines of a text were touched by an edit, so the edit box can bold
just those again. Like the rest of core/, it never touches a widget.

A column in Tk is not always a Python position. Tk 8.6, the version that comes
with Python 3.13 on Windows, counts a character outside the Basic Multilingual
Plane (an emoji, for one) as two columns. Tk 9 counts it as one. The widget
asks Tk which it is and passes the answer in as astral_width, so a bold stretch
after an emoji still lands on the right letters."""

import re

from core.bold_starts import bold_ranges

# Every character outside the Basic Multilingual Plane.
_ASTRAL = re.compile(f"[{chr(0x10000)}-{chr(0x10FFFF)}]")


def tk_spans(text: str, astral_width: int = 1, first_line: int = 1) -> list[tuple[int, int, int]]:
    """The bold stretches of `text` as (line, start_column, end_column), in the
    order they appear. The end is exclusive, like a Tk "line.column" range end.

    `text` is split on "\\n" only, which is all Tk treats as a line break (not
    the other separators Python's splitlines() knows). first_line numbers its
    first line, for a piece cut out of the middle of a longer text. astral_width
    is how many columns Tk gives one character outside the Basic Multilingual
    Plane: 2 for Tk 8.6, 1 for Tk 9."""
    spans = []
    for number, line in enumerate(text.split("\n"), first_line):
        ranges = bold_ranges(line)
        if astral_width != 1 and ranges and _ASTRAL.search(line):
            ranges = [(_to_tk_column(line, start, astral_width), _to_tk_column(line, end, astral_width))
                      for start, end in ranges]
        spans.extend((number, start, end) for start, end in ranges)
    return spans


def _to_tk_column(line: str, offset: int, astral_width: int) -> int:
    """The Tk column of the character at `offset` in `line`: each astral
    character before it takes up astral_width columns instead of one."""
    return offset + (astral_width - 1) * len(_ASTRAL.findall(line, 0, offset))


def changed_lines(old_lines: list[str], new_lines: list[str]) -> tuple[int, int]:
    """Which lines of `new_lines` differ from `old_lines`, as (first, end) with
    end not included, so new_lines[first:end] are the ones to bold again.

    It trusts that a single edit (typing, a paste, a delete, an undo) changes one
    block of lines in a row. The lines that match at the start and the end are
    skipped, and what is left in the middle is the block. Two edits made since
    the last look are covered too, as one larger block. When nothing changed the
    block is empty and sits at the end, (len(new_lines), len(new_lines))."""
    shortest = min(len(old_lines), len(new_lines))
    first = 0
    while first < shortest and old_lines[first] == new_lines[first]:
        first += 1
    old_end, new_end = len(old_lines), len(new_lines)
    while old_end > first and new_end > first and old_lines[old_end - 1] == new_lines[new_end - 1]:
        old_end -= 1
        new_end -= 1
    return first, new_end