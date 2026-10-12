"""Tests for the pure horizontal-scroll geometry in core/scroll.py: the pan
range, clamping, and the round trip between a pan offset and the (first, last)
thumb fractions a Tk-style scrollbar uses."""

from core.scroll import pan_range, clamp_pan, scrollbar_fractions, pan_from_fraction


def test_no_overflow_fills_the_track():
    # Nothing spills either side: the thumb spans the whole track and there is
    # nowhere to pan.
    assert scrollbar_fractions(100, 0, 0, 0) == (0.0, 1.0)
    assert pan_from_fraction(0.0, 100, 0, 0) == 0.0
    assert pan_range(0, 0) == (0.0, 0.0)


def test_pan_range_is_right_overflow_negative_to_left_overflow_positive():
    assert pan_range(0, 50) == (-50, 0)
    assert pan_range(30, 0) == (0, 30)
    assert pan_range(20, 40) == (-40, 20)


def test_clamp_keeps_pan_within_range():
    assert clamp_pan(-999, 0, 50) == -50   # cannot pan further left than the right overflow
    assert clamp_pan(999, 0, 50) == 0       # no left overflow, so no rightward pan
    assert clamp_pan(-10, 0, 50) == -10     # inside the range, untouched


def test_right_overflow_thumb_sits_left_at_centre_and_right_when_panned():
    # viewport 100, 50px spills off the right. Virtual strip is 150 wide, so the
    # thumb covers two thirds of the track.
    first, last = scrollbar_fractions(100, 0, 50, 0)      # centred
    assert first == 0.0
    assert abs(last - (100 / 150)) < 1e-9
    # Panned fully left (pan = -50) brings the right overflow into view: the
    # thumb slides to the right end of the track.
    first, last = scrollbar_fractions(100, 0, 50, -50)
    assert abs(last - 1.0) < 1e-9
    assert abs(first - (50 / 150)) < 1e-9


def test_fraction_to_pan_is_the_inverse_of_pan_to_fraction():
    viewport, ol, orr = 100, 20, 40
    for pan in (-40, -25, -10, 0, 10, 20):
        first, _ = scrollbar_fractions(viewport, ol, orr, pan)
        assert abs(pan_from_fraction(first, viewport, ol, orr) - pan) < 1e-6


def test_fraction_past_the_ends_clamps_to_the_pan_limits():
    viewport, ol, orr = 100, 0, 50
    assert pan_from_fraction(0.0, viewport, ol, orr) == 0      # hard left: centred (no left overflow)
    assert pan_from_fraction(1.0, viewport, ol, orr) == -50    # hard right: fully reveals the right overflow


def test_left_overflow_panning_right_reveals_it():
    # 30px spills off the left; panning right (pan = +30) brings it into view and
    # the thumb sits at the far left of the track.
    first, last = scrollbar_fractions(100, 30, 0, 30)
    assert abs(first - 0.0) < 1e-9
    assert abs(last - (100 / 130)) < 1e-9