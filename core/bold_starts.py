"""Bold word starts for the edit box: which letters at the front of each word to
draw in bold, like [we]ll-[kno]wn.

This module only answers "which characters". Drawing them is the GUI's job, and
the text itself is never changed. Everything here is plain text and arithmetic,
so it can be tested without a window.

bold_ranges() takes a piece of text and returns (start, end) pairs, counted in
characters (Python string positions), sorted and never overlapping. A word never
runs across a line break, so the text can be handed over a whole or one line at a
time and the answer is the same. Handing over one line at a time is how the edit
box can re-bold just the lines somebody typed in.

What counts as a word:

- A run of letters from the alphabets that put spaces between words: Latin,
  Cyrillic and Greek. Letters of other scripts (Chinese, Japanese, Arabic,
  Hebrew and so on) are left alone, because bolding the start of a whole sentence
  means nothing, and bolding part of a joined word is wrong.
- An apostrophe between two letters stays inside the word (don't, O'Brien, a
  curly one too, and the modifier apostrophe Ukrainian writes in m'yaso). One at
  the start or the end (dogs') is just punctuation.
- A soft hyphen or a joiner inside a word is invisible, so it stays inside the
  word without being counted. Text pasted from a PDF is full of soft hyphens. A
  zero-width space is a break opportunity, so it ends the word like a space.
- Accents written as a separate combining mark stay with their letter, and a
  bold stretch never ends between a letter and its mark.
- Everything else ends a word: spaces, digits, punctuation, every kind of hyphen
  and dash, slashes and underscores. So well-known has two words and each gets
  its own bold start.
- A word with a digit right against it (3rd, H2O, mp3, 1990's) is an identifier
  or a number, not something to read, so it is left alone. So are web addresses
  and email addresses.

How much of a word is bold comes from fixation_length(), which grows more slowly
than the word does so a long word doesn't end up half bold. In a long word the
cut is then nudged a letter or two to a place that sits between a vowel and a
consonant, so it avoids landing in the middle of a pair like "ea" or a cluster
like "rn". That is a rule of thumb, not hyphenation: with no dictionary there is
no way to know where a syllable really ends."""

import re
import unicodedata
from functools import lru_cache

# The most letters fixation_length() makes bold. The nudge below can move a cut
# by up to MAX_NUDGE letters, so a very long word can end up with a bit more or
# less than this.
MAX_BOLD_LETTERS = 6

# Words with fewer letters than this keep the cut fixation_length() gives them.
# Short words are bold by half, and a nudge there would only make them lighter.
NUDGE_MIN_LETTERS = 7
MAX_NUDGE = 2

# The apostrophes that can sit inside a word: the straight one, the curly one
# and the modifier letter apostrophe.
_APOSTROPHES = "'\u2019\u02bc"

# Characters that are invisible and sit inside a word without breaking it: the
# soft hyphen, the two joiners and the word joiner.
_INVISIBLE_GLUE = "\u00ad\u200c\u200d\u2060"

# Letters of the scripts we bold, as (first, last) code point ranges. A letter
# outside these ends the word. The ranges include a few characters that are not
# letters (the Greek question mark, say), which _kind() weeds out by category.
_SCRIPT_RANGES = (
    # Latin, with the Latin-1 and extended blocks and the f-ligatures.
    (0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x024F), (0x1E00, 0x1EFF),
    (0x2C60, 0x2C7F), (0xA720, 0xA7FF), (0xFB00, 0xFB06),
    # Greek, with the polytonic block.
    (0x0370, 0x03FF), (0x1F00, 0x1FFF),
    # Cyrillic, with the extended blocks.
    (0x0400, 0x052F), (0x1C80, 0x1C8F), (0xA640, 0xA69F),
)
_CYRILLIC_RANGE = (0x0400, 0x052F)

# Web and email addresses are skipped whole. A bare domain with no http://, no
# www. and no @ (example.com) is not recognised: it is rare in a transcript, and
# it would take a list of every ending to tell it from "end.Then".
_LEAVE_ALONE = re.compile(
    r"https?://\S+|www\.\S+"
    r"|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
)

# The Cyrillic soft and hard sign. They belong to the letter in front of them, so
# a cut is never made right before one.
_SIGNS = "\u044c\u044a"

# The vowels, lower case and without accents. The Latin and Greek ones are
# matched after stripping an accent (see _is_vowel). A Cyrillic letter is
# matched as it is, because taking an accent off "\u0439" would turn a consonant
# into the vowel "\u0438".
_VOWELS = frozenset(
    "aeiouy\u00e6\u0153\u00f8\u0131\u0259"
    "\u0430\u0435\u0451\u0438\u043e\u0443\u044b\u044d\u044e\u044f\u0456\u0457\u0454\u045d"
    "\u03b1\u03b5\u03b7\u03b9\u03bf\u03c5\u03c9"
)


def fixation_length(letter_count: int) -> int:
    """How many letters at the start of a word with this many letters are bold.

    Half of a short word, rounded up, then slowly less: one letter for one or
    two, two for three or four, three for five or six, four for seven to ten,
    five for eleven to fourteen and six from fifteen on. A word of two letters
    or more is never bold all the way through.

    The curve is meant to be tuned by eye. Change it here and nothing else needs
    to know."""
    if letter_count <= 6:
        return (letter_count + 1) // 2
    return min(MAX_BOLD_LETTERS, 3 + (letter_count - 3) // 4)


def bold_ranges(text: str) -> list[tuple[int, int]]:
    """The (start, end) pairs of the stretches of `text` to draw in bold. See the
    top of this module for what counts as a word and how long the stretch is."""
    skips = [match.span() for match in _LEAVE_ALONE.finditer(text)]
    ranges = []
    size = len(text)
    i = 0
    next_skip = 0
    while i < size:
        # Step over a web or email address whole.
        while next_skip < len(skips) and skips[next_skip][1] <= i:
            next_skip += 1
        if next_skip < len(skips) and skips[next_skip][0] <= i:
            i = skips[next_skip][1]
            continue
        if _kind(text[i]) != "L":
            i += 1
            continue

        # A word starts here. Take its letters, each with the combining marks
        # that follow it, and let apostrophes and invisible glue ride along. One
        # that ends up on the end of the word (dogs') is harmless, because the
        # bold stretch is cut from the letters alone.
        start = i
        letters = []
        ends = []
        while i < size:
            kind = _kind(text[i])
            if kind == "L":
                letters.append(text[i])
                i += 1
                while i < size and _kind(text[i]) == "M":
                    i += 1
                ends.append(i)
            elif kind in ("A", "I"):
                i += 1
            else:
                break

        if _touches_digit(text, start, i):
            continue
        ranges.append((start, ends[_cut_after(letters) - 1]))
    return ranges


@lru_cache(maxsize=4096)
def _kind(char: str) -> str:
    """What a character is to the word finder: "L" a letter we bold, "M" a
    combining mark, "A" an apostrophe, "I" invisible glue inside a word, and "O"
    for everything else, which ends a word."""
    if char in _APOSTROPHES:
        return "A"
    if char in _INVISIBLE_GLUE:
        return "I"
    category = unicodedata.category(char)
    if category[0] == "M":
        return "M"
    if category[0] == "L":
        code = ord(char)
        if any(first <= code <= last for first, last in _SCRIPT_RANGES):
            return "L"
    return "O"


def _touches_digit(text: str, start: int, end: int) -> bool:
    """Whether the word at text[start:end] has a digit right against it. An
    apostrophe in front is looked through, so the s of 1990's counts too."""
    before = text[start - 1] if start > 0 else ""
    if before in _APOSTROPHES and start > 1:
        before = text[start - 2]
    after = text[end] if end < len(text) else ""
    return before.isnumeric() or after.isnumeric()


def _cut_after(letters: list[str]) -> int:
    """How many of a word's letters are bold. The length from fixation_length(),
    moved a little in a long word to a better place to cut."""
    count = len(letters)
    keep = fixation_length(count)
    if count < NUDGE_MIN_LETTERS:
        return keep
    for distance in range(MAX_NUDGE + 1):
        # The shorter cut goes first, so a tie keeps the bold part lighter.
        for cut in (keep - distance, keep + distance):
            if 1 <= cut < count and _clean_cut(letters[cut - 1], letters[cut]):
                return cut
    return keep


def _clean_cut(before: str, after: str) -> bool:
    """Whether cutting between these two letters sits between a vowel and a
    consonant, and not right in front of a Cyrillic sign."""
    if after.lower() in _SIGNS:
        return False
    return _is_vowel(before) != _is_vowel(after)


@lru_cache(maxsize=4096)
def _is_vowel(letter: str) -> bool:
    letter = letter.lower()[0]
    if letter not in _VOWELS and not _CYRILLIC_RANGE[0] <= ord(letter) <= _CYRILLIC_RANGE[1]:
        # An accented Latin or Greek letter counts as the plain one.
        letter = unicodedata.normalize("NFD", letter)[0]
    return letter in _VOWELS