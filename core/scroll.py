"""Pure geometry for the reader's horizontal scrollbar.

The reader centres each flash on the ORP letter at the middle of the reading
row. When a flash is wider than the row, even after the font has been shrunk to
fit, part of it falls off one or both edges. A horizontal scrollbar lets the
reader pan left or right to bring the hidden part into view: a pan offset is
added to the centre anchor, sliding the whole flash sideways.

These helpers convert between that pan offset, in pixels, and the (first, last)
fraction pair a Tk-style scrollbar uses to size and place its thumb. They are
pure arithmetic with no widgets, so the panning logic can be tested without a
display.

Terms:
- viewport: the visible reading width, in pixels.
- overflow_left / overflow_right: how far the content reaches past the viewport
  on each side, in pixels (0 when nothing spills that way).
- pan: the offset added to the centre anchor, in pixels. Positive moves the
  flash right (revealing content that spilled off the left); negative moves it
  left (revealing the right). Its valid range is
  [-overflow_right, +overflow_left].
"""


def pan_range(overflow_left: float, overflow_right: float) -> tuple[float, float]:
    """The (minimum, maximum) pan offset. Pan can move the flash right by up to
    the left overflow (to reveal it) and left by up to the right overflow, so
    the range runs from -overflow_right to +overflow_left."""
    return -overflow_right, overflow_left


def clamp_pan(pan: float, overflow_left: float, overflow_right: float) -> float:
    """Pin a pan offset inside its valid range, so panning can never push the
    flash further than there is hidden content to reveal."""
    low, high = pan_range(overflow_left, overflow_right)
    return max(low, min(high, pan))


def scrollbar_fractions(viewport: float, overflow_left: float, overflow_right: float, pan: float) -> tuple[float, float]:
    """The (first, last) thumb fractions for a given pan, in the Tk scrollbar
    convention (0 at the far left of the track, 1 at the far right). The virtual
    content is the viewport plus whatever overflows each side; the thumb is the
    viewport's share of that. With no overflow the thumb fills the whole track,
    (0.0, 1.0), which is how a scrollbar shows "nothing to scroll"."""
    span = overflow_left + overflow_right
    if viewport <= 0 or span <= 0:
        return 0.0, 1.0
    virtual = viewport + span
    pan = clamp_pan(pan, overflow_left, overflow_right)
    x = overflow_left - pan  # distance from the left end of the virtual strip
    first = x / virtual
    last = (x + viewport) / virtual
    return first, last


def pan_from_fraction(first: float, viewport: float, overflow_left: float, overflow_right: float) -> float:
    """The pan offset for a scrollbar dragged so the left edge of its thumb sits
    at `first` (0..1). The inverse of scrollbar_fractions, clamped to the valid
    pan range so a drag past either end simply stops at it."""
    span = overflow_left + overflow_right
    if span <= 0:
        return 0.0
    virtual = viewport + span
    x = first * virtual
    pan = overflow_left - x
    return clamp_pan(pan, overflow_left, overflow_right)