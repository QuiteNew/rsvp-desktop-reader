"""Tests for how a transcript's reading colours follow the Light and Dark theme
(gui/app.py, _current_theme_reading_colors() and _resync_theme_default_colors()).

The Appearance tab explains this to the person, and it used to say the opposite:
that a new transcript's colours come from the Defaults tab and won't match the
theme. In Dark they don't come from the Defaults tab at all. These tests pin down
what the note now says:

- A new transcript gets the Defaults tab colours in Light and the app's dark
  reading colours in Dark.
- At every launch, each colour that wasn't picked by hand is brought in line
  with the theme again, so it follows a change of theme, and in Light a change
  of the Defaults tab colours too.
- A colour picked by hand stays the same in both themes.

A launch is played without building the window: the app's own two methods run
on a small stand-in with real stores, the way RSVPApp.__init__ calls them."""

import types

import pytest

from gui.theme import (
    DARK_READING_BACKGROUND_COLOR, DARK_READING_FONT_COLOR, DARK_READING_HIGHLIGHT_COLOR,
)

DARK = (DARK_READING_FONT_COLOR, DARK_READING_HIGHLIGHT_COLOR, DARK_READING_BACKGROUND_COLOR)
LIGHT_DEFAULTS = ("#111111", "#222222", "#333333")
NEW_LIGHT_DEFAULTS = ("#444444", "#555555", "#666666")
PICKED = "#ABCDEF"


@pytest.fixture
def launch(tmp_path, monkeypatch):
    """Starts the app's colour handling in a theme, on stores kept in tmp_path,
    and returns the stand-in. Calling it again is the next launch."""
    import gui.app
    from core.settings_store import SettingsStore
    from core.transcript_store import TranscriptStore

    def start(mode):
        monkeypatch.setattr(gui.app, "CTK_APPEARANCE_MODE", mode)
        app = types.SimpleNamespace(
            settings_store=SettingsStore(str(tmp_path / "settings")),
            store=TranscriptStore(data_directory=str(tmp_path / "data")),
        )
        app._current_theme_reading_colors = lambda: gui.app.RSVPApp._current_theme_reading_colors(app)
        app._theme_guide_mark_color = lambda: gui.app.RSVPApp._theme_guide_mark_color(app)
        gui.app.RSVPApp._resync_theme_default_colors(app)
        return app

    return start


def set_defaults(app, colours):
    font, highlight, background = colours
    app.settings_store.set_defaults(300, font, highlight, background, 40)
    app.settings_store.flush()


def new_transcript(app, title):
    """Adds a transcript the way the app does, with the colours the current
    theme gives a new one."""
    font, highlight, background = app._current_theme_reading_colors()
    transcript = app.store.add_transcript(
        title, app.store.current_space, wpm=300,
        font_color=font, highlight_color=highlight, background_color=background, font_size=40,
    )
    app.store.flush()
    return transcript


def colours(transcript):
    return transcript.font_color, transcript.highlight_color, transcript.background_color


def by_title(app, title):
    return next(t for t in app.store.transcripts if t.title == title)


# ---- a new transcript ----

def test_in_light_a_new_transcript_gets_the_defaults_tab_colours(launch):
    app = launch("Light")
    set_defaults(app, LIGHT_DEFAULTS)
    assert colours(new_transcript(app, "new")) == LIGHT_DEFAULTS


def test_in_dark_a_new_transcript_gets_the_dark_reading_colours_not_the_defaults_tab(launch):
    app = launch("Dark")
    set_defaults(app, LIGHT_DEFAULTS)
    assert colours(new_transcript(app, "new")) == DARK


# ---- at the next launch ----

def test_colours_not_picked_by_hand_follow_a_change_to_dark(launch):
    app = launch("Light")
    set_defaults(app, LIGHT_DEFAULTS)
    new_transcript(app, "follows")

    assert colours(by_title(launch("Dark"), "follows")) == DARK


def test_colours_not_picked_by_hand_come_back_to_the_defaults_tab_in_light(launch):
    app = launch("Dark")
    set_defaults(app, LIGHT_DEFAULTS)
    new_transcript(app, "follows")

    assert colours(by_title(launch("Light"), "follows")) == LIGHT_DEFAULTS


def test_in_light_a_change_to_the_defaults_tab_colours_reaches_them_at_the_next_launch(launch):
    app = launch("Light")
    set_defaults(app, LIGHT_DEFAULTS)
    new_transcript(app, "follows")
    set_defaults(app, NEW_LIGHT_DEFAULTS)

    assert colours(by_title(launch("Light"), "follows")) == NEW_LIGHT_DEFAULTS


def test_nothing_changes_before_the_next_launch(launch):
    app = launch("Light")
    set_defaults(app, LIGHT_DEFAULTS)
    transcript = new_transcript(app, "follows")
    set_defaults(app, NEW_LIGHT_DEFAULTS)
    assert colours(transcript) == LIGHT_DEFAULTS


# ---- a colour picked by hand ----

@pytest.mark.parametrize("first, then", [("Light", "Dark"), ("Dark", "Light"), ("Light", "Light")])
def test_a_colour_picked_by_hand_stays_the_same_in_both_themes(launch, first, then):
    app = launch(first)
    set_defaults(app, LIGHT_DEFAULTS)
    transcript = new_transcript(app, "picked")
    app.store.set_transcript_font_color(transcript.id, PICKED)
    app.store.flush()
    set_defaults(app, NEW_LIGHT_DEFAULTS)

    assert by_title(launch(then), "picked").font_color == PICKED


def test_each_colour_follows_on_its_own(launch):
    """Picking the font colour by hand doesn't stop the highlight and the
    background from following the theme."""
    app = launch("Light")
    set_defaults(app, LIGHT_DEFAULTS)
    transcript = new_transcript(app, "picked")
    app.store.set_transcript_font_color(transcript.id, PICKED)
    app.store.flush()

    assert colours(by_title(launch("Dark"), "picked")) == (PICKED, DARK[1], DARK[2])