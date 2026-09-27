import re

# Timestamps, in the order they're checked: subtitle timing lines (so a
# whole "00:00:01,000 --> 00:00:04,000" goes, not just its two ends),
# anything in square brackets or parentheses ("[00:01:23]", "(1:23)"),
# and full hour:minute:second ones anywhere ("00:02:45"). A bare
# two-part time only counts when it's alone on its line, the way
# YouTube transcripts copy ("0:05" above each caption), so "we met at
# 10:30" keeps its time. Shared with core/normalizer.py, so reading,
# importing and the Normalize button all agree on what a timestamp is.
TIMESTAMP_PATTERN = re.compile(
    r"\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?\s*-->\s*\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?"
    r"|[\[(]\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?[\])]"
    r"|(?<![\d:])\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?(?![\d:])"
    r"|^[ \t]*\d{1,2}:\d{2}[ \t\r]*$",
    re.MULTILINE,
)

# Any whitespace except a line break: spaces, tabs, and the odd form
# feed or non-breaking space that PDFs and Word files leave behind.
_SPACE_RUN_WITHIN_LINE = re.compile(r'[^\S\n]+')
_BLANK_LINE_RUN = re.compile(r'\n{3,}')

# Removing a timestamp from the middle of a line strands the punctuation
# that framed it: the commas in "(9:00, 9:15, done)", the space in
# "later , we", an empty "()". These tidy that up. They run only on text
# where a timestamp was actually found (see strip_timestamps), so an
# ordinary ":)" or a spaced-out "..." in text with no timestamps is
# never touched. Only spaces and tabs, never a line break, so they can't
# pull two lines together.
_REPEATED_SEPARATOR = re.compile(r'([,;])(?:[ \t]*[,;])+')
_SEPARATOR_AFTER_OPEN = re.compile(r'([(\[])[ \t]*[,;:][ \t]*')
_SEPARATOR_BEFORE_CLOSE = re.compile(r'[ \t]*[,;:][ \t]*([)\]])')
_EMPTY_BRACKETS = re.compile(r'[ \t]*\([ \t]*\)|[ \t]*\[[ \t]*\]')
_SPACE_BEFORE_PUNCT = re.compile(r'[ \t]+([,.;:!?)\]])')

# Single characters that PDFs use to draw two or three letters as one
# shape. They look right on screen but break search and make words
# count as shorter than they are, so they're swapped for plain letters.
# A fixed list rather than Python's general unicodedata NFKC cleanup,
# which would also turn "½" into "1⁄2", "²" into "2" and "…" into "...".
LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "st",
    "\ufb06": "st",
}
_LIGATURE_TABLE = str.maketrans(LIGATURES)


def strip_timestamps(text: str) -> str:
    """Remove timestamps (see TIMESTAMP_PATTERN) and tidy the punctuation
    and spaces they leave behind, so a removed timestamp doesn't strand a
    comma, an empty bracket or a floating space. Text with no timestamp
    is returned untouched, so ordinary punctuation elsewhere is never
    altered."""
    if not TIMESTAMP_PATTERN.search(text):
        return text
    text = TIMESTAMP_PATTERN.sub('', text)
    text = _REPEATED_SEPARATOR.sub(r'\1', text)
    text = _SEPARATOR_AFTER_OPEN.sub(r'\1', text)
    text = _SEPARATOR_BEFORE_CLOSE.sub(r'\1', text)
    text = _EMPTY_BRACKETS.sub('', text)
    text = _SPACE_BEFORE_PUNCT.sub(r'\1', text)
    return text


def clean_transcript(raw_text: str) -> str:
    """Strip timestamps from raw transcript text and normalize whitespace."""
    text = strip_timestamps(raw_text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def expand_ligatures(text: str) -> str:
    """Replace combined letters such as "ﬁ" with the plain letters they
    stand for. See LIGATURES above."""
    return text.translate(_LIGATURE_TABLE)


def clean_transcript_keep_lines(raw_text: str) -> str:
    """Like clean_transcript(), but keeps line breaks. Used for imported
    files, so the text lands in the edit view with its lines intact and
    the Normalize button (core/normalizer.py) has structure to work
    with. Spaces inside each line are still collapsed, each line is
    trimmed, runs of blank lines are cut down to one, combined letters
    such as "ﬁ" are expanded, and a line that held only a timestamp is
    dropped rather than left behind as a blank line."""
    text = raw_text.replace('\r\n', '\n').replace('\r', '\n')
    text = expand_ligatures(text)
    lines = []
    for line in text.split('\n'):
        without_timestamps = strip_timestamps(line)
        if line.strip() and not without_timestamps.strip():
            # Nothing but a timestamp: drop the line entirely, so it
            # doesn't turn into a blank line that splits a paragraph.
            continue
        lines.append(_SPACE_RUN_WITHIN_LINE.sub(' ', without_timestamps).strip())
    text = _BLANK_LINE_RUN.sub('\n\n', '\n'.join(lines))
    return text.strip()


if __name__ == "__main__":
    sample = """
    [00:00:01] Welcome to the show.
    (1:23) Today we're talking about
    00:02:45 rapid serial visual presentation.
    """
    print(clean_transcript(sample))