"""Where the main window goes at launch.

The app remembers the window's size, where it was on the screen and whether it
was maximized when the app was last closed, and puts it back the same way at
the next launch. This file holds the rules for that, with no Tk in it, so they
can be tested without a screen. gui/app.py does the measuring and the moving.

Two kinds of number meet here, so it helps to say which is which. The width
and height are in the app's own units, the ones the Layout tab shows, with the
display scaling taken out (that is how CustomTkinter's geometry() works). The x
and y are plain screen pixels, because CustomTkinter passes a position through
as it is. So a saved size still means the same after the scaling is changed,
and so does a saved position."""

import re

# A point this far below the window's top edge is on its title bar.
TITLE_BAR_DEPTH = 16
# The outer two of the three points checked are this far in from the sides.
TITLE_BAR_INSET = 40

_GEOMETRY = re.compile(r"(\d+)x(\d+)([+-])(-?\d+)([+-])(-?\d+)")


def parse_geometry(text: str) -> tuple[int, int, int | None, int | None] | None:
    """Splits a Tk geometry string like "1000x650+120+80" into width, height,
    x and y. A window on a screen left of or above the main one has a negative
    position, which Tk writes as "+-1500".

    Tk puts a "-" in place of the "+" when a position is counted from the right
    or bottom edge of the screen. The app never places its window that way, so
    for one of those only the size is kept and the position comes back as None,
    rather than being read the wrong way round. Anything that isn't a geometry
    string at all gives None."""
    match = _GEOMETRY.fullmatch(text.strip())
    if match is None:
        return None
    width, height = int(match.group(1)), int(match.group(2))
    if match.group(3) == "-" or match.group(5) == "-":
        return width, height, None, None
    return width, height, int(match.group(4)), int(match.group(6))


def geometry_string(width: int, height: int, x: int | None, y: int | None) -> str:
    """The other way round: "1000x650+120+80", or just "1000x650" when there is
    no position, which leaves the placing to the system. Tk reads "+-1500" as a
    position left of the main screen, so a negative needs nothing special."""
    if x is None or y is None:
        return f"{width}x{height}"
    return f"{width}x{height}+{x}+{y}"


def title_bar_points(x: int, y: int, width_px: int) -> list[tuple[int, int]]:
    """Three points along the window's title bar: near its left end, in the
    middle and near its right end. width_px is the window's width in screen
    pixels."""
    inset = min(TITLE_BAR_INSET, width_px // 2)
    row = y + TITLE_BAR_DEPTH
    return [(x + inset, row), (x + width_px // 2, row), (x + width_px - inset, row)]


def position_is_usable(x: int, y: int, width_px: int, on_screen) -> bool:
    """Whether a saved position can be used as it is. It can when at least one
    of title_bar_points() is on a screen, because then the window can still be
    grabbed and moved. on_screen(px, py) says whether a point is on any screen.

    A position fails when the screen it was on has gone, say a second monitor
    that has since been unplugged, or the resolution has gone down. The window
    then opens where the system puts it, not somewhere nobody can see it. This
    also catches the odd spot Windows parks a minimized window at, far off to
    the top left, if that is ever what got saved."""
    return any(on_screen(px, py) for px, py in title_bar_points(x, y, width_px))


def clamp(value: int, value_range: tuple[int, int]) -> int:
    """value, moved inside value_range if it falls outside it."""
    low, high = value_range
    return max(low, min(high, value))
