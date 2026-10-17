"""Letter spacing for the reader's flashing word.

Tk has no letter spacing setting, so the gap is built out of space characters:
a few thin spaces go between the letters of a word. Which characters to use, and
how many, depends on how wide each one really is in the font on screen, and that
differs from font to font (and from machine to machine, since most fonts have no
glyph of their own for these characters and Windows borrows one from another
font). So the GUI measures each character once, in em, and hands those widths
to build_plan() here, which picks the combination that lands closest to the
gap the chosen level asks for.

Everything in this module is plain text and arithmetic. It never measures
anything and never touches a widget, so it can be tested without a window.

The gap is part of the text that gets drawn, not a layout offset. The reader's
labels are placed around the focus letter, and a label's width counts spaces at
its edges, so a gap added to the end of the before text and the start of the
after text lands exactly where it should without any change to the placement
code. The focus letter itself is never touched."""

from dataclasses import dataclass

LEVEL_NAMES = ("Off", "Small", "Medium", "Large")

# The extra room between two neighbouring letters at each level, as a fraction
# of the font size. Medium is close to the 2.5 pt on 14 pt text (about 0.18 em)
# used in one published study of children with dyslexia. That study was about
# running text, not single flashed words, so the levels are a starting point to
# adjust by eye, not a proven setting.
LEVEL_GAP_EM = (0.0, 0.10, 0.18, 0.30)
MAX_LEVEL = len(LEVEL_GAP_EM) - 1

PLAIN_SPACE = " "

# The space characters a letter gap can be made of. They are written with chr()
# so this file stays plain ASCII: the characters themselves are invisible.
HAIR_SPACE = chr(0x200A)
SIX_PER_EM_SPACE = chr(0x2006)
THIN_SPACE = chr(0x2009)
PUNCTUATION_SPACE = chr(0x2008)

# The order here only decides which of two equally good combinations is found
# first.
GAP_UNIT_CHARS = (PUNCTUATION_SPACE, SIX_PER_EM_SPACE, THIN_SPACE, HAIR_SPACE)

# A character narrower than this is treated as unusable (a zero-width or missing
# glyph would never get the gap anywhere).
MIN_UNIT_EM = 0.02

# The most characters one gap may be made of. Keeps the drawn text short and
# the search small.
MAX_GAP_CHARS = 6

# Between words of a chunk the gap has to stay clearly wider than the gap
# between letters, or the words run together. A word gap is therefore at least
# this many times the letter gap. In a font whose plain space is already wide
# (OpenDyslexic's is about 0.85 em) nothing extra is needed.
WORD_GAP_RATIO = 2.0


@dataclass(frozen=True)
class SpacingPlan:
    """What to put between letters and between words at one level, for one
    font. letter_gap and word_gap are the actual strings. The two *_em values are
    how wide those strings measure, in em, kept for tests and for showing what
    was picked; they are 0.0 when nothing was measured."""
    level: int
    letter_gap: str
    word_gap: str
    letter_gap_em: float
    word_gap_em: float

    @property
    def is_off(self) -> bool:
        """True when the plan changes nothing: no letter gap and a plain space
        between words."""
        return not self.letter_gap and self.word_gap == PLAIN_SPACE


# What the reader uses before any measuring has happened: no spacing at all.
NO_SPACING = SpacingPlan(0, "", PLAIN_SPACE, 0.0, 0.0)


def clamp_level(level) -> int:
    """A level the rest of this module can trust. Anything that isn't a whole
    number (including True and False) gives 0, which is "Off", and a number
    outside the levels is pulled to the nearest one."""
    if isinstance(level, bool) or not isinstance(level, int):
        return 0
    return max(0, min(MAX_LEVEL, level))


def gap_width_em(gap: str, unit_widths_em: dict) -> float:
    """How wide a gap string is, in em, from the measured widths. A character
    with no measured width counts as nothing."""
    return sum(unit_widths_em.get(char, 0.0) for char in gap)


def choose_gap(target_em: float, unit_widths_em: dict, max_chars: int = MAX_GAP_CHARS) -> str:
    """The string of gap characters whose total width is closest to target_em.

    unit_widths_em maps a character to its measured width in em. Only the
    characters in GAP_UNIT_CHARS are used, and only those wide enough to be
    real (MIN_UNIT_EM). An empty string is a valid answer: when the target is
    smaller than half of the narrowest character, no gap is the closest one.
    When two combinations are equally close the one with fewer characters wins,
    and after that the first found, so the result is the same every time."""
    if target_em <= 0:
        return ""
    units = [(char, unit_widths_em[char]) for char in GAP_UNIT_CHARS
             if unit_widths_em.get(char, 0.0) >= MIN_UNIT_EM]
    if not units:
        return ""

    best_counts = (0,) * len(units)
    best_key = (round(target_em, 9), 0)  # the empty gap: all of the target is missing

    def search(index: int, counts: list, width: float, used: int) -> None:
        nonlocal best_counts, best_key
        if index == len(units):
            key = (round(abs(target_em - width), 9), used)
            if key < best_key:
                best_key = key
                best_counts = tuple(counts)
            return
        unit_width = units[index][1]
        for count in range(max_chars - used + 1):
            counts.append(count)
            search(index + 1, counts, width + count * unit_width, used + count)
            counts.pop()

    search(0, [], 0.0, 0)
    return "".join(char * count for (char, _), count in zip(units, best_counts))


def build_plan(level, unit_widths_em: dict) -> SpacingPlan:
    """Work out the letter gap and word gap for a level.

    unit_widths_em holds the measured width, in em, of PLAIN_SPACE and of each
    character in GAP_UNIT_CHARS in the font that is on screen. Level 0, and a
    font where none of the gap characters measure as usable, give a plan that
    changes nothing."""
    level = clamp_level(level)
    space_em = unit_widths_em.get(PLAIN_SPACE, 0.0)
    if level == 0:
        return SpacingPlan(0, "", PLAIN_SPACE, 0.0, space_em)

    letter_gap = choose_gap(LEVEL_GAP_EM[level], unit_widths_em)
    if not letter_gap:
        return SpacingPlan(level, "", PLAIN_SPACE, 0.0, space_em)
    letter_em = gap_width_em(letter_gap, unit_widths_em)

    # The plain space stays as the base of the word gap. Anything the word gap
    # still needs to reach WORD_GAP_RATIO times the letter gap is added on top.
    extra = choose_gap(WORD_GAP_RATIO * letter_em - space_em, unit_widths_em)
    word_gap = PLAIN_SPACE + extra
    return SpacingPlan(level, letter_gap, word_gap, letter_em, space_em + gap_width_em(extra, unit_widths_em))


def space_text(text: str, plan: SpacingPlan) -> str:
    """Put the plan's gaps into a piece of text: the letter gap between every two
    neighbouring characters of a word, and the word gap in place of each single
    plain space between words. Nothing is added at either end of the text."""
    if plan.is_off:
        return text
    words = text.split(PLAIN_SPACE)
    return plan.word_gap.join(plan.letter_gap.join(word) for word in words)


def space_chunk(before: str, focus: str, after: str, plan: SpacingPlan) -> tuple[str, str, str]:
    """Space a flash's (before, focus, after) triple, as core.reader's
    assemble_chunk_text() builds it. The focus letter is returned untouched.

    The room between the focus letter and its neighbours is added to the edge of
    the neighbouring text: a letter gap after the before text and in front of the
    after text. Where the after text starts with a plain space (a one-letter first
    word followed by more words in a chunk) the word gap already provides that
    room, so no letter gap is added there. An empty before or after text gets
    nothing, since there is no neighbour on that side."""
    if plan.is_off:
        return before, focus, after
    spaced_before = space_text(before, plan)
    spaced_after = space_text(after, plan)
    if before:
        spaced_before += plan.letter_gap
    if after and not after.startswith(PLAIN_SPACE):
        spaced_after = plan.letter_gap + spaced_after
    return spaced_before, focus, spaced_after