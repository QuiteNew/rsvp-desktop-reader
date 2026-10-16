"""Tests for putting back the guide mark colour together with its "follows the
theme" flag: SettingsStore.restore_guide_mark_color().

Reading profiles need this. The existing set_guide_mark_color() can only turn
following off, and only when the colour changes, so it can't put back a colour
that was recorded as "follows the theme", or mark a colour as picked by hand
when it happens to match the current one."""

import pytest

from core.settings_store import AppSettings, SettingsStore


@pytest.fixture
def settings(tmp_path):
    return SettingsStore(settings_directory=str(tmp_path / "settings"))


def test_guide_mark_color_follows_the_theme_on_a_fresh_store(settings):
    assert settings.guide_mark_color_is_default is True

def test_picking_a_guide_mark_colour_by_hand_stops_it_following_the_theme(settings):
    settings.set_guide_mark_color("#112233")
    assert settings.guide_mark_color_is_default is False

def test_restore_guide_mark_color_sets_the_colour_and_the_flag(settings):
    settings.restore_guide_mark_color("#112233", False)
    assert settings.guide_mark_color == "#112233"
    assert settings.guide_mark_color_is_default is False

def test_restore_guide_mark_color_can_turn_following_back_on(settings):
    settings.set_guide_mark_color("#112233")
    settings.restore_guide_mark_color("#F2E8DC", True)
    assert settings.guide_mark_color == "#F2E8DC"
    assert settings.guide_mark_color_is_default is True

def test_restore_guide_mark_color_can_mark_the_current_colour_as_picked_by_hand(settings):
    # set_guide_mark_color() would leave the flag alone here, because the
    # colour doesn't change. That is the gap this method fills.
    same = settings.guide_mark_color
    settings.restore_guide_mark_color(same, False)
    assert settings.guide_mark_color == same
    assert settings.guide_mark_color_is_default is False

def test_restore_guide_mark_color_is_saved_and_survives_a_restart(settings, tmp_path):
    settings.restore_guide_mark_color("#112233", False)
    again = SettingsStore(settings_directory=str(tmp_path / "settings"))
    assert again.guide_mark_color == "#112233"
    assert again.guide_mark_color_is_default is False

def test_a_colour_restored_as_following_is_updated_by_the_startup_resync(settings):
    settings.restore_guide_mark_color("#000000", True)
    settings.resync_guide_mark_color_default("#F2E8DC")
    assert settings.guide_mark_color == "#F2E8DC"

def test_a_colour_restored_as_picked_by_hand_is_left_alone_by_the_startup_resync(settings):
    settings.restore_guide_mark_color("#112233", False)
    settings.resync_guide_mark_color_default("#F2E8DC")
    assert settings.guide_mark_color == "#112233"

def test_restore_guide_mark_color_does_not_touch_other_settings(settings):
    settings.set_defaults(450, "#112233", "#445566", "#778899", 50)
    settings.restore_guide_mark_color("#AABBCC", False)
    assert settings.default_wpm == 450
    assert settings.default_font_color == "#112233"
    assert settings.guide_mark_thickness_px == AppSettings().guide_mark_thickness_px