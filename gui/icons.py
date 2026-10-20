"""Small icon-drawing helpers.

Icons here are drawn as vector images via Pillow, rather than relying
on Unicode symbol glyphs (⏻, ⏸, etc.). Glyph coverage for those
characters varies unpredictably across fonts and operating systems,
which is exactly why the power icon showed up as an empty box. Drawing
them ourselves guarantees the same appearance on any machine.
"""

from PIL import Image, ImageColor, ImageDraw
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


# The bold word starts button draws rows of "words" as plain bars, with no page
# around them, so it can't be taken for the Normalize or Revert page icons.
# Each tuple is one row, and each number is a word's width as a share of the
# glyph. The rows end ragged, like a paragraph does.
_BOLD_STARTS_ROWS = ((0.36, 0.40), (0.44, 0.32), (0.30, 0.24))
_BOLD_STARTS_ROW_Y = (0.24, 0.50, 0.76)

# How strong the "plain" part of a word is, out of 255. With the button off,
# every word is drawn at this strength. With it on, the front half of each word
# is drawn at full strength instead. It is a lower alpha rather than a second
# colour so it still looks right on hover, when the button colour changes.
_BOLD_STARTS_SOFT_ALPHA = 130


def _draw_bold_starts_glyph(size: int, color, bold_starts: bool) -> Image.Image:
    """Rows of "words" as rounded bars. Off, every word is the same soft tone.
    On, the front half of each word is full strength, the way the start of a
    word looks in the text itself.

    `color` is an RGBA tuple. The on glyph is the off glyph with the word
    starts brightened, so switching it on only ever adds ink."""
    supersample = 4  # draw large, then downscale: gives smooth, anti-aliased edges
    s = size * supersample
    bar = s * 0.13
    gap = s * 0.09
    red, green, blue, alpha = color
    soft = (red, green, blue, round(alpha * _BOLD_STARTS_SOFT_ALPHA / 255))

    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for widths, y in zip(_BOLD_STARTS_ROWS, _BOLD_STARTS_ROW_Y):
        top, bottom = s * y - bar / 2, s * y + bar / 2
        x = s * 0.08
        for width in widths:
            end = x + s * width
            # Drawing with an alpha replaces the pixels instead of blending
            # over them, so the bright front covers the soft bar under it.
            draw.rounded_rectangle([x, top, end, bottom], radius=bar * 0.4, fill=soft)
            if bold_starts:
                draw.rounded_rectangle([x, top, x + (end - x) / 2, bottom], radius=bar * 0.4, fill=color)
            x = end + gap

    return image.resize((size, size), Image.LANCZOS)


def bold_starts_icon(is_on: bool, size: int = 24) -> ctk.CTkImage:
    """The bold word starts button's icon. is_on picks the glyph that shows the
    word starts brightened. The button colour is the same either way, so the
    icon is the only thing that says whether the look is on."""
    glyph = _draw_bold_starts_glyph(size * _PAGE_ICON_SOURCE_SCALE, PAGE_ICON_COLOR, is_on)
    return ctk.CTkImage(light_image=glyph, dark_image=glyph, size=(size, size))


def _draw_center_glyph(size: int, color) -> Image.Image:
    """A centring target: a ring with a dot at its middle and a short tick
    running out from each side, the familiar "locate" mark.

    Proportions keep the ticks reaching almost to the edge of the square,
    so the glyph fills a small button without loose space around it."""
    supersample = 4  # draw large, then downscale: gives smooth, anti-aliased edges
    s = size * supersample
    line_width = max(2, round(s * 0.09))
    centre = s / 2

    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    ring = s * 0.27
    draw.ellipse([centre - ring, centre - ring, centre + ring, centre + ring], outline=color, width=line_width)

    dot = s * 0.10
    draw.ellipse([centre - dot, centre - dot, centre + dot, centre + dot], fill=color)

    tick_start = ring - line_width / 2
    tick_end = s * 0.48
    draw.line([(centre, centre - tick_start), (centre, centre - tick_end)], fill=color, width=line_width)
    draw.line([(centre, centre + tick_start), (centre, centre + tick_end)], fill=color, width=line_width)
    draw.line([(centre - tick_start, centre), (centre - tick_end, centre)], fill=color, width=line_width)
    draw.line([(centre + tick_start, centre), (centre + tick_end, centre)], fill=color, width=line_width)

    return image.resize((size, size), Image.LANCZOS)


def center_icon(size: int = 12, color: str = "#FFFFFF") -> ctk.CTkImage:
    """The reader's "centre" button icon, drawn in the given #RRGGBB colour
    (the caller passes its theme's ink colour, so it reads on the button)."""
    rgba = (*ImageColor.getrgb(color)[:3], 255)
    glyph = _draw_center_glyph(size * _PAGE_ICON_SOURCE_SCALE, rgba)
    return ctk.CTkImage(light_image=glyph, dark_image=glyph, size=(size, size))

def _draw_clear_glyph(size: int, color) -> Image.Image:
    """A small "X": two diagonals with rounded ends, the usual clear mark for a
    search box. Kept well inside its square so a 10px glyph has breathing room
    in a 20px button."""
    supersample = 4  # draw large, then downscale: gives smooth, anti-aliased edges
    s = size * supersample
    line_width = max(2, round(s * 0.14))

    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    near, far = s * 0.27, s * 0.73
    draw.line([(near, near), (far, far)], fill=color, width=line_width)
    draw.line([(near, far), (far, near)], fill=color, width=line_width)

    # PIL's lines have square ends; a small disc on each end rounds them.
    cap = line_width / 2
    for x, y in ((near, near), (far, far), (near, far), (far, near)):
        draw.ellipse([x - cap, y - cap, x + cap, y + cap], fill=color)

    return image.resize((size, size), Image.LANCZOS)


def clear_icon(size: int = 10, color: str = "#888888") -> ctk.CTkImage:
    """The search box's clear button icon, drawn in the given #RRGGBB colour
    (the caller passes a grey that suits its theme)."""
    rgba = (*ImageColor.getrgb(color)[:3], 255)
    glyph = _draw_clear_glyph(size * _PAGE_ICON_SOURCE_SCALE, rgba)
    return ctk.CTkImage(light_image=glyph, dark_image=glyph, size=(size, size))



def _draw_description_glyph(size: int, color) -> Image.Image:
    """A few short lines of "text", the usual mark for a block of writing.
    Used on the Settings search's "also search descriptions" toggle. The last
    line is shorter so it reads as a paragraph rather than a menu."""
    supersample = 4  # draw large, then downscale: gives smooth, anti-aliased edges
    s = size * supersample
    line_width = max(2, round(s * 0.085))

    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    rows = ((0.16, 0.84, 0.26), (0.16, 0.84, 0.50), (0.16, 0.60, 0.74))  # x0, x1, y
    cap = line_width / 2
    for x0, x1, y in rows:
        draw.line([(s * x0, s * y), (s * x1, s * y)], fill=color, width=line_width)
        # PIL's lines have square ends; a small disc on each end rounds them.
        for x in (x0, x1):
            draw.ellipse([s * x - cap, s * y - cap, s * x + cap, s * y + cap], fill=color)

    return image.resize((size, size), Image.LANCZOS)


def description_icon(size: int = 16, color: str = "#000000") -> ctk.CTkImage:
    """The Settings search's "search descriptions" toggle icon, drawn in the
    given #RRGGBB colour (the caller passes its theme's ink colour)."""
    rgba = (*ImageColor.getrgb(color)[:3], 255)
    glyph = _draw_description_glyph(size * _PAGE_ICON_SOURCE_SCALE, rgba)
    return ctk.CTkImage(light_image=glyph, dark_image=glyph, size=(size, size))


def _draw_info_glyph(size: int, color) -> Image.Image:
    """A lowercase "i": a round dot above a short stem, the usual mark for
    an about/info button. Just the letter, not a circle around it; the
    button itself supplies the round look via its own corner_radius, the
    same way clear_icon's X does not draw a circle either."""
    supersample = 4  # draw large, then downscale: gives smooth, anti-aliased edges
    s = size * supersample
    line_width = max(2, round(s * 0.14))
    centre_x = s / 2

    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    dot_radius = line_width * 0.62
    dot_y = s * 0.26
    draw.ellipse(
        [centre_x - dot_radius, dot_y - dot_radius, centre_x + dot_radius, dot_y + dot_radius],
        fill=color,
    )

    stem_top = s * 0.44
    stem_bottom = s * 0.78
    draw.line([(centre_x, stem_top), (centre_x, stem_bottom)], fill=color, width=line_width)
    # Rounds the stem's lower end to match the dot's curve; the top end sits
    # flush under the dot, so only the bottom needs a cap.
    cap = line_width / 2
    draw.ellipse([centre_x - cap, stem_bottom - cap, centre_x + cap, stem_bottom + cap], fill=color)

    return image.resize((size, size), Image.LANCZOS)


def info_icon(size: int = 14, color: str = "#888888") -> ctk.CTkImage:
    """The Settings window's About button icon, drawn in the given #RRGGBB
    colour (the caller passes a grey that suits its theme)."""
    rgba = (*ImageColor.getrgb(color)[:3], 255)
    glyph = _draw_info_glyph(size * _PAGE_ICON_SOURCE_SCALE, rgba)
    return ctk.CTkImage(light_image=glyph, dark_image=glyph, size=(size, size))