import json
import pytest
from core.settings_store import SettingsStore, AppSettings


@pytest.fixture
def store(tmp_path):
    """A fresh SettingsStore backed by a unique, disposable temporary
    directory — never touches your real ~/.rsvp_reader/settings.json."""
    return SettingsStore(settings_directory=str(tmp_path))


# ---- Fresh store: every property matches AppSettings' own defaults ----
# Reading from a live AppSettings() instance, rather than hardcoding
# numbers a second time here, means these can never silently drift out
# of sync with the dataclass itself.

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


# ---- set_window_size ----

def test_set_window_size_updates_both_dimensions(store):
    store.set_window_size(1200, 800)
    assert store.window_width == 1200
    assert store.window_height == 800

def test_set_window_size_does_not_affect_other_settings(store):
    store.set_window_size(1200, 800)
    assert store.sidebar_width == AppSettings().sidebar_width
    assert store.appearance_mode == AppSettings().appearance_mode


# ---- set_layout_sizes ----

def test_set_layout_sizes_updates_both_values(store):
    store.set_layout_sizes(300, 150)
    assert store.sidebar_width == 300
    assert store.bottom_band_height == 150

def test_set_layout_sizes_does_not_affect_window_size(store):
    store.set_window_size(1200, 800)
    store.set_layout_sizes(300, 150)
    assert store.window_width == 1200
    assert store.window_height == 800


# ---- set_defaults ----

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


# ---- set_data_directory ----

def test_set_data_directory_updates_value(store):
    store.set_data_directory("/some/new/path")
    assert store.data_directory == "/some/new/path"


# ---- set_freeform_resize_enabled ----

def test_set_freeform_resize_enabled_true(store):
    store.set_freeform_resize_enabled(True)
    assert store.freeform_resize_enabled is True

def test_set_freeform_resize_enabled_false(store):
    store.set_freeform_resize_enabled(True)
    store.set_freeform_resize_enabled(False)
    assert store.freeform_resize_enabled is False


# ---- set_skip_behavior ----

def test_set_skip_behavior_updates_both_values(store):
    store.set_skip_behavior(25, True)
    assert store.skip_word_count == 25
    assert store.pause_on_skip is True

def test_set_skip_behavior_does_not_affect_defaults(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_skip_behavior(25, True)
    assert store.default_wpm == 500


# ---- set_appearance_mode ----

def test_set_appearance_mode_light(store):
    store.set_appearance_mode("light")
    assert store.appearance_mode == "light"

def test_set_appearance_mode_dark(store):
    store.set_appearance_mode("dark")
    assert store.appearance_mode == "dark"

def test_set_appearance_mode_system(store):
    store.set_appearance_mode("system")
    assert store.appearance_mode == "system"


# ---- Persistence ----

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
    """Simulates upgrading from an older version of the app whose
    settings.json was written before some fields (e.g. appearance_mode)
    existed. A dataclass happily fills in missing keys with its own
    defaults — this confirms that promise actually holds, not just in
    theory."""
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
    """header_height was removed from AppSettings entirely after the
    header-resize investigation, but real settings.json files written
    before that point still have it saved on disk. Passing an unexpected
    keyword straight into AppSettings(**data) would raise a TypeError —
    this uses a value AppSettings would reject if the explicit
    data.pop("header_height", None) migration step weren't in place,
    confirming it actually works rather than just assuming it does."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({
        "window_width": 1000,
        "window_height": 650,
        "header_height": 80,  # stale field, no longer a real AppSettings attribute
    }), encoding="utf-8")

    store = SettingsStore(settings_directory=str(tmp_path))  # must not raise TypeError
    assert store.window_width == 1000
    assert store.window_height == 650


# ---- Isolation between separate settings directories ----

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


# ---- No-argument constructor still works (backward compatibility) ----

def test_no_argument_constructor_still_works():
    """SettingsStore() with zero arguments must keep working exactly as
    before — gui/app.py and gui/theme.py both call it this way. This
    test intentionally reads from the REAL ~/.rsvp_reader/settings.json
    (there's no way to verify default behavior without touching it at
    least once) — but it only ever reads, via the constructor. It never
    calls a single setter, so it cannot overwrite anything real."""
    store = SettingsStore()
    assert isinstance(store.appearance_mode, str)
    assert isinstance(store.window_width, int)


# ---- Tests below were added when the font resize amount mechanic was added in settings

def test_fresh_store_font_size_step_matches_defaults(store):
    assert store.font_size_step == AppSettings().font_size_step

def test_set_font_size_step_updates_value(store):
    store.set_font_size_step(5)
    assert store.font_size_step == 5

def test_set_font_size_step_does_not_affect_other_settings(store):
    store.set_defaults(500, "#111111", "#222222", "#333333", 32)
    store.set_font_size_step(5)
    assert store.default_wpm == 500