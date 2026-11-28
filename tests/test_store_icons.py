"""Tests for store/make_icons.py, which draws the app icon at any size for the
Microsoft Store.

The one picture that exists is assets/icons/app.png at 256 pixels, and the
script's numbers were measured from it. The check that matters most is the
first one: the icon drawn at 256 has to land on top of that picture. If a
number is changed by accident, or the drawing is changed so a shape moves,
that comparison catches it. The rest check the colours, the corners, the SVG,
the files the script writes and the logo set for the Store package."""

import importlib.util
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "store" / "make_icons.py"
APP_ICON = ROOT / "assets" / "icons" / "app.png"


def _load_script():
    """Loads store/make_icons.py by its path. It lives outside the packages the
    app imports from, so it can't be imported by name."""
    spec = importlib.util.spec_from_file_location("make_icons", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["make_icons"] = module
    spec.loader.exec_module(module)
    return module


icons = _load_script()


def _hex(colour: str) -> tuple[int, int, int]:
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def _close(pixel, colour: str, tolerance: int = 6) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(pixel[:3], _hex(colour)))


def _on_magenta(image: Image.Image) -> Image.Image:
    """The picture laid over a flat colour that appears nowhere in the icon, so
    a change in the see-through corners counts as a difference too."""
    backing = Image.new("RGBA", image.size, (255, 0, 255, 255))
    return Image.alpha_composite(backing, image.convert("RGBA")).convert("RGB")


# ---- It is the app's icon ----

def test_the_icon_drawn_at_256_lands_on_top_of_the_one_in_the_app():
    """The measured numbers reproduce app.png to within the softness its own
    resizing left in the edges. A shape that moved by half a pixel would put
    pixels well past the limit; the best fit is 21 out of 255 at worst."""
    difference = ImageChops.difference(
        _on_magenta(Image.open(APP_ICON)), _on_magenta(icons.render(256))
    ).convert("L")
    histogram = difference.histogram()
    worst = max(level for level, count in enumerate(histogram) if count)
    assert worst <= 40, f"the drawn icon is off from app.png by up to {worst} out of 255"


@pytest.mark.parametrize("size", [16, 44, 150, 256, 300, 1024])
def test_it_draws_the_size_asked_for(size):
    image = icons.render(size)
    assert image.size == (size, size)
    assert image.mode == "RGBA"


@pytest.mark.parametrize("size", [16, 256, 300, 1024])
def test_the_corners_are_see_through_and_the_middle_is_not(size):
    image = icons.render(size)
    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel((size - 1, size - 1))[3] == 0
    assert image.getpixel((size // 2, size // 2))[3] == 255


def test_the_three_colours_are_the_apps_own():
    image = icons.render(1024)
    scale = 1024 / icons.CANVAS
    assert _close(image.getpixel((round(20 * scale), round(128 * scale))), icons.COCOA)
    for centre, colour in zip(icons.BAR_CENTRES_X, icons.BAR_COLOURS):
        assert _close(image.getpixel((round(centre * scale), round(128 * scale))), colour), centre
    assert icons.BAR_COLOURS == (icons.CREAM, icons.AMBER, icons.CREAM)
    assert _close(image.getpixel((round(icons.EYE_CENTRE[0] * scale), round(100 * scale) + 12)), icons.CREAM)


def test_the_colours_are_the_ones_in_the_apps_own_picture():
    """The colours are read off app.png itself, not off the script's constants,
    so a constant that gets changed can't take the check with it."""
    original = Image.open(APP_ICON).convert("RGBA")
    assert _close(original.getpixel((20, 128)), icons.COCOA, tolerance=3)
    assert _close(original.getpixel((60, 128)), icons.CREAM, tolerance=3)
    assert _close(original.getpixel((167, 128)), icons.CREAM, tolerance=3)
    assert _close(original.getpixel((200, 128)), icons.AMBER, tolerance=3)


@pytest.mark.parametrize("size", [300, 1024])
def test_a_bar_has_the_area_its_numbers_give(size):
    """Adding up how much of the amber bar is covered gives its area to a small
    fraction of a pixel, so a shape drawn a hair too big, or too small, shows
    here even where the eye can't see it."""
    image = icons.render(size)
    scale = size / icons.CANVAS
    centre = icons.BAR_CENTRES_X[1]
    box = (
        round((centre - icons.BAR_WIDTH) * scale),
        round((icons.BAR_CENTRE_Y - icons.BAR_HEIGHT) * scale),
        round((centre + icons.BAR_WIDTH) * scale),
        round((icons.BAR_CENTRE_Y + icons.BAR_HEIGHT) * scale),
    )
    red = image.crop(box).convert("RGB").getchannel(0)
    pixels = red.width * red.height
    dark, amber = _hex(icons.COCOA)[0], _hex(icons.AMBER)[0]
    covered = (sum(level * count for level, count in enumerate(red.histogram())) - dark * pixels) / (amber - dark)
    radius = icons.BAR_WIDTH / 2
    exact = (icons.BAR_WIDTH * icons.BAR_HEIGHT - (4 - math.pi) * radius ** 2) * scale ** 2
    assert covered / exact == pytest.approx(1, abs=0.0015)


def _covered(image: Image.Image, box, dark: tuple, light: tuple) -> float:
    """How much of the box is light, in whole pixels, adding up the part-covered
    ones at their share. It reads the red channel, which differs between every
    pair of colours in the icon."""
    red = image.crop(box).convert("RGB").getchannel(0)
    pixels = red.width * red.height
    total = sum(level * count for level, count in enumerate(red.histogram()))
    return (total - dark[0] * pixels) / (light[0] - dark[0])


def test_the_numbers_give_the_areas_the_apps_own_picture_has():
    """Each shape's area, added up from the pixels of app.png, has to match what
    its numbers say. This is what pins the sizes to the real icon even when a
    number and the drawing are changed together: 0.25 of a pixel on a bar's
    width is over 1% of its area, and the limit here is 0.6%."""
    original = Image.open(APP_ICON).convert("RGBA")
    cocoa, cream = _hex(icons.COCOA), _hex(icons.CREAM)
    centre_x, centre_y = icons.EYE_CENTRE
    pupil = icons.PUPIL_RADIUS
    pi = math.pi

    bar_area = icons.BAR_WIDTH * icons.BAR_HEIGHT - (4 - pi) * (icons.BAR_WIDTH / 2) ** 2
    ratios = {}
    for number, (centre, colour) in enumerate(zip(icons.BAR_CENTRES_X, icons.BAR_COLOURS), start=1):
        box = (
            int(centre - icons.BAR_WIDTH), int(icons.BAR_CENTRE_Y - icons.BAR_HEIGHT),
            int(centre + icons.BAR_WIDTH) + 1, int(icons.BAR_CENTRE_Y + icons.BAR_HEIGHT) + 1,
        )
        ratios[f"bar {number}"] = _covered(original, box, cocoa, _hex(colour)) / bar_area

    # The pupil is the part of a small box round it that isn't cream.
    box = (int(centre_x - pupil - 1), int(centre_y - pupil - 1), int(centre_x + pupil + 2), int(centre_y + pupil + 2))
    pupil_area = (box[2] - box[0]) * (box[3] - box[1]) - _covered(original, box, cocoa, cream)
    ratios["pupil"] = pupil_area / (pi * pupil ** 2)

    # The eye is the cream round the pupil, and the pupil's own area.
    radius = icons.eye_circle_radius()
    offset = radius - icons.EYE_HALF_HEIGHT
    eye_area = 2 * (radius ** 2 * math.acos(offset / radius)
                    - offset * (radius ** 2 - offset ** 2) ** 0.5)
    box = (
        int(centre_x - icons.EYE_HALF_WIDTH) - 3, int(centre_y - icons.EYE_HALF_HEIGHT) - 3,
        int(centre_x + icons.EYE_HALF_WIDTH) + 4, int(centre_y + icons.EYE_HALF_HEIGHT) + 4,
    )
    ratios["eye"] = (_covered(original, box, cocoa, cream) + pupil_area) / eye_area

    # The corner is the see-through part of the top left 64 x 64 pixels.
    opaque = sum(level * count for level, count in enumerate(original.getchannel("A").crop((0, 0, 64, 64)).histogram())) / 255
    ratios["corner"] = (64 * 64 - opaque) / ((1 - pi / 4) * icons.CORNER_RADIUS ** 2)

    for shape, ratio in ratios.items():
        assert ratio == pytest.approx(1, abs=0.006), f"{shape}: its numbers give {ratio:.4f} of the area app.png has"


def test_the_edge_of_a_corner_keeps_its_colour():
    """Where the corner curves, pixels are partly see-through. Their colour must
    still be the dark of the square, or the curve gets a dark fringe."""
    image = icons.render(256)
    edge = [
        image.getpixel((x, y))
        for x in range(60)
        for y in range(60)
        if 20 < image.getpixel((x, y))[3] < 235
    ]
    assert len(edge) > 30
    assert all(_close(pixel, icons.COCOA, tolerance=12) for pixel in edge)


# ---- The shapes are the ones in the numbers ----

def test_the_eye_comes_to_a_point_at_each_side_and_has_its_height():
    image = icons.render(1024)
    scale = 1024 / icons.CANVAS
    cx, cy = icons.EYE_CENTRE
    tip_left = (cx - icons.EYE_HALF_WIDTH) * scale
    tip_right = (cx + icons.EYE_HALF_WIDTH) * scale
    y = round(cy * scale)
    assert _close(image.getpixel((round(tip_left) - 8, y)), icons.COCOA)
    assert _close(image.getpixel((round(tip_left) + 8, y)), icons.CREAM)
    assert _close(image.getpixel((round(tip_right) - 8, y)), icons.CREAM)
    assert _close(image.getpixel((round(tip_right) + 8, y)), icons.COCOA)
    top = (cy - icons.EYE_HALF_HEIGHT) * scale
    x = round(cx * scale)
    assert _close(image.getpixel((x, round(top) - 8)), icons.COCOA)
    assert _close(image.getpixel((x, round(top) + 8)), icons.CREAM)


def test_the_pupil_sits_in_the_middle_of_the_eye():
    image = icons.render(1024)
    scale = 1024 / icons.CANVAS
    cx, cy = icons.EYE_CENTRE
    assert _close(image.getpixel((round(cx * scale), round(cy * scale))), icons.COCOA)
    inside = round((cx - icons.PUPIL_RADIUS) * scale) - 10
    assert _close(image.getpixel((inside, round(cy * scale))), icons.CREAM)


def test_the_bars_are_one_size_with_round_ends():
    image = icons.render(1024)
    scale = 1024 / icons.CANVAS
    top = (icons.BAR_CENTRE_Y - icons.BAR_HEIGHT / 2) * scale
    bottom = (icons.BAR_CENTRE_Y + icons.BAR_HEIGHT / 2) * scale
    for centre, colour in zip(icons.BAR_CENTRES_X, icons.BAR_COLOURS):
        x = round(centre * scale)
        assert _close(image.getpixel((x, round(top) - 6)), icons.COCOA), centre
        assert _close(image.getpixel((x, round(top) + 20)), colour), centre
        assert _close(image.getpixel((x, round(bottom) - 20)), colour), centre
        assert _close(image.getpixel((x, round(bottom) + 6)), icons.COCOA), centre
        # The end is round: the corner of the bar's box is still the background.
        corner_x = round(centre * scale - icons.BAR_WIDTH * scale / 2) + 3
        assert _close(image.getpixel((corner_x, round(top) + 3)), icons.COCOA), centre


# ---- The SVG ----

def test_the_svg_is_valid_and_has_every_shape():
    root = ET.fromstring(icons.svg_text())
    assert root.tag.endswith("svg")
    assert root.get("viewBox") == f"0 0 {icons.CANVAS} {icons.CANVAS}"
    names = [child.tag.split("}")[1] for child in root]
    assert names == ["rect", "path", "circle", "rect", "rect", "rect"]


def test_the_svg_uses_the_same_colours_and_numbers():
    text = icons.svg_text()
    for colour in (icons.COCOA, icons.CREAM, icons.AMBER):
        assert f'fill="{colour}"' in text
    assert text.count(f'fill="{icons.AMBER}"') == 1
    assert f'rx="{icons.CORNER_RADIUS}"' in text
    assert f'r="{icons.PUPIL_RADIUS}"' in text
    root = ET.fromstring(text)
    bars = [child for child in root if child.tag.endswith("rect")][1:]
    for bar, centre in zip(bars, icons.BAR_CENTRES_X):
        assert float(bar.get("x")) + float(bar.get("width")) / 2 == pytest.approx(centre, abs=0.001)
        assert float(bar.get("height")) == icons.BAR_HEIGHT
        assert float(bar.get("rx")) == pytest.approx(icons.BAR_WIDTH / 2, abs=0.001)


def test_the_eyes_circles_pass_through_its_corners():
    """The two circles are worked out from the eye's width and height, so each
    one must go through both tips and sit the right distance from the line."""
    radius = icons.eye_circle_radius()
    offset = radius - icons.EYE_HALF_HEIGHT
    assert (offset ** 2 + icons.EYE_HALF_WIDTH ** 2) ** 0.5 == pytest.approx(radius)


# ---- The files it writes ----

def test_it_writes_the_svg_and_the_store_pictures(tmp_path):
    written = icons.write_all(tmp_path / "out")
    assert sorted(path.name for path in written) == ["app-icon-1024.png", "app-icon.svg", "store-tile-300.png"]
    for name, size in (("app-icon-1024.png", 1024), ("store-tile-300.png", 300)):
        with Image.open(tmp_path / "out" / name) as written_picture:
            assert written_picture.size == (size, size)
    assert (tmp_path / "out" / "app-icon.svg").read_text(encoding="utf-8") == icons.svg_text()


def test_the_store_tile_is_the_size_the_store_asks_for():
    assert icons.OUTPUTS["store-tile-300.png"] == 300


def test_without_a_folder_it_writes_under_build(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert icons.main(["make_icons.py"]) == 0
    assert (tmp_path / "build" / "store-assets" / "store-tile-300.png").is_file()
    assert capsys.readouterr().out.count("store-assets") == 3


def test_with_a_folder_it_writes_there(tmp_path, capsys):
    assert icons.main(["make_icons.py", str(tmp_path / "somewhere")]) == 0
    assert (tmp_path / "somewhere" / "app-icon.svg").is_file()


# ---- The logos inside the Store package ----

# Written out in full on purpose. The manifest names "Square44x44Logo.png" and
# Windows finds the rest by these exact names, so a rename in the script has to
# show up here as a failing test and not slip through.
EXPECTED_LOGOS = {
    "StoreLogo.scale-100.png": 50,
    "StoreLogo.scale-125.png": 63,
    "StoreLogo.scale-150.png": 75,
    "StoreLogo.scale-200.png": 100,
    "StoreLogo.scale-400.png": 200,
    "Square44x44Logo.scale-100.png": 44,
    "Square44x44Logo.scale-125.png": 55,
    "Square44x44Logo.scale-150.png": 66,
    "Square44x44Logo.scale-200.png": 88,
    "Square44x44Logo.scale-400.png": 176,
    "Square150x150Logo.scale-100.png": 150,
    "Square150x150Logo.scale-125.png": 188,
    "Square150x150Logo.scale-150.png": 225,
    "Square150x150Logo.scale-200.png": 300,
    "Square150x150Logo.scale-400.png": 600,
    "Square44x44Logo.targetsize-16.png": 16,
    "Square44x44Logo.targetsize-24.png": 24,
    "Square44x44Logo.targetsize-32.png": 32,
    "Square44x44Logo.targetsize-48.png": 48,
    "Square44x44Logo.targetsize-256.png": 256,
    "Square44x44Logo.targetsize-16_altform-unplated.png": 16,
    "Square44x44Logo.targetsize-24_altform-unplated.png": 24,
    "Square44x44Logo.targetsize-32_altform-unplated.png": 32,
    "Square44x44Logo.targetsize-48_altform-unplated.png": 48,
    "Square44x44Logo.targetsize-256_altform-unplated.png": 256,
}


def test_the_package_logos_are_the_ones_windows_looks_for_at_the_sizes_it_wants():
    assert icons.msix_logo_sizes() == EXPECTED_LOGOS


@pytest.mark.parametrize("base_name, base_size", [("StoreLogo", 50), ("Square44x44Logo", 44), ("Square150x150Logo", 150)])
def test_each_scale_is_the_base_size_times_the_percentage_to_the_nearest_pixel(base_name, base_size):
    sizes = icons.msix_logo_sizes()
    for percent in (100, 125, 150, 200, 400):
        expected = math.floor(base_size * percent / 100 + 0.5)
        assert sizes[f"{base_name}.scale-{percent}.png"] == expected


def test_every_exact_size_comes_plain_and_unplated():
    sizes = icons.msix_logo_sizes()
    for size in (16, 24, 32, 48, 256):
        assert sizes[f"Square44x44Logo.targetsize-{size}.png"] == size
        assert sizes[f"Square44x44Logo.targetsize-{size}_altform-unplated.png"] == size


def test_it_writes_every_package_logo_at_its_size(tmp_path):
    written = icons.write_msix_logos(tmp_path / "Assets")
    assert sorted(path.name for path in written) == sorted(EXPECTED_LOGOS)
    for name, size in EXPECTED_LOGOS.items():
        with Image.open(tmp_path / "Assets" / name) as logo:
            assert logo.size == (size, size), name
            assert logo.mode == "RGBA", name


def test_the_package_logos_are_the_icon_drawn_at_that_size(tmp_path):
    """Same picture as render() gives, not a stretched copy of a bigger one, so
    the small ones are drawn small and stay crisp."""
    icons.write_msix_logos(tmp_path)
    for name, size in EXPECTED_LOGOS.items():
        with Image.open(tmp_path / name) as logo:
            assert logo.tobytes() == icons.render(size).tobytes(), name


def test_the_package_logos_have_see_through_corners_and_the_amber_bar(tmp_path):
    icons.write_msix_logos(tmp_path)
    for name, size in EXPECTED_LOGOS.items():
        with Image.open(tmp_path / name) as logo:
            assert logo.getpixel((0, 0))[3] == 0, name
            assert logo.getpixel((size - 1, size - 1))[3] == 0, name
            if size >= 44:  # below that the bar is about a pixel wide and blends
                bar_x = round(icons.BAR_CENTRES_X[1] / icons.CANVAS * size)
                assert _close(logo.getpixel((bar_x, size // 2)), icons.AMBER, tolerance=12), name


def test_the_package_logos_are_not_written_with_the_listing_pictures(tmp_path):
    """The listing files and the package files are separate sets: the Store
    listing takes the 300 pixel tile on its own, and the package must not end
    up with a stray copy of it or of the SVG."""
    icons.write_all(tmp_path / "listing")
    assert not any(path.name.startswith(("Square", "StoreLogo")) for path in (tmp_path / "listing").iterdir())


# ---- It stays out of the app ----

def test_the_app_never_imports_the_script():
    """Nothing the app runs may depend on store/, because the build doesn't
    carry it."""
    sources = [ROOT / "main.py", *(ROOT / "core").rglob("*.py"), *(ROOT / "gui").rglob("*.py")]
    for source in sources:
        assert not re.search(r"make_icons", source.read_text(encoding="utf-8")), source
