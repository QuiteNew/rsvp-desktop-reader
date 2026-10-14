"""Tests for the drawn icons in gui/icons.py. Only the new "i" glyph for the
Settings About button so far. The drawing helpers return plain Pillow images,
so these checks need no window: they look at the pixels the glyph produces."""

from gui.icons import _draw_info_glyph, info_icon

# Big enough that the dot, the gap and the stem are each several pixels tall,
# so the checks below are about the shape and not about rounding at 14px.
GLYPH_SIZE = 56
INK = (200, 40, 40)


def _glyph(size: int = GLYPH_SIZE, color=INK):
    return _draw_info_glyph(size, (*color, 255))


def _ink_runs_down_the_middle(image, threshold: int = 128) -> list[tuple[int, int]]:
    """The (first_row, last_row) of each separate stretch of ink along the
    middle column, top to bottom."""
    middle = image.width // 2
    runs = []
    start = None
    for y in range(image.height):
        inked = image.getpixel((middle, y))[3] >= threshold
        if inked and start is None:
            start = y
        elif not inked and start is not None:
            runs.append((start, y - 1))
            start = None
    if start is not None:
        runs.append((start, image.height - 1))
    return runs


def test_glyph_is_a_square_rgba_image_of_the_requested_size():
    image = _glyph()
    assert image.mode == "RGBA"
    assert image.size == (GLYPH_SIZE, GLYPH_SIZE)


def test_the_four_corners_stay_transparent():
    image = _glyph()
    last = GLYPH_SIZE - 1
    for corner in ((0, 0), (last, 0), (0, last), (last, last)):
        assert image.getpixel(corner)[3] == 0


def test_it_reads_as_a_dot_over_a_stem_with_a_gap_between():
    runs = _ink_runs_down_the_middle(_glyph())
    assert len(runs) == 2
    (dot_top, dot_bottom), (stem_top, stem_bottom) = runs
    assert dot_bottom < stem_top
    # The stem is the longer of the two, the way a lowercase i is.
    assert (stem_bottom - stem_top) > (dot_bottom - dot_top)


def test_the_ink_sits_inside_the_square_with_room_to_spare():
    box = _glyph().getchannel("A").point(lambda a: 255 if a > 0 else 0).getbbox()
    left, top, right, bottom = box
    assert left >= 1 and top >= 1
    assert right <= GLYPH_SIZE - 1 and bottom <= GLYPH_SIZE - 1


def test_the_glyph_fills_enough_of_its_square_to_read_at_small_sizes():
    box = _glyph().getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    _, top, _, bottom = box
    assert (bottom - top) >= GLYPH_SIZE * 0.5


def test_the_ink_is_centred_left_to_right():
    alpha = _glyph().getchannel("A")
    total = 0
    weighted = 0
    for y in range(alpha.height):
        for x in range(alpha.width):
            a = alpha.getpixel((x, y))
            total += a
            weighted += a * x
    centre_of_ink = weighted / total
    centre_of_square = (GLYPH_SIZE - 1) / 2
    assert abs(centre_of_ink - centre_of_square) < 0.5


def test_solid_pixels_use_the_colour_that_was_asked_for():
    image = _glyph()
    solid = [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)
             if image.getpixel((x, y))[3] == 255]
    assert solid, "expected some fully opaque pixels"
    # Shrinking the drawing nudges the colour of a few pixels along the edge,
    # even where they are fully opaque, so this checks the average colour of
    # the solid pixels rather than demanding each one be exact.
    for channel, wanted in enumerate(INK):
        average = sum(pixel[channel] for pixel in solid) / len(solid)
        assert abs(average - wanted) <= 8


def test_a_different_colour_gives_a_different_glyph():
    # A point on the stem, well inside the ink.
    point = (GLYPH_SIZE // 2, GLYPH_SIZE // 2 + 8)
    red = _glyph(color=(200, 40, 40))
    blue = _glyph(color=(40, 40, 200))
    assert red.getpixel(point)[:3] != blue.getpixel(point)[:3]


def test_info_icon_is_sized_for_the_screen_not_the_drawing():
    icon = info_icon(14, "#336699")
    assert icon.cget("size") == (14, 14)
    # The source image is drawn larger and only ever scaled down, so it stays
    # sharp on high-DPI displays (see _PAGE_ICON_SOURCE_SCALE in gui/icons.py).
    assert icon.cget("light_image").size[0] > 14
    assert icon.cget("light_image").size == icon.cget("dark_image").size


def test_info_icon_is_14px_when_no_size_is_given():
    assert info_icon().cget("size") == (14, 14)