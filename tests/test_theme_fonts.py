"""Tests for how gui/theme.py applies the font choice: reading the saved switch,
looking at the fonts folder, and making unstyled widgets follow.

None of these needs a window. They call the theme's own helper functions
instead of re-importing the theme, because the theme settles its constants once
at import and the rest of the test run has already used them. Every test points
the settings and the fonts folder at throwaway folders, so the real settings and
the real fonts are never involved."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from customtkinter import ThemeManager

import core.settings_store as settings_store
from core.font_choice import DYSLEXIA_FONTS, STANDARD_FONTS
from gui import theme

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def settings_dir(tmp_path, monkeypatch):
    """A throwaway settings folder that SettingsStore() with no arguments will
    read from."""
    folder = tmp_path / "settings"
    folder.mkdir()
    monkeypatch.setattr(settings_store, "SETTINGS_DIR", folder)
    return folder


@pytest.fixture
def font_dir(tmp_path, monkeypatch):
    """A throwaway fonts folder, filled by each test as it needs."""
    folder = tmp_path / "fonts"
    folder.mkdir()
    monkeypatch.setattr(theme, "_FONT_DIR", str(folder))
    return folder


def _write_setting(settings_dir, value):
    (settings_dir / "settings.json").write_text(
        json.dumps({"dyslexia_font_enabled": value}), encoding="utf-8")


def _put_files(font_dir, names):
    for name in names:
        (font_dir / name).write_bytes(b"not a real font")


# ---- Which fonts the theme picks ----

def test_a_fresh_install_gets_the_standard_fonts(settings_dir, font_dir):
    _put_files(font_dir, STANDARD_FONTS.files + DYSLEXIA_FONTS.files)
    assert theme._resolve_font_choice() is STANDARD_FONTS

def test_with_the_switch_off_the_standard_fonts_are_used(settings_dir, font_dir):
    _write_setting(settings_dir, False)
    _put_files(font_dir, STANDARD_FONTS.files + DYSLEXIA_FONTS.files)
    assert theme._resolve_font_choice() is STANDARD_FONTS

def test_with_the_switch_on_and_the_files_there_the_dyslexia_fonts_are_used(settings_dir, font_dir):
    _write_setting(settings_dir, True)
    _put_files(font_dir, STANDARD_FONTS.files + DYSLEXIA_FONTS.files)
    assert theme._resolve_font_choice() is DYSLEXIA_FONTS

def test_with_the_switch_on_and_a_file_missing_it_falls_back(settings_dir, font_dir):
    _write_setting(settings_dir, True)
    _put_files(font_dir, STANDARD_FONTS.files + DYSLEXIA_FONTS.files[:1])
    chosen = theme._resolve_font_choice()
    assert chosen.body == STANDARD_FONTS.body
    assert chosen.fell_back is True

def test_with_the_switch_on_and_no_fonts_folder_at_all_it_falls_back(settings_dir, tmp_path, monkeypatch):
    _write_setting(settings_dir, True)
    monkeypatch.setattr(theme, "_FONT_DIR", str(tmp_path / "no such folder"))
    chosen = theme._resolve_font_choice()
    assert chosen.body == STANDARD_FONTS.body
    assert chosen.fell_back is True

def test_a_switch_that_is_not_a_real_true_does_not_turn_the_font_on(settings_dir, font_dir):
    _write_setting(settings_dir, "yes")
    _put_files(font_dir, STANDARD_FONTS.files + DYSLEXIA_FONTS.files)
    assert theme._resolve_font_choice() is STANDARD_FONTS

def test_an_unreadable_settings_file_gets_the_standard_fonts(settings_dir, font_dir):
    (settings_dir / "settings.json").write_text("{ this is not json", encoding="utf-8")
    _put_files(font_dir, STANDARD_FONTS.files + DYSLEXIA_FONTS.files)
    assert theme._resolve_font_choice() is STANDARD_FONTS

def test_a_settings_store_that_fails_to_open_does_not_stop_the_theme(font_dir, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("settings unavailable")
    monkeypatch.setattr(settings_store, "SettingsStore", broken)
    _put_files(font_dir, STANDARD_FONTS.files + DYSLEXIA_FONTS.files)
    assert theme._resolve_font_choice() is STANDARD_FONTS


# ---- Widgets that set no font ----

def test_the_dyslexia_fonts_become_the_default_for_widgets_with_no_font(monkeypatch):
    monkeypatch.setitem(ThemeManager.theme["CTkFont"], "family", "Roboto")
    theme._apply_default_font_family(DYSLEXIA_FONTS)
    assert ThemeManager.theme["CTkFont"]["family"] == DYSLEXIA_FONTS.body

def test_the_standard_fonts_leave_the_default_alone(monkeypatch):
    monkeypatch.setitem(ThemeManager.theme["CTkFont"], "family", "Roboto")
    theme._apply_default_font_family(STANDARD_FONTS)
    assert ThemeManager.theme["CTkFont"]["family"] == "Roboto"

def test_a_fallback_leaves_the_default_alone(monkeypatch):
    monkeypatch.setitem(ThemeManager.theme["CTkFont"], "family", "Roboto")
    theme._apply_default_font_family(theme.choose_fonts(True, []))
    assert ThemeManager.theme["CTkFont"]["family"] == "Roboto"


# ---- The files that get registered ----

def test_the_font_paths_are_the_files_of_the_current_choice(font_dir, monkeypatch):
    _put_files(font_dir, STANDARD_FONTS.files + DYSLEXIA_FONTS.files)
    monkeypatch.setattr(theme, "FONT_CHOICE", DYSLEXIA_FONTS)
    assert theme._font_paths() == [str(font_dir / name) for name in DYSLEXIA_FONTS.files]
    monkeypatch.setattr(theme, "FONT_CHOICE", STANDARD_FONTS)
    assert theme._font_paths() == [str(font_dir / name) for name in STANDARD_FONTS.files]

def test_a_font_file_that_is_not_there_is_skipped(font_dir, monkeypatch):
    _put_files(font_dir, DYSLEXIA_FONTS.files[:1])
    monkeypatch.setattr(theme, "FONT_CHOICE", DYSLEXIA_FONTS)
    assert theme._font_paths() == [str(font_dir / DYSLEXIA_FONTS.files[0])]

def test_no_font_paths_when_the_folder_is_empty(font_dir, monkeypatch):
    monkeypatch.setattr(theme, "FONT_CHOICE", STANDARD_FONTS)
    assert theme._font_paths() == []


# ---- The names every component imports ----

def test_the_theme_exposes_the_names_the_components_import():
    assert theme.FONT_HEADING == theme.FONT_CHOICE.heading
    assert theme.FONT_BODY == theme.FONT_CHOICE.body
    assert theme.DYSLEXIA_FONT_ACTIVE == theme.FONT_CHOICE.dyslexia_friendly
    assert theme.DYSLEXIA_FONT_FELL_BACK == theme.FONT_CHOICE.fell_back

def test_the_heading_and_body_names_are_one_of_the_two_known_sets():
    assert (theme.FONT_HEADING, theme.FONT_BODY) in (
        (STANDARD_FONTS.heading, STANDARD_FONTS.body),
        (DYSLEXIA_FONTS.heading, DYSLEXIA_FONTS.body),
    )


# ---- Import time, end to end ----
# The theme settles its fonts when it is first imported, and by the time any test
# runs it already has been. So this part runs the import in a fresh Python
# process with its own home folder, holding whatever settings file the test
# wrote, and reports what the theme came up with.

_IMPORT_THEME = """
import sys
sys.path.insert(0, sys.argv[1])
from customtkinter import ThemeManager
before = ThemeManager.theme["CTkFont"]["family"]
from gui import theme
print(theme.FONT_HEADING)
print(theme.FONT_BODY)
print(before)
print(ThemeManager.theme["CTkFont"]["family"])
"""


def _import_theme_with_setting(tmp_path, value):
    home = tmp_path / "home"
    (home / ".rsvp_reader").mkdir(parents=True)
    if value is not None:
        (home / ".rsvp_reader" / "settings.json").write_text(
            json.dumps({"dyslexia_font_enabled": value}), encoding="utf-8")
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_THEME, str(PROJECT_ROOT)],
        capture_output=True, text=True, env=env, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    heading, body, family_before, family_after = result.stdout.splitlines()
    return heading, body, family_before, family_after

def test_importing_the_theme_with_the_switch_on_applies_the_dyslexia_fonts_everywhere(tmp_path):
    heading, body, family_before, family_after = _import_theme_with_setting(tmp_path, True)
    assert heading == DYSLEXIA_FONTS.heading
    assert body == DYSLEXIA_FONTS.body
    assert family_before != DYSLEXIA_FONTS.body
    assert family_after == DYSLEXIA_FONTS.body

def test_importing_the_theme_with_the_switch_off_keeps_the_standard_fonts(tmp_path):
    heading, body, family_before, family_after = _import_theme_with_setting(tmp_path, False)
    assert heading == STANDARD_FONTS.heading
    assert body == STANDARD_FONTS.body
    assert family_after == family_before

def test_importing_the_theme_with_no_settings_file_keeps_the_standard_fonts(tmp_path):
    heading, body, family_before, family_after = _import_theme_with_setting(tmp_path, None)
    assert (heading, body) == (STANDARD_FONTS.heading, STANDARD_FONTS.body)
    assert family_after == family_before