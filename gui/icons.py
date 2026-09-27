"""Small icon-drawing helpers.

Icons here are drawn as vector images via Pillow, rather than relying
on Unicode symbol glyphs (⏻, ⏸, etc.). Glyph coverage for those
characters varies unpredictably across fonts and operating systems,
which is exactly why the power icon showed up as an empty box. Drawing
them ourselves guarantees the same appearance on any machine.
"""

from PIL import Image, ImageDraw
import customtkinter as ctk

LIGHT_MODE_COLOR = (32, 32, 32, 255)     # dark icon, legible on a light button
DARK_MODE_COLOR = (230, 230, 230, 255)   # light icon, legible on a dark button


def _draw_power_glyph(size: int, color) -> Image.Image:
    """The classic power symbol: a circle broken at the top, with a
    vertical tick through the gap, the same icon used on PC power buttons.
    """
    supersample = 4  # draw large, then downscale: gives smooth, anti-aliased edges
    canvas_size = size * supersample
    padding = canvas_size * 0.18
    line_width = max(2, canvas_size // 14)

    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    bbox = [padding, padding, canvas_size - padding, canvas_size - padding]
    # PIL angles increase clockwise starting from 3 o'clock; 270° is straight up.
    # Leaving a ~70-degree gap centered on the top, for the tick to sit in.
    draw.arc(bbox, start=305, end=595, fill=color, width=line_width)

    center_x = canvas_size // 2
    draw.line(
        [(center_x, padding * 0.3), (center_x, canvas_size // 2)],
        fill=color, width=line_width,
    )

    return image.resize((size, size), Image.LANCZOS)


def power_icon(size: int = 18) -> ctk.CTkImage:
    """A power icon that automatically matches light/dark appearance mode."""
    light_version = _draw_power_glyph(size, LIGHT_MODE_COLOR)
    dark_version = _draw_power_glyph(size, DARK_MODE_COLOR)
    return ctk.CTkImage(light_image=light_version, dark_image=dark_version, size=(size, size))


# White in both appearance modes: unlike the power icon, which sits on a
# grey "glass" button, the page icons sit on a blue CTkButton, where
# white reads well in light and dark mode alike.
PAGE_ICON_COLOR = (255, 255, 255, 255)

# CTkImage resizes its source image to the on-screen size times the
# display scaling (175% on a high-resolution laptop turns a 24px icon
# into 42px). A source drawn at exactly 24px gets stretched up and looks
# soft, so the page icons are drawn this many times larger and only
# ever scaled down, which stays sharp up to 400% scaling.
_PAGE_ICON_SOURCE_SCALE = 4


def _draw_page_glyph(size: int, color, with_check: bool) -> Image.Image:
    """A page: a rounded rectangle with three lines of "text" on it.

    With with_check, the page sits left of centre and a checkmark sits
    over its lower right corner, inside a small cut-out circle. The
    cut-out is made transparent rather than filled with the button's
    colour, so it still looks right on hover, when the button colour
    changes.

    Proportions are chosen so the glyph reaches close to the edges of
    its square, leaving no loose space inside the button."""
    supersample = 4  # draw large, then downscale: gives smooth, anti-aliased edges
    s = size * supersample
    line_width = max(2, round(s * 0.065))

    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    left, right = (0.06, 0.64) if with_check else (0.18, 0.82)
    page = [s * left, s * 0.04, s * right, s * 0.96]
    draw.rounded_rectangle(page, radius=s * 0.08, outline=color, width=line_width)

    text_left = page[0] + s * 0.13
    text_right = page[2] - s * 0.13
    for y in (0.30, 0.50, 0.70):
        draw.line([(text_left, s * y), (text_right, s * y)], fill=color, width=line_width)

    if with_check:
        cx, cy, r = s * 0.70, s * 0.70, s * 0.28
        # Drawing with a fully transparent fill replaces the pixels
        # instead of blending over them, which is what clears the cut-out.
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 0))
        draw.line(
            [(cx - r * 0.60, cy + r * 0.02), (cx - r * 0.15, cy + r * 0.48), (cx + r * 0.68, cy - r * 0.50)],
            fill=color, width=max(2, round(s * 0.085)), joint="curve",
        )

    return image.resize((size, size), Image.LANCZOS)


def normalize_icon(size: int = 24) -> ctk.CTkImage:
    """The Normalize button's icon: a page with a checkmark."""
    glyph = _draw_page_glyph(size * _PAGE_ICON_SOURCE_SCALE, PAGE_ICON_COLOR, with_check=True)
    return ctk.CTkImage(light_image=glyph, dark_image=glyph, size=(size, size))


def revert_icon(size: int = 24) -> ctk.CTkImage:
    """The Normalize button's icon while it offers to revert: a plain page."""
    glyph = _draw_page_glyph(size * _PAGE_ICON_SOURCE_SCALE, PAGE_ICON_COLOR, with_check=False)
    return ctk.CTkImage(light_image=glyph, dark_image=glyph, size=(size, size))