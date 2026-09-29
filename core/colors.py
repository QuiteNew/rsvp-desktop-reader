"""Small, pure colour helpers, kept out of gui/theme.py so they can be unit
tested without importing the GUI. gui/theme.py holds the palette; this holds
the maths."""


def blend_colors(color_a: str, color_b: str, ratio: float) -> str:
    """Linear blend between two hex colours, returned as "#RRGGBB". ratio is
    how far to move from color_a toward color_b: 0.0 is color_a, 1.0 is
    color_b, clamped to that range. Accepts "#RGB" or "#RRGGBB", with or
    without the leading #. Used for the peripheral context ribbon, which
    dims the reading font toward the reading background so the surrounding
    words recede."""
    ratio = max(0.0, min(1.0, ratio))
    ar, ag, ab = _channels(color_a)
    br, bg, bb = _channels(color_b)
    r = round(ar + (br - ar) * ratio)
    g = round(ag + (bg - ag) * ratio)
    b = round(ab + (bb - ab) * ratio)
    return f"#{r:02X}{g:02X}{b:02X}"


def _channels(value: str) -> tuple[int, int, int]:
    """Split a hex colour into its (r, g, b) integer channels. Expands the
    "#RGB" short form to "#RRGGBB" first, and tolerates a missing #."""
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)