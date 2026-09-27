import re

_TIMESTAMP_PATTERN = re.compile(r'\[?\(?\d{1,2}:\d{2}(:\d{2})?\)?\]?')

# Any whitespace except a line break: spaces, tabs, and the odd form
# feed or non-breaking space that PDFs and Word files leave behind.
_SPACE_RUN_WITHIN_LINE = re.compile(r'[^\S\n]+')
_BLANK_LINE_RUN = re.compile(r'\n{3,}')

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


def clean_transcript(raw_text: str) -> str:
    """Strip timestamps from raw transcript text and normalize whitespace."""
    text = _TIMESTAMP_PATTERN.sub('', raw_text)
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
    trimmed, runs of blank lines are cut down to one, and combined
    letters such as "ﬁ" are expanded."""
    text = raw_text.replace('\r\n', '\n').replace('\r', '\n')
    text = expand_ligatures(text)
    text = _TIMESTAMP_PATTERN.sub('', text)
    lines = [_SPACE_RUN_WITHIN_LINE.sub(' ', line).strip() for line in text.split('\n')]
    text = _BLANK_LINE_RUN.sub('\n\n', '\n'.join(lines))
    return text.strip()


if __name__ == "__main__":
    sample = """
    [00:00:01] Welcome to the show.
    (1:23) Today we're talking about
    00:02:45 rapid serial visual presentation.
    """
    print(clean_transcript(sample))