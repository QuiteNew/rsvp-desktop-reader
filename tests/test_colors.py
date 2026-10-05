from core.colors import blend_colors, _channels


# blend_colors

def test_blend_at_zero_returns_the_first_colour():
    assert blend_colors("#000000", "#FFFFFF", 0.0) == "#000000"

def test_blend_at_one_returns_the_second_colour():
    assert blend_colors("#000000", "#FFFFFF", 1.0) == "#FFFFFF"

def test_blend_midpoint_is_halfway():
    # round(255 * 0.5) == 128 == 0x80 on each channel.
    assert blend_colors("#000000", "#FFFFFF", 0.5) == "#808080"

def test_blend_midpoint_between_two_colours():
    # red -> blue at the midpoint.
    assert blend_colors("#FF0000", "#0000FF", 0.5) == "#800080"

def test_blend_clamps_ratio_below_zero_to_the_first_colour():
    assert blend_colors("#000000", "#FFFFFF", -1.0) == "#000000"

def test_blend_clamps_ratio_above_one_to_the_second_colour():
    assert blend_colors("#000000", "#FFFFFF", 2.0) == "#FFFFFF"

def test_blend_accepts_colours_without_a_leading_hash():
    assert blend_colors("000000", "FFFFFF", 0.0) == "#000000"

def test_blend_expands_short_form_colours():
    assert blend_colors("#000", "#fff", 1.0) == "#FFFFFF"
    assert blend_colors("#f00", "#00f", 0.5) == "#800080"

def test_blend_output_is_uppercase_regardless_of_input_case():
    assert blend_colors("#ffffff", "#ffffff", 0.0) == "#FFFFFF"

def test_blend_output_is_zero_padded_per_channel():
    assert blend_colors("#000000", "#0a0b0c", 1.0) == "#0A0B0C"


# _channels

def test_channels_splits_full_hex():
    assert _channels("#FFFFFF") == (255, 255, 255)
    assert _channels("#1a2b3c") == (26, 43, 60)

def test_channels_tolerates_missing_hash():
    assert _channels("000000") == (0, 0, 0)

def test_channels_expands_short_form():
    # "#abc" -> "aabbcc" -> (170, 187, 204)
    assert _channels("#abc") == (170, 187, 204)