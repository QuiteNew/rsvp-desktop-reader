"""Draws the app icon at any size, for the Microsoft Store.

The icon in assets/icons is a 256 pixel picture, which is too small for the
Store's 300 x 300 tile and gets soft when it's stretched. This script draws the
same icon from its shapes instead, so it comes out sharp at any size.

The numbers below were measured from assets/icons/app.png: its size, where each
shape sits and the three colours. Everything on the 256 pixel canvas is
described by them, and the SVG and the pictures both come from them, so they
can't drift apart. tests/test_store_icons.py draws the icon at 256 and holds it
against app.png, so a number that moves shows up there.

Run it from the project root:

    python store/make_icons.py [folder]

It writes app-icon.svg, app-icon-1024.png and store-tile-300.png into the
folder, which is build/store-assets if none is given. The app itself never
imports this file, and the build doesn't copy it."""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

# The canvas the numbers below are measured on. Everything is drawn on it and
# then scaled to whatever size is asked for.
CANVAS = 256

COCOA = "#3B2E27"  # the dark rounded square, and the pupil
CREAM = "#F6EFE3"  # the eye and the two outer bars
AMBER = "#D98A3D"  # the middle bar, the one that marks the focus letter

CORNER_RADIUS = 56.37  # of the rounded square, 22% of the canvas

# The eye is the overlap of two circles, so it has a point at each side. It
# gets its width and height here, and the circle's size follows from them.
EYE_CENTRE = (85.75, 128.0)
EYE_HALF_WIDTH = 44.95
EYE_HALF_HEIGHT = 27.0
PUPIL_RADIUS = 19.35

# Three upright bars with round ends, all the same size and on the same line.
BAR_WIDTH = 19.25
BAR_HEIGHT = 76.9
BAR_CENTRES_X = (167.13, 200.37, 233.68)
BAR_CENTRE_Y = 128.0
BAR_COLOURS = (CREAM, AMBER, CREAM)

# The sizes the Store listing asks for, by file name.
OUTPUTS = {
    "app-icon-1024.png": 1024,
    "store-tile-300.png": 300,
}


def eye_circle_radius() -> float:
    """The radius of each of the two circles whose overlap makes the eye."""
    return (EYE_HALF_WIDTH ** 2 + EYE_HALF_HEIGHT ** 2) / (2 * EYE_HALF_HEIGHT)


def svg_text() -> str:
    """The icon as an SVG, from the same numbers the pictures are drawn with."""
    radius = eye_circle_radius()
    left = EYE_CENTRE[0] - EYE_HALF_WIDTH
    right = EYE_CENTRE[0] + EYE_HALF_WIDTH
    y = EYE_CENTRE[1]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS}" height="{CANVAS}" viewBox="0 0 {CANVAS} {CANVAS}">',
        f'<rect width="{CANVAS}" height="{CANVAS}" rx="{CORNER_RADIUS}" fill="{COCOA}"/>',
        f'<path d="M{left:.3f} {y:.3f} A{radius:.3f} {radius:.3f} 0 0 1 {right:.3f} {y:.3f} '
        f'A{radius:.3f} {radius:.3f} 0 0 1 {left:.3f} {y:.3f} Z" fill="{CREAM}"/>',
        f'<circle cx="{EYE_CENTRE[0]}" cy="{y}" r="{PUPIL_RADIUS}" fill="{COCOA}"/>',
    ]
    for centre, colour in zip(BAR_CENTRES_X, BAR_COLOURS):
        parts.append(
            f'<rect x="{centre - BAR_WIDTH / 2:.3f}" y="{BAR_CENTRE_Y - BAR_HEIGHT / 2:.3f}" '
            f'width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="{BAR_WIDTH / 2:.3f}" fill="{colour}"/>'
        )
    parts.append("</svg>")
    return "".join(parts) + "\n"


def _supersample_for(size: int) -> int:
    """How many times bigger to draw than the size asked for. Drawing larger
    and shrinking is what smooths the edges, so small icons get more of it."""
    return min(16, max(4, 4096 // size))


def render(size: int) -> Image.Image:
    """The icon at size x size pixels, as an RGBA picture with see-through
    corners."""
    scale = _supersample_for(size) * size / CANVAS
    big = round(CANVAS * scale)

    def px(value: float) -> float:
        return value * scale

    def far(value: float) -> float:
        # Pillow counts the right and bottom edge of a shape as part of it, so
        # those two are pulled in by one drawing pixel. Without this every
        # shape comes out a hair too big.
        return value * scale - 1

    picture = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    draw.rounded_rectangle((0, 0, far(CANVAS), far(CANVAS)), radius=px(CORNER_RADIUS), fill=COCOA)

    # The eye: where two big circles overlap, one centred above the line of the
    # eye and one below it, so the overlap comes to a point at each side.
    radius = eye_circle_radius()
    offset = radius - EYE_HALF_HEIGHT
    cx, cy = EYE_CENTRE
    lens = None
    for direction in (-1, 1):
        mask = Image.new("L", (big, big), 0)
        centre_y = cy + direction * offset
        ImageDraw.Draw(mask).ellipse(
            (px(cx - radius), px(centre_y - radius), far(cx + radius), far(centre_y + radius)), fill=255
        )
        lens = mask if lens is None else ImageChops.darker(lens, mask)
    picture.paste(Image.new("RGBA", (big, big), CREAM), (0, 0), lens)

    draw = ImageDraw.Draw(picture)
    draw.ellipse(
        (px(cx - PUPIL_RADIUS), px(cy - PUPIL_RADIUS), far(cx + PUPIL_RADIUS), far(cy + PUPIL_RADIUS)), fill=COCOA
    )
    for centre, colour in zip(BAR_CENTRES_X, BAR_COLOURS):
        draw.rounded_rectangle(
            (
                px(centre - BAR_WIDTH / 2),
                px(BAR_CENTRE_Y - BAR_HEIGHT / 2),
                far(centre + BAR_WIDTH / 2),
                far(BAR_CENTRE_Y + BAR_HEIGHT / 2),
            ),
            radius=px(BAR_WIDTH / 2),
            fill=colour,
        )

    # Pillow shrinks see-through pictures with the colour and the see-through
    # part kept apart, so the corners don't pick up a dark edge.
    return picture.resize((size, size), Image.BOX)


def write_all(folder: Path) -> list[Path]:
    """Writes the SVG and the Store pictures into folder, and returns the files."""
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    svg = folder / "app-icon.svg"
    svg.write_text(svg_text(), encoding="utf-8")
    written.append(svg)
    for name, size in OUTPUTS.items():
        path = folder / name
        render(size).save(path)
        written.append(path)
    return written


def main(argv: list[str]) -> int:
    folder = Path(argv[1]) if len(argv) > 1 else Path("build") / "store-assets"
    for path in write_all(folder):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))