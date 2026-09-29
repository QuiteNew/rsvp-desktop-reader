from core.colors import blend_colors


def test_blend_ratio_zero_returns_first_color():
    assert blend_colors("#000000", "#FFFFFF", 0.0) == "#000000"

def test_blend_ratio_one_returns_second_color():
    assert blend_colors("#000000", "#FFFFFF", 1.0) == "#FFFFFF"

def test_blend_midpoint_is_halfway():
    assert blend_colors("#000000", "#FFFFFF", 0.5) == "#808080"

def test_blend_clamps_below_zero():
    assert blend_colors("#102030", "#405060", -1.0) == "#102030"

def test_blend_clamps_above_one():
    assert blend_colors("#102030", "#405060", 2.0) == "#405060"

def test_blend_accepts_short_hex():
    # "#abc" expands to "#aabbcc".
    assert blend_colors("#abc", "#abc", 0.5) == "#AABBCC"

def test_blend_is_per_channel():
    # Red toward green at the midpoint blends each channel independently.
    assert blend_colors("#FF0000", "#00FF00", 0.5) == "#808000"

def test_blend_works_without_leading_hash():
    assert blend_colors("000000", "FFFFFF", 0.5) == "#808080"