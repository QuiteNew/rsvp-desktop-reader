import json
import pytest
from core.settings_store import SettingsStore, AppSettings


@pytest.fixture
def store(tmp_path):
    """A fresh SettingsStore in a throwaway temporary folder, so it never
    touches your real ~/.rsvp_reader/settings.json."""
    return SettingsStore(settings_directory=str(tmp_path))


# A fresh store matches AppSettings' own defaults
# These read from a live AppSettings() instead of repeating the numbers
# here, so the tests can never drift out of sync with the dataclass.

def test_fresh_store_window_size_matches_defaults(store):
    defaults = AppSettings()
    assert store.window_width == defaults.window_width
    assert store.window_height == defaults.window_height

def test_fresh_store_layout_matches_defaults(store):
    defaults = AppSettings()
    assert store.sidebar_width == defaults.sidebar_width
    assert store.bottom_band_height == defaults.bottom_band_height

def test_fresh_store_reading_defaults_match(store):
    defaults = AppSettings()
    assert store.default_wpm == defaults.default_wpm
    assert store.default_font_color == defaults.default_font_color
    assert store.default_highlight_color == defaults.default_highlight_color
    assert store.default_background_color == defaults.default_background_color

def test_fresh_store_skip_behavior_matches_defaults(store):
    defaults = AppSettings()
    assert store.skip_word_count == defaults.skip_word_count
    assert store.pause_on_skip == defaults.pause_on_skip

def test_fresh_store_freeform_resize_matches_defaults(store):
    assert store.freeform_resize_enabled == AppSettings().freeform_resize_enabled

def test_fresh_store_appearance_mode_matches_defaults(store):
    assert store.appearance_mode == AppSettings().appearance_mode

def test_fresh_store_data_directory_matches_defaults(store):
    assert store.data_directory == AppSettings().data_directory


# set_window_size

def test_set_window_size_updates_both_dimensions(store):
    store.set_window_size(1200, 800)
    assert store.window_width == 1200
    assert store.window_height == 800

def test_set_window_size_does_not_affect_other_settings(store):
    store.set_window_size(1200, 800)
    assert store.sidebar_width == AppSettings().sidebar_width
    assert store.appearance_mode == AppSettings().appearance_mode


# set_layout_sizes

def test_set_layout_sizes_updates_both_values(store):
    store.set_layout_sizes(300, 150)
    assert store.sidebar_width == 300
    assert store.bottom_band_height == 150

def test_set_layout_sizes_does_not_affect_window_size(store):
    store.set_window_size(1200, 800)
    store.set_layout_sizes(300, 150)
    assert store.window_width == 1200
    assert store.window_height == 800


# set_defaults

def test_set_defaults_updates_all_four_values(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    assert store.default_wpm == 500
    assert store.default_font_color == "#111111"
    assert store.default_highlight_color == "#222222"
    assert store.default_background_color == "#333333"

def test_set_defaults_does_not_affect_skip_behavior(store):
    store.set_skip_behavior(20, True)
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    assert store.skip_word_count == 20
    assert store.pause_on_skip is True


# set_data_directory

def test_set_data_directory_updates_value(store):
    store.set_data_directory("/some/new/path")
    assert store.data_directory == "/some/new/path"


# set_freeform_resize_enabled

def test_set_freeform_resize_enabled_true(store):
    store.set_freeform_resize_enabled(True)
    assert store.freeform_resize_enabled is True

def test_set_freeform_resize_enabled_false(store):
    store.set_freeform_resize_enabled(True)
    store.set_freeform_resize_enabled(False)
    assert store.freeform_resize_enabled is False


# set_skip_behavior

def test_set_skip_behavior_updates_both_values(store):
    store.set_skip_behavior(25, True)
    assert store.skip_word_count == 25
    assert store.pause_on_skip is True

def test_set_skip_behavior_does_not_affect_defaults(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_skip_behavior(25, True)
    assert store.default_wpm == 500


# set_appearance_mode

def test_set_appearance_mode_light(store):
    store.set_appearance_mode("light")
    assert store.appearance_mode == "light"

def test_set_appearance_mode_dark(store):
    store.set_appearance_mode("dark")
    assert store.appearance_mode == "dark"

def test_set_appearance_mode_system(store):
    store.set_appearance_mode("system")
    assert store.appearance_mode == "system"


# Saving and loading

def test_persists_and_reloads_every_setting_correctly(tmp_path):
    directory = str(tmp_path)

    first = SettingsStore(settings_directory=directory)
    first.set_window_size(1500, 900)
    first.set_layout_sizes(350, 175)
    first.set_defaults(700, "#AAAAAA", "#BBBBBB", "#CCCCCC", 48)
    first.set_data_directory("/custom/transcripts")
    first.set_freeform_resize_enabled(True)
    first.set_skip_behavior(30, True)
    first.set_appearance_mode("dark")
    first.set_highlight_offset_px(-2)

    second = SettingsStore(settings_directory=directory)

    assert second.window_width == 1500
    assert second.window_height == 900
    assert second.sidebar_width == 350
    assert second.bottom_band_height == 175
    assert second.default_wpm == 700
    assert second.default_font_color == "#AAAAAA"
    assert second.default_font_size == 48
    assert second.default_highlight_color == "#BBBBBB"
    assert second.default_background_color == "#CCCCCC"
    assert second.data_directory == "/custom/transcripts"
    assert second.freeform_resize_enabled is True
    assert second.skip_word_count == 30
    assert second.pause_on_skip is True
    assert second.appearance_mode == "dark"
    assert second.highlight_offset_px == -2

def test_missing_settings_file_falls_back_to_fresh_defaults(tmp_path):
    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.window_width == AppSettings().window_width
    assert store.appearance_mode == AppSettings().appearance_mode

def test_corrupted_settings_file_falls_back_to_fresh_defaults(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("{not valid json!!!", encoding="utf-8")

    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.window_width == AppSettings().window_width

def test_settings_file_missing_newer_fields_fills_in_defaults(tmp_path):
    """Simulates upgrading from an older version of the app, where
    settings.json was saved before some fields, like appearance_mode,
    existed. The dataclass should fill in any missing keys with its own
    defaults, and this checks that it really does."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({
        "window_width": 1234,
        "window_height": 567,
    }), encoding="utf-8")

    store = SettingsStore(settings_directory=str(tmp_path))
    assert store.window_width == 1234
    assert store.window_height == 567
    assert store.appearance_mode == AppSettings().appearance_mode  # filled in, not missing or crashing

def test_settings_file_with_stale_header_height_field_loads_correctly(tmp_path):
    """header_height was removed from AppSettings, but older settings.json
    files may still have it saved. Passing an unknown keyword straight into
    AppSettings(**data) would raise a TypeError. This test would fail
    without the data.pop("header_height", None) step, which proves that
    step really works."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({
        "window_width": 1000,
        "window_height": 650,
        "header_height": 80,  # stale field, no longer a real AppSettings attribute
    }), encoding="utf-8")

    store = SettingsStore(settings_directory=str(tmp_path))  # must not raise TypeError
    assert store.window_width == 1000
    assert store.window_height == 650


# Separate settings folders don't affect each other

def test_two_stores_in_different_directories_do_not_interfere(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    store_a = SettingsStore(settings_directory=str(dir_a))
    store_b = SettingsStore(settings_directory=str(dir_b))

    store_a.set_appearance_mode("dark")
    store_b.set_appearance_mode("light")

    assert store_a.appearance_mode == "dark"
    assert store_b.appearance_mode == "light"
    assert (dir_a / "settings.json").exists()
    assert (dir_b / "settings.json").exists()


# The constructor still works with no arguments

def test_no_argument_constructor_still_works():
    """gui/app.py and gui/theme.py both call SettingsStore() with no
    arguments, so that has to keep working. This test reads the REAL
    ~/.rsvp_reader/settings.json, since there's no other way to check the
    default behavior. It only reads through the constructor and never
    calls a setter, so it can't overwrite anything real."""
    store = SettingsStore()
    assert isinstance(store.appearance_mode, str)
    assert isinstance(store.window_width, int)


# Font size step and highlight offset

def test_fresh_store_font_size_step_matches_defaults(store):
    assert store.font_size_step == AppSettings().font_size_step

def test_set_font_size_step_updates_value(store):
    store.set_font_size_step(5)
    assert store.font_size_step == 5

def test_set_font_size_step_does_not_affect_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_font_size_step(5)
    assert store.default_wpm == 500

def test_fresh_store_highlight_offset_matches_defaults(store):
    assert store.highlight_offset_px == AppSettings().highlight_offset_px

def test_set_highlight_offset_positive_value(store):
    store.set_highlight_offset_px(2)
    assert store.highlight_offset_px == 2

def test_set_highlight_offset_negative_value(store):
    # This is the only setting in the app that allows a negative value.
    store.set_highlight_offset_px(-3)
    assert store.highlight_offset_px == -3

def test_set_highlight_offset_zero_resets_to_default_value(store):
    store.set_highlight_offset_px(3)
    store.set_highlight_offset_px(0)
    assert store.highlight_offset_px == 0

def test_set_highlight_offset_does_not_affect_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_highlight_offset_px(-2)
    assert store.default_wpm == 500


# split_long_paragraphs_enabled

def test_fresh_store_split_long_paragraphs_matches_defaults(store):
    assert store.split_long_paragraphs_enabled == AppSettings().split_long_paragraphs_enabled

def test_set_split_long_paragraphs_enabled_true(store):
    store.set_split_long_paragraphs_enabled(True)
    assert store.split_long_paragraphs_enabled is True

def test_set_split_long_paragraphs_enabled_false(store):
    store.set_split_long_paragraphs_enabled(True)
    store.set_split_long_paragraphs_enabled(False)
    assert store.split_long_paragraphs_enabled is False

def test_set_split_long_paragraphs_does_not_affect_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_split_long_paragraphs_enabled(True)
    assert store.default_wpm == 500

def test_split_long_paragraphs_persists_and_reloads(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_split_long_paragraphs_enabled(True)
    second = SettingsStore(settings_directory=directory)
    assert second.split_long_paragraphs_enabled is True


# resume_rewind

def test_fresh_store_resume_rewind_matches_defaults(store):
    defaults = AppSettings()
    assert store.resume_rewind_enabled == defaults.resume_rewind_enabled
    assert store.resume_rewind_words == defaults.resume_rewind_words

def test_set_resume_rewind_updates_both_values(store):
    store.set_resume_rewind(True, 5)
    assert store.resume_rewind_enabled is True
    assert store.resume_rewind_words == 5

def test_set_resume_rewind_disable(store):
    store.set_resume_rewind(True, 4)
    store.set_resume_rewind(False, 2)
    assert store.resume_rewind_enabled is False
    assert store.resume_rewind_words == 2

def test_set_resume_rewind_does_not_affect_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_resume_rewind(True, 3)
    assert store.default_wpm == 500

def test_resume_rewind_persists_and_reloads(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_resume_rewind(True, 4)
    second = SettingsStore(settings_directory=directory)
    assert second.resume_rewind_enabled is True
    assert second.resume_rewind_words == 4


# warm_up_enabled

def test_fresh_store_warm_up_matches_defaults(store):
    assert store.warm_up_enabled == AppSettings().warm_up_enabled

def test_set_warm_up_enabled_true(store):
    store.set_warm_up_enabled(True)
    assert store.warm_up_enabled is True

def test_set_warm_up_enabled_false(store):
    store.set_warm_up_enabled(True)
    store.set_warm_up_enabled(False)
    assert store.warm_up_enabled is False

def test_set_warm_up_does_not_affect_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_warm_up_enabled(True)
    assert store.default_wpm == 500

def test_warm_up_persists_and_reloads(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_warm_up_enabled(True)
    second = SettingsStore(settings_directory=directory)
    assert second.warm_up_enabled is True


# scrub_pause_enabled (defaults to True, unlike the other behavior toggles)

def test_fresh_store_scrub_pause_matches_defaults(store):
    assert store.scrub_pause_enabled == AppSettings().scrub_pause_enabled

def test_fresh_store_scrub_pause_defaults_to_true(store):
    # Deliberately on by default: it preserves the original scrubber
    # behavior, where releasing the bar pauses reading on the landed word.
    assert store.scrub_pause_enabled is True

def test_set_scrub_pause_enabled_false(store):
    store.set_scrub_pause_enabled(False)
    assert store.scrub_pause_enabled is False

def test_set_scrub_pause_enabled_true(store):
    store.set_scrub_pause_enabled(False)
    store.set_scrub_pause_enabled(True)
    assert store.scrub_pause_enabled is True

def test_set_scrub_pause_does_not_affect_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_scrub_pause_enabled(False)
    assert store.default_wpm == 500

def test_scrub_pause_persists_and_reloads(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_scrub_pause_enabled(False)
    second = SettingsStore(settings_directory=directory)
    assert second.scrub_pause_enabled is False


# length_pacing_enabled

def test_fresh_store_length_pacing_matches_defaults(store):
    assert store.length_pacing_enabled == AppSettings().length_pacing_enabled

def test_set_length_pacing_enabled_true(store):
    store.set_length_pacing_enabled(True)
    assert store.length_pacing_enabled is True

def test_set_length_pacing_enabled_false(store):
    store.set_length_pacing_enabled(True)
    store.set_length_pacing_enabled(False)
    assert store.length_pacing_enabled is False

def test_length_pacing_persists_and_reloads(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_length_pacing_enabled(True)
    second = SettingsStore(settings_directory=directory)
    assert second.length_pacing_enabled is True


# peripheral_context_enabled

def test_fresh_store_peripheral_context_matches_defaults(store):
    assert store.peripheral_context_enabled == AppSettings().peripheral_context_enabled

def test_set_peripheral_context_enabled_true(store):
    store.set_peripheral_context_enabled(True)
    assert store.peripheral_context_enabled is True

def test_set_peripheral_context_enabled_false(store):
    store.set_peripheral_context_enabled(True)
    store.set_peripheral_context_enabled(False)
    assert store.peripheral_context_enabled is False

def test_peripheral_context_persists_and_reloads(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_peripheral_context_enabled(True)
    second = SettingsStore(settings_directory=directory)
    assert second.peripheral_context_enabled is True


# guide_mark_horizontal_enabled

def test_fresh_store_guide_mark_horizontal_matches_defaults(store):
    assert store.guide_mark_horizontal_enabled == AppSettings().guide_mark_horizontal_enabled

def test_set_guide_mark_horizontal_enabled_true(store):
    store.set_guide_mark_horizontal_enabled(True)
    assert store.guide_mark_horizontal_enabled is True

def test_set_guide_mark_horizontal_enabled_false(store):
    store.set_guide_mark_horizontal_enabled(True)
    store.set_guide_mark_horizontal_enabled(False)
    assert store.guide_mark_horizontal_enabled is False

def test_guide_mark_horizontal_persists_and_reloads(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_guide_mark_horizontal_enabled(True)
    second = SettingsStore(settings_directory=directory)
    assert second.guide_mark_horizontal_enabled is True


# guide_mark_thickness_px and guide_mark_length_percent

def test_fresh_store_guide_mark_thickness_matches_defaults(store):
    assert store.guide_mark_thickness_px == AppSettings().guide_mark_thickness_px

def test_set_guide_mark_thickness_px_updates_value(store):
    store.set_guide_mark_thickness_px(5)
    assert store.guide_mark_thickness_px == 5

def test_fresh_store_guide_mark_length_percent_matches_defaults(store):
    assert store.guide_mark_length_percent == AppSettings().guide_mark_length_percent

def test_set_guide_mark_length_percent_updates_value(store):
    store.set_guide_mark_length_percent(50)
    assert store.guide_mark_length_percent == 50

def test_guide_mark_thickness_and_length_persist_and_reload(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_guide_mark_thickness_px(4)
    first.set_guide_mark_length_percent(60)
    second = SettingsStore(settings_directory=directory)
    assert second.guide_mark_thickness_px == 4
    assert second.guide_mark_length_percent == 60


# guide_mark_color and its theme-tracking flag

def test_fresh_store_guide_mark_color_matches_defaults(store):
    assert store.guide_mark_color == AppSettings().guide_mark_color

def test_set_guide_mark_color_updates_the_color(store):
    store.set_guide_mark_color("#123456")
    assert store.guide_mark_color == "#123456"

def test_set_guide_mark_color_persists_and_reloads(tmp_path):
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_guide_mark_color("#123456")
    second = SettingsStore(settings_directory=directory)
    assert second.guide_mark_color == "#123456"

def test_set_guide_mark_color_to_a_new_color_retires_theme_tracking(store):
    # Picking a different color clears the is_default flag. There's no getter
    # for that flag, so we observe it through resync: once retired, a later
    # resync must leave the manual pick alone.
    store.set_guide_mark_color("#123456")
    store.resync_guide_mark_color_default("#999999")
    assert store.guide_mark_color == "#123456"

def test_set_guide_mark_color_to_the_same_color_keeps_theme_tracking(store):
    # Re-applying the current color must not freeze it: the flag stays set,
    # so a later resync can still move it.
    default_color = AppSettings().guide_mark_color
    store.set_guide_mark_color(default_color)  # same as current, flag unchanged
    store.resync_guide_mark_color_default("#999999")
    assert store.guide_mark_color == "#999999"


# resync_guide_mark_color_default

def test_resync_guide_mark_color_updates_while_tracking_default(store):
    # A fresh store is still tracking the theme default, so resync applies.
    store.resync_guide_mark_color_default("#654321")
    assert store.guide_mark_color == "#654321"

def test_resync_guide_mark_color_noop_when_already_equal(store):
    default_color = AppSettings().guide_mark_color
    store.resync_guide_mark_color_default(default_color)
    assert store.guide_mark_color == default_color

def test_resync_guide_mark_color_does_not_override_a_manual_pick(store):
    store.set_guide_mark_color("#ABCDEF")  # manual pick retires theme-tracking
    store.resync_guide_mark_color_default("#000000")
    assert store.guide_mark_color == "#ABCDEF"


# set_skip_word_count_live and flush (the live-save throttle)

def test_set_skip_word_count_live_updates_the_value(store):
    store.set_skip_word_count_live(20)
    assert store.skip_word_count == 20

def test_set_skip_word_count_live_first_write_persists(tmp_path):
    # On a fresh store the throttle has never fired, so the first live write
    # goes straight to disk.
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_skip_word_count_live(20)
    second = SettingsStore(settings_directory=directory)
    assert second.skip_word_count == 20

def test_flush_forces_a_throttled_change_to_disk(tmp_path):
    # The first live write saves; a second one moments later is throttled and
    # stays in memory only (the two calls are microseconds apart, far inside
    # the throttle window). flush() then forces it out, which is what app
    # close relies on.
    directory = str(tmp_path)
    first = SettingsStore(settings_directory=directory)
    first.set_skip_word_count_live(20)  # saved: the throttle has never fired
    first.set_skip_word_count_live(25)  # throttled: in memory only
    assert first.skip_word_count == 25

    before_flush = SettingsStore(settings_directory=directory)
    assert before_flush.skip_word_count == 20  # the throttled change hasn't hit disk yet

    first.flush()
    after_flush = SettingsStore(settings_directory=directory)
    assert after_flush.skip_word_count == 25  # flush forced it out