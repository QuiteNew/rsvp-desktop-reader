"""Small icon-drawing helpers.

Icons here are drawn as vector images via Pillow, rather than relying on
Unicode symbol glyphs (⏻, ⏸, etc.) — glyph coverage for those characters
varies unpredictably across fonts and operating systems, which is exactly
why the power icon showed up as an empty box. Drawing them ourselves
guarantees the same appearance on any machine.
"""

from PIL import Image, ImageDraw
import customtkinter as ctk

LIGHT_MODE_COLOR = (32, 32, 32, 255)     # dark icon, legible on a light button
DARK_MODE_COLOR = (230, 230, 230, 255)   # light icon, legible on a dark button


def _draw_power_glyph(size: int, color) -> Image.Image:
    """The classic power symbol: a circle broken at the top, with a
    vertical tick through the gap — the same icon used on PC power buttons.
    """
    supersample = 4  # draw large, then downscale — gives smooth, anti-aliased edges
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