"""Cutting a line of text down to the room it has, with an ellipsis at the end.

Kept out of the GUI so it can be tested without a window. It never measures
anything itself: the caller passes in a measure function that says how wide a
piece of text is, which in the app asks the label that will show it."""

from typing import Callable

ELLIPSIS = "…"


def fit_text(text: str, max_width: int, measure: Callable[[str], int], ellipsis: str = ELLIPSIS) -> str:
    """Return text unchanged when it fits in max_width, otherwise the longest
    start of it that still fits once the ellipsis is added.

    Spaces left at the cut are dropped, so the ellipsis sits against the last
    word instead of floating after a gap. When not even the ellipsis fits, the
    ellipsis alone is returned, which is the least the caller can show.

    measure(text) is the width of that text in the same unit as max_width.
    It is expected to grow as text gets longer, which holds for any real font."""
    if measure(text) <= max_width:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if measure(text[:middle].rstrip() + ellipsis) <= max_width:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + ellipsis