"""Tests for the drawn icons in gui/icons.py: the "i" glyph for the Settings
About button, and the glyph for the bold word starts button. The drawing helpers
return plain Pillow images, so these checks need no window: they look at the
pixels the glyph produces."""

import pytest

from gui.icons import (
    _draw_bold_starts_glyph, _draw_info_glyph, bold_starts_icon, info_icon,
    normalize_icon, revert_icon,
)

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


# ---- Bold word starts glyph ----

# Big enough that every word, the gaps between words and the bright front of a
# word are several pixels wide.
BOLD_SIZE = 96
SOFT = (110, 150)   # the range the soft tone has to fall in (130 out of 255)
FULL = 250          # at least this, to count as full strength


def _bold_glyph(bold_starts: bool, size: int = BOLD_SIZE, color=INK):
    return _draw_bold_starts_glyph(size, (*color, 255), bold_starts)


def _alpha(image, x: int, y: int) -> int:
    return image.getpixel((x, y))[3]


def _runs(values, threshold: int = 64) -> list[tuple[int, int]]:
    """The (first, last) index of each stretch of values at or over the threshold."""
    runs = []
    start = None
    for index, value in enumerate(values):
        if value >= threshold and start is None:
            start = index
        elif value < threshold and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(values) - 1))
    return runs


def _row_centres(image) -> list[int]:
    """The middle y of each row of words, found down a column that is inside
    the first word of every row."""
    x = int(image.width * 0.16)
    runs = _runs([_alpha(image, x, y) for y in range(image.height)])
    return [(first + last) // 2 for first, last in runs]


def _words_along(image, y: int) -> list[tuple[int, int]]:
    return _runs([_alpha(image, x, y) for x in range(image.width)])


def _front_and_tail(word: tuple[int, int]) -> tuple[int, int]:
    """One x inside the front half of a word and one inside its back half, both
    clear of the rounded ends."""
    first, last = word
    length = last - first
    return first + round(length * 0.2), last - round(length * 0.15)


@pytest.mark.parametrize("bold_starts", [False, True])
def test_bold_glyph_is_a_square_rgba_image_of_the_requested_size(bold_starts):
    image = _bold_glyph(bold_starts)
    assert image.mode == "RGBA"
    assert image.size == (BOLD_SIZE, BOLD_SIZE)

@pytest.mark.parametrize("bold_starts", [False, True])
def test_bold_glyph_keeps_its_four_corners_transparent(bold_starts):
    image = _bold_glyph(bold_starts)
    last = BOLD_SIZE - 1
    for corner in ((0, 0), (last, 0), (0, last), (last, last)):
        assert _alpha(image, *corner) == 0

@pytest.mark.parametrize("bold_starts", [False, True])
def test_bold_glyph_is_three_rows_of_two_words(bold_starts):
    image = _bold_glyph(bold_starts)
    centres = _row_centres(image)
    assert len(centres) == 3
    for y in centres:
        assert len(_words_along(image, y)) == 2

@pytest.mark.parametrize("bold_starts", [False, True])
def test_bold_glyph_rows_are_evenly_spaced_and_centred_on_the_square(bold_starts):
    first, second, third = _row_centres(_bold_glyph(bold_starts))
    assert abs((second - first) - (third - second)) <= 1
    assert abs(second - (BOLD_SIZE - 1) / 2) <= 1

@pytest.mark.parametrize("bold_starts", [False, True])
def test_bold_glyph_ink_sits_inside_the_square_with_room_to_spare(bold_starts):
    box = _bold_glyph(bold_starts).getchannel("A").point(lambda a: 255 if a > 0 else 0).getbbox()
    left, top, right, bottom = box
    assert left >= 1 and top >= 1
    assert right <= BOLD_SIZE - 1 and bottom <= BOLD_SIZE - 1

@pytest.mark.parametrize("bold_starts", [False, True])
def test_bold_glyph_fills_enough_of_its_square_to_read_at_small_sizes(bold_starts):
    box = _bold_glyph(bold_starts).getchannel("A").point(lambda a: 255 if a >= 64 else 0).getbbox()
    left, top, right, bottom = box
    assert (right - left) >= BOLD_SIZE * 0.8
    assert (bottom - top) >= BOLD_SIZE * 0.5

def test_with_it_off_every_word_is_the_same_soft_tone():
    image = _bold_glyph(False)
    assert image.getchannel("A").getextrema()[1] <= SOFT[1]
    for y in _row_centres(image):
        for word in _words_along(image, y):
            for x in _front_and_tail(word):
                assert SOFT[0] <= _alpha(image, x, y) <= SOFT[1]

def test_with_it_on_the_front_of_every_word_is_full_strength_and_the_rest_soft():
    image = _bold_glyph(True)
    for y in _row_centres(image):
        for word in _words_along(image, y):
            front, tail = _front_and_tail(word)
            assert _alpha(image, front, y) >= FULL
            assert SOFT[0] <= _alpha(image, tail, y) <= SOFT[1]

def test_with_it_on_the_front_covers_about_half_of_each_word():
    image = _bold_glyph(True)
    for y in _row_centres(image):
        for first, last in _words_along(image, y):
            bright = [x for x in range(first, last + 1) if _alpha(image, x, y) >= FULL]
            share = (bright[-1] - bright[0] + 1) / (last - first + 1)
            assert 0.4 <= share <= 0.6

def test_switching_it_on_only_adds_ink():
    off, on = _bold_glyph(False), _bold_glyph(True)
    # Shrinking the drawing makes the soft tone dip a little right beside the
    # sharp edge of a bright front (the resize overshoots at a step). That is
    # about a tenth of the step, so a pixel may sit a little under its old
    # value, but never by much.
    for y in range(BOLD_SIZE):
        for x in range(BOLD_SIZE):
            assert _alpha(on, x, y) >= _alpha(off, x, y) - 15
    assert sum(on.getchannel("A").tobytes()) > sum(off.getchannel("A").tobytes()) * 1.2

@pytest.mark.parametrize("bold_starts", [False, True])
def test_bold_glyph_pixels_use_the_colour_that_was_asked_for(bold_starts):
    image = _bold_glyph(bold_starts)
    inked = [image.getpixel((x, y)) for y in range(BOLD_SIZE) for x in range(BOLD_SIZE)
             if image.getpixel((x, y))[3] >= 100]
    assert inked, "expected some inked pixels"
    # The resize overshoots a little beside the edge between the soft tone and
    # the bright front, so a single pixel can be off by a fair bit. What counts
    # is that the colour is right on average and never wildly off.
    for channel, wanted in enumerate(INK):
        average = sum(pixel[channel] for pixel in inked) / len(inked)
        assert abs(average - wanted) <= 4
        assert all(abs(pixel[channel] - wanted) <= 30 for pixel in inked)

def test_a_see_through_colour_makes_a_see_through_glyph():
    # The soft tone is worked out from the colour's own alpha, so a glyph asked
    # for at half strength is about half as strong everywhere, not full strength.
    full = _draw_bold_starts_glyph(BOLD_SIZE, (*INK, 255), True)
    half = _draw_bold_starts_glyph(BOLD_SIZE, (*INK, 128), True)
    for y in _row_centres(full):
        for word in _words_along(full, y):
            front, tail = _front_and_tail(word)
            assert 115 <= _alpha(half, front, y) <= 145
            assert 55 <= _alpha(half, tail, y) <= 75


# ---- Bold word starts icon ----

def _source_pixels(icon):
    return icon.cget("light_image").tobytes()


@pytest.mark.parametrize("is_on", [False, True])
def test_bold_starts_icon_is_sized_for_the_screen_not_the_drawing(is_on):
    icon = bold_starts_icon(is_on, 24)
    assert icon.cget("size") == (24, 24)
    # Drawn larger and only ever scaled down, so it stays sharp on high-DPI
    # displays, like the other button icons.
    assert icon.cget("light_image").size[0] > 24
    assert icon.cget("light_image").size == icon.cget("dark_image").size

@pytest.mark.parametrize("is_on", [False, True])
def test_bold_starts_icon_is_24px_when_no_size_is_given(is_on):
    assert bold_starts_icon(is_on).cget("size") == (24, 24)

@pytest.mark.parametrize("is_on", [False, True])
def test_bold_starts_icon_follows_the_size_it_is_asked_for(is_on):
    icon = bold_starts_icon(is_on, 16)
    assert icon.cget("size") == (16, 16)
    assert icon.cget("light_image").size[0] > 16

def test_the_icon_is_white_in_both_appearance_modes_like_the_other_page_icons():
    icon = bold_starts_icon(True)
    assert _source_pixels(icon) == icon.cget("dark_image").tobytes()
    image = icon.cget("light_image")
    # Only the fully opaque pixels say what colour the ink is. The faint pixels
    # along an edge come out of the resize with noisy colour values.
    solid = [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)
             if image.getpixel((x, y))[3] == 255]
    assert solid, "expected some fully opaque pixels"
    for channel in range(3):
        assert sum(pixel[channel] for pixel in solid) / len(solid) >= 250

def test_the_on_and_off_icons_look_different():
    assert _source_pixels(bold_starts_icon(True)) != _source_pixels(bold_starts_icon(False))

def test_the_on_icon_is_the_one_with_the_word_starts_brightened():
    # Not just "different": on is the one with more ink, whichever way round
    # the two are asked for.
    on = bold_starts_icon(True).cget("light_image").getchannel("A").tobytes()
    off = bold_starts_icon(False).cget("light_image").getchannel("A").tobytes()
    assert sum(on) > sum(off) * 1.2

@pytest.mark.parametrize("is_on", [False, True])
def test_neither_state_looks_like_the_normalize_or_revert_icons(is_on):
    icon = _source_pixels(bold_starts_icon(is_on))
    assert icon != _source_pixels(normalize_icon())
    assert icon != _source_pixels(revert_icon())