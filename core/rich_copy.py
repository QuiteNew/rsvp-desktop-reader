"""Text with bold stretches, as Word wants to find it on the clipboard.

Copying out of the edit box gives plain text, because that is all a Tk text
widget puts on the clipboard: the bold word starts are a tag, and tags do not
travel. Word can show bold, but only if the clipboard also carries a richer
format next to the plain text. This module builds that format. Like the rest of
core/, it never touches a widget or the clipboard itself.

The format is Windows' "HTML Format" (often called CF_HTML). It is an HTML
fragment with a small text header in front, and the header says where the
fragment starts and ends as byte counts from the start of the data. Those are
counts of UTF-8 bytes, not characters, so Cyrillic (2 bytes a letter) or an emoji
(4 bytes) shifts them, which is why the header is worked out from the encoded
text and tested with exactly such characters.

The input is a list of (text, is_bold) pieces in reading order, which is what the
widget can read straight off the screen. A piece may hold several lines. Only "\\n"
ends a line, as in a Tk text widget. Each line becomes one paragraph, the way
pasting plain text into Word makes one paragraph per line.

HTML squeezes white space and Word follows it, so spaces that would be lost (at
the edge of a line, or next to another space) are written as non-breaking spaces,
a tab as four of them, and an empty line keeps one so it still takes up a row.
Control characters are left out of the HTML (not out of the plain text, see
segments_text) since they have no place in it."""

import unicodedata
from itertools import groupby

# One piece of text and whether it is shown in bold.
Segment = tuple[str, bool]

_NBSP = "&nbsp;"

# Paragraphs sit tight against each other, like the lines of the draft do. Word
# would otherwise add its own space between them. A guess about how it looks in
# Word, to be judged there.
_PARAGRAPH = '<p style="margin:0">'

_START_MARKER = "<!--StartFragment-->"
_END_MARKER = "<!--EndFragment-->"
_HEAD = '<html><head><meta charset="utf-8"></head><body>'
_TAIL = "</body></html>"

_HEADER = "Version:0.9\r\nStartHTML:{:010d}\r\nEndHTML:{:010d}\r\nStartFragment:{:010d}\r\nEndFragment:{:010d}\r\n"

_ESCAPES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", "\t": _NBSP * 4}


def segments_text(segments: list[Segment]) -> str:
    """The plain text of the pieces, which goes on the clipboard next to the HTML
    so that Notepad and everything else that only knows plain text still gets it."""
    return "".join(text for text, _ in segments)


def cf_html(segments: list[Segment]) -> bytes:
    """The pieces as Windows' HTML clipboard format, encoded as UTF-8. The caller
    puts these bytes on the clipboard (with a closing zero byte) as "HTML Format"."""
    body = "".join(_paragraph(line) for line in _lines(segments))
    document = _HEAD + _START_MARKER + body + _END_MARKER + _TAIL
    # The header has the same length whatever the numbers are (they are padded to
    # ten digits), so it can be measured first and filled in afterwards.
    header_size = len(_HEADER.format(0, 0, 0, 0).encode("ascii"))
    start_fragment = header_size + len((_HEAD + _START_MARKER).encode("utf-8"))
    end_fragment = start_fragment + len(body.encode("utf-8"))
    end_html = header_size + len(document.encode("utf-8"))
    header = _HEADER.format(header_size, end_html, start_fragment, end_fragment)
    return (header + document).encode("utf-8")


def _lines(segments: list[Segment]) -> list[list[Segment]]:
    """The pieces cut into lines, each a list of pieces with no line break in them.
    Always at least one line, so an empty text is one empty paragraph."""
    lines: list[list[Segment]] = [[]]
    for text, bold in segments:
        for number, part in enumerate(_without_controls(text).split("\n")):
            if number:
                lines.append([])
            if part:
                lines[-1].append((part, bold))
    return lines


def _without_controls(text: str) -> str:
    """text without control characters, except the line break and the tab. That
    takes out the carriage return of a Windows line ending as well."""
    return "".join(
        char for char in text
        if char in "\n\t" or unicodedata.category(char) != "Cc"
    )


def _paragraph(pieces: list[Segment]) -> str:
    """One line as a paragraph, with a <b> around each bold stretch."""
    text = "".join(piece for piece, _ in pieces)
    if not text:
        return f"{_PARAGRAPH}{_NBSP}</p>"
    bold_flags = [bold for piece, bold in pieces for _ in piece]
    written = [_ESCAPES.get(char, char) for char in text]
    _protect_spaces(text, written)
    runs = []
    for bold, group in groupby(zip(written, bold_flags), key=lambda pair: pair[1]):
        run = "".join(char for char, _ in group)
        runs.append(f"<b>{run}</b>" if bold else run)
    return f"{_PARAGRAPH}{''.join(runs)}</p>"


def _protect_spaces(text: str, written: list[str]) -> None:
    """Turn the spaces HTML would drop into non-breaking ones, in `written`, which
    holds what to write for each character of `text`. A lone space between two
    other characters is the only one that is safe as it is."""
    last = len(text) - 1
    for index, char in enumerate(text):
        if char != " ":
            continue
        alone = 0 < index < last and text[index - 1] not in " \t" and text[index + 1] not in " \t"
        if not alone:
            written[index] = _NBSP