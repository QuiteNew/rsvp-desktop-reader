"""Tests for reopening the last transcript at launch: the choice in
core/reopen.py, the two settings it needs (core/settings_store.py), the app's
side of it (gui/app.py) and the switch on the Defaults tab of Settings.

What was agreed: when the app starts, it opens the transcript that was open
when it was last closed, as a Settings switch that is on by default. On top of
that: the transcript always comes back paused, so nothing starts playing on its
own, and it comes back at the same word; one left in the edit box comes back in
the edit box. Nothing is opened when the switch is off or the transcript is
gone."""

from dataclasses import asdict

import customtkinter as ctk
import pytest

from core.models import Transcript
from core.reopen import transcript_to_reopen
from core.settings_store import AppSettings, SettingsStore
from core.transcript_store import TranscriptStore


# ---- which transcript (core/reopen.py) ----

TRANSCRIPTS = [
    Transcript(id=1, title="Lecture", space="General"),
    Transcript(id=2, title="Notes", space="Work"),
]


def test_the_last_transcript_is_chosen():
    assert transcript_to_reopen(True, 1, TRANSCRIPTS) is TRANSCRIPTS[0]


def test_a_transcript_in_another_space_is_chosen_too():
    """The app keeps a transcript open across a switch of space, so it comes
    back the same way."""
    assert transcript_to_reopen(True, 2, TRANSCRIPTS) is TRANSCRIPTS[1]


def test_nothing_when_the_setting_is_off():
    assert transcript_to_reopen(False, 1, TRANSCRIPTS) is None


def test_nothing_when_nothing_was_open():
    assert transcript_to_reopen(True, None, TRANSCRIPTS) is None


def test_nothing_when_the_transcript_is_gone():
    assert transcript_to_reopen(True, 99, TRANSCRIPTS) is None


# ---- the two settings (core/settings_store.py) ----

@pytest.fixture
def settings(tmp_path):
    return SettingsStore(str(tmp_path / "settings"))


def test_reopening_is_on_by_default(settings):
    assert AppSettings().reopen_last_transcript is True
    assert settings.reopen_last_transcript is True
    assert settings.last_transcript_id is None


def test_both_settings_are_saved_and_survive_a_restart(settings, tmp_path):
    settings.set_reopen_last_transcript(False)
    settings.set_last_transcript_id(7)
    again = SettingsStore(str(tmp_path / "settings"))
    assert again.reopen_last_transcript is False
    assert again.last_transcript_id == 7


def test_forgetting_the_last_transcript_is_saved(settings, tmp_path):
    settings.set_last_transcript_id(7)
    settings.set_last_transcript_id(None)
    assert SettingsStore(str(tmp_path / "settings")).last_transcript_id is None


@pytest.mark.parametrize("odd", ["3", 2.5, True, [3]])
def test_an_odd_id_in_the_file_reads_as_none(settings, odd):
    settings._settings.last_transcript_id = odd
    assert settings.last_transcript_id is None


@pytest.mark.parametrize("odd", ["no", 0, None])
def test_an_odd_switch_value_in_the_file_keeps_the_default_on(settings, odd):
    settings._settings.reopen_last_transcript = odd
    assert settings.reopen_last_transcript is True


def test_opening_the_same_transcript_again_does_not_write_the_file(settings, monkeypatch):
    settings.set_last_transcript_id(7)
    writes = []
    monkeypatch.setattr(settings, "_save", lambda: writes.append(1))
    settings.set_last_transcript_id(7)
    assert writes == []


def test_an_old_settings_file_without_them_gets_the_defaults(tmp_path):
    folder = tmp_path / "settings"
    folder.mkdir()
    (folder / "settings.json").write_text('{"default_wpm": 350}', encoding="utf-8")
    store = SettingsStore(str(folder))
    assert store.default_wpm == 350
    assert store.reopen_last_transcript is True
    assert store.last_transcript_id is None


# ---- the app (gui/app.py) ----

class Anything:
    """Stands in for any part of the app: every attribute is another stand-in,
    and every call is remembered with its arguments."""

    def __init__(self, name="app"):
        self.name = name
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        part = Anything(name)
        object.__setattr__(self, name, part)
        return part

    def __call__(self, *args):
        self.calls.append(args)


def app_with_stores(tmp_path):
    """A stand-in app with real stores, so what gets saved can be checked."""
    app = Anything()
    app.settings_store = SettingsStore(str(tmp_path / "settings"))
    app.store = TranscriptStore(data_directory=str(tmp_path / "data"))
    return app


def add(app, title, text="one two three four five", paused=False, stopped=False, position=0):
    transcript = app.store.add_transcript(
        title, app.store.current_space, wpm=300, font_color="#000000",
        highlight_color="#FF0000", background_color="#FFFFFF", font_size=40,
    )
    app.store.set_transcript_text(transcript.id, text)
    app.store.set_transcript_paused(transcript.id, paused)
    app.store.set_transcript_stopped(transcript.id, stopped)
    app.store.set_transcript_position(transcript.id, position)
    return transcript


def test_opening_a_transcript_remembers_it(tmp_path):
    from gui.app import RSVPApp

    app = app_with_stores(tmp_path)
    transcript = add(app, "Lecture")
    RSVPApp._handle_open_transcript(app, transcript)
    assert app.settings_store.last_transcript_id == transcript.id


def test_deleting_the_remembered_transcript_forgets_it(tmp_path):
    from gui.app import RSVPApp

    app = app_with_stores(tmp_path)
    transcript = add(app, "Lecture")
    app.settings_store.set_last_transcript_id(transcript.id)
    app._current_transcript = transcript
    RSVPApp._handle_delete_confirmed(app, transcript)
    assert app.settings_store.last_transcript_id is None


def test_deleting_another_transcript_keeps_it(tmp_path):
    from gui.app import RSVPApp

    app = app_with_stores(tmp_path)
    kept = add(app, "Lecture")
    other = add(app, "Notes")
    app.settings_store.set_last_transcript_id(kept.id)
    app._current_transcript = kept
    RSVPApp._handle_delete_confirmed(app, other)
    assert app.settings_store.last_transcript_id == kept.id


def reopen(app):
    """Run the app's launch step on the stand-in, recording what it opens."""
    from gui.app import RSVPApp

    opened = []
    app._handle_open_transcript = lambda transcript: opened.append(transcript)
    RSVPApp._reopen_last_transcript(app)
    return opened


def test_a_transcript_left_playing_comes_back_paused_at_the_same_word(tmp_path):
    app = app_with_stores(tmp_path)
    transcript = add(app, "Lecture", paused=False, position=3)
    app.settings_store.set_last_transcript_id(transcript.id)

    opened = reopen(app)

    assert [t.id for t in opened] == [transcript.id]
    assert opened[0].is_paused is True
    assert opened[0].position == 3
    reloaded = TranscriptStore(data_directory=str(tmp_path / "data")).transcripts[0]
    assert reloaded.is_paused is True, "the pause was not saved"


def test_a_transcript_left_in_the_edit_box_comes_back_there(tmp_path):
    app = app_with_stores(tmp_path)
    transcript = add(app, "Lecture", stopped=True)
    app.settings_store.set_last_transcript_id(transcript.id)

    opened = reopen(app)

    assert [t.id for t in opened] == [transcript.id]
    assert opened[0].is_stopped is True
    assert opened[0].is_paused is False


def test_nothing_is_opened_when_the_switch_is_off(tmp_path):
    app = app_with_stores(tmp_path)
    transcript = add(app, "Lecture")
    app.settings_store.set_last_transcript_id(transcript.id)
    app.settings_store.set_reopen_last_transcript(False)
    assert reopen(app) == []


def test_nothing_is_opened_when_the_transcript_is_gone(tmp_path):
    app = app_with_stores(tmp_path)
    app.settings_store.set_last_transcript_id(42)
    assert reopen(app) == []


def test_apply_saves_the_switch(tmp_path):
    from gui.app import RSVPApp

    app = Anything()
    values = asdict(AppSettings())
    values["reopen_last_transcript"] = False
    RSVPApp._handle_settings_applied(app, values)
    assert app.settings_store.set_reopen_last_transcript.calls == [(False,)]


# ---- the switch in Settings ----


@pytest.fixture
def open_settings(root, wait_until_shown):
    """Opens Settings with the switch set as given, and returns the window and
    a list of what Apply sent."""
    from gui.components.settings_window import SettingsWindow

    windows = []

    def build(reopen_last_transcript):
        owner = ctk.CTkToplevel(root)
        owner.geometry("600x700+0+0")
        wait_until_shown(owner)
        defaults = asdict(AppSettings())
        names = (
            "window_width", "window_height", "sidebar_width", "bottom_band_height",
            "freeform_resize_enabled", "default_wpm", "default_font_color",
            "default_highlight_color", "default_background_color", "default_font_size",
            "font_size_step", "highlight_offset_px", "skip_word_count", "pause_on_skip",
            "length_pacing_enabled", "split_long_paragraphs_enabled", "resume_rewind_enabled",
            "resume_rewind_words", "warm_up_enabled", "scrub_pause_enabled",
            "peripheral_context_enabled", "guide_mark_horizontal_enabled",
            "guide_mark_thickness_px", "guide_mark_length_percent", "guide_mark_color",
            "data_directory", "appearance_mode", "dyslexia_font_enabled", "letter_spacing_level",
        )
        applied = []
        nothing = lambda *args: None
        window = SettingsWindow(
            owner, **{name: defaults[name] for name in names},
            transcripts=[], on_apply=applied.append,
            on_export_requested=nothing, on_import_requested=nothing,
            profile_names=lambda: [], on_profile_save=nothing, on_profile_update=nothing,
            on_profile_apply=nothing, on_profile_rename=nothing, on_profile_delete=nothing,
            reopen_last_transcript=reopen_last_transcript,
        )
        wait_until_shown(window)
        windows.append((window, owner))
        return window, applied

    yield build
    for window, owner in windows:
        if window.winfo_exists():
            for timer in window.tk.splitlist(window.tk.call("after", "info")):
                window.tk.call("after", "cancel", timer)
            window.destroy()
        owner.destroy()


@pytest.mark.parametrize("on", [True, False])
def test_the_switch_shows_the_saved_value_and_apply_sends_it(open_settings, on):
    window, applied = open_settings(on)
    assert bool(window.reopen_last_transcript_switch.get()) is on
    assert window._handle_apply() is True
    assert applied[-1]["reopen_last_transcript"] is on


def test_reset_to_original_defaults_turns_it_back_on(open_settings):
    window, applied = open_settings(False)
    window._handle_reset_defaults()
    assert bool(window.reopen_last_transcript_switch.get()) is True


def test_the_switch_can_be_found_by_searching(open_settings):
    window, _ = open_settings(True)
    window._defaults_search.set_text("launch")
    window.update()
    shown = [item.name for item in window._defaults_items if item.holder.winfo_manager() == "pack" and item.searchable]
    assert "Reopen the last transcript at launch" in shown
