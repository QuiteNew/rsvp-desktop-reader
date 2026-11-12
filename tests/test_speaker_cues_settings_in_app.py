"""The Configure speaker cues window in the real app: opened from Settings, and
what its Apply does there.

Everything goes through the real windows: Settings is opened, Configure speaker
cues is clicked, the window's controls are changed and Apply is clicked. What
the window itself shows and hands back is tested in test_speaker_cues_window.py,
and what the readers do with the settings in test_speaker_cues_wiring.py.

TEXT's words, by number: Ann:(0) hi there Bob:(3) hello you Cat:(6) just once
Ann:(9) and so Bob:(12) we go. Auto switches Ann and Bob on; Cat starts only
one line."""

import customtkinter as ctk
import pytest

import core.settings_store as settings_store
from gui.components.speaker_cues_window import SpeakerCuesWindow

from tk_helpers import all_widgets, click_button, settle

TEXT = "Ann: hi there\nBob: hello you\nCat: just once\nAnn: and so\nBob: we go"
AUTO_STARTS = (0, 3, 9, 12)


@pytest.fixture
def app(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        app.callback_errors = []
        app.report_callback_exception = lambda *details: app.callback_errors.append(details)
        yield app
        assert app.callback_errors == []


def _add(app, title="Talk", stopped=False):
    transcript = app.store.add_transcript(title, app.store.current_space, wpm=60)
    app.store.set_transcript_text(transcript.id, TEXT)
    app.store.set_transcript_paused(transcript.id, True)
    app.store.set_transcript_stopped(transcript.id, stopped)
    app._refresh_transcript_list()
    settle(app, 100)
    return transcript


def _open(app, transcript):
    app._handle_open_transcript(transcript)
    settle(app, 200)


def _button(window, text):
    (button,) = [w for w in all_widgets(window) if isinstance(w, ctk.CTkButton) and w.cget("text") == text]
    return button


def _open_the_window(app):
    """Open Settings and click Configure speaker cues on its Defaults tab.
    Hands back Settings and the new window."""
    app._open_settings_window()
    settle(app, 300)
    settings = app._settings_window
    settings.tabview.set("Defaults")
    settle(settings, 100)
    click_button(_button(settings, "Configure speaker cues\u2026"))
    settle(app, 300)
    (window,) = [w for w in settings.winfo_children() if isinstance(w, SpeakerCuesWindow)]
    return settings, window


def _apply_and_close(app, settings, window):
    click_button(window.apply_button)
    settle(app, 100)
    click_button(window.close_button)
    settle(app, 200)
    click_button(_button(settings, "Close"))
    settle(app, 200)
    assert not settings.winfo_exists()


def _row(window, key):
    return next(entry for entry in window._row_widgets if entry[0].key == key)


# --- Opening it ---------------------------------------------------------------

def test_it_opens_with_the_saved_settings_and_the_open_transcript(app):
    store = app.settings_store
    store.set_speaker_cues_enabled(True)
    store.set_speaker_cue_flash_enabled(False)
    store.set_speaker_cue_sound("change")
    store.set_speaker_cue_style("soft")
    store.set_speaker_cue_tag_position("top_right")
    transcript = _add(app)
    _open(app, transcript)

    settings, window = _open_the_window(app)

    assert window.enabled_switch.get() == 1
    assert (window.name_tag_check.get(), window.flash_check.get()) == (1, 0)
    assert (window.chosen_sound(), window.chosen_style()) == ("change", "soft")
    assert window.chosen_tag_position() == "top_right"
    assert window._transcript is transcript
    assert [row.key for row, _, _ in window._row_widgets] == ["ann", "bob", "cat"]
    assert window._chime_player is app.chime_player
    _apply_and_close(app, settings, window)


def test_with_nothing_open_it_shows_no_speaker_list(app):
    settings, window = _open_the_window(app)
    assert window._transcript is None
    assert window.list_mode_label is None
    _apply_and_close(app, settings, window)


def test_settings_search_finds_it(app):
    app._open_settings_window()
    settle(app, 300)
    settings = app._settings_window
    try:
        for word in ("speaker", "chime", "interview"):
            settings._defaults_search.set_text(word)
            shown = [
                item.name for item in settings._defaults_items
                if item.searchable and item.holder.winfo_manager() == "pack"
            ]
            assert "Configure speaker cues" in shown, word
    finally:
        settings.destroy()


# --- Apply, for the whole app -------------------------------------------------

def test_apply_saves_the_settings(app):
    settings, window = _open_the_window(app)
    window.enabled_switch.select()
    window.name_tag_check.deselect()
    window.sound_selector.set("Per speaker")
    window.style_selector.set("Glass")
    window.tag_position_selector.set("Top right")

    _apply_and_close(app, settings, window)

    store = app.settings_store
    assert store.speaker_cues_enabled is True
    assert store.speaker_cue_name_tag_enabled is False
    assert store.speaker_cue_flash_enabled is True
    assert store.speaker_cue_sound == "per_speaker"
    assert store.speaker_cue_style == "glass"
    assert store.speaker_cue_tag_position == "top_right", "kept even with the name off"
    # Saved to disk too, not just held in memory.
    saved = settings_store.SettingsStore()
    assert (saved.speaker_cues_enabled, saved.speaker_cue_name_tag_enabled, saved.speaker_cue_sound,
            saved.speaker_cue_style, saved.speaker_cue_tag_position) == (True, False, "per_speaker", "glass", "top_right")


def test_apply_reaches_the_reader_on_screen(app):
    _open(app, _add(app))
    reader = app.canvas.reader_display
    assert reader.session.speaker_turns.starts == ()

    settings, window = _open_the_window(app)
    window.enabled_switch.select()
    window.flash_check.deselect()
    window.style_selector.set("Wood")
    window.tag_position_selector.set("Top right")
    _apply_and_close(app, settings, window)

    assert reader.session.speaker_turns.starts == AUTO_STARTS
    assert (reader._speaker_tag_enabled, reader._speaker_flash_enabled, reader._speaker_style) == (True, False, "wood")
    assert reader._speaker_tag_position == "top_right"


def test_turning_it_off_reaches_the_reader_on_screen(app):
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    _open(app, _add(app))
    reader = app.canvas.reader_display
    assert reader.session.speaker_turns.starts == AUTO_STARTS

    settings, window = _open_the_window(app)
    window.enabled_switch.deselect()
    _apply_and_close(app, settings, window)

    assert reader.session.speaker_turns.starts == ()
    assert app.settings_store.speaker_cues_enabled is False


# --- Apply, for the transcript's speaker list ---------------------------------

def test_apply_saves_the_transcripts_list_and_the_reader_follows(app):
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    transcript = _add(app)
    _open(app, transcript)

    settings, window = _open_the_window(app)
    _row(window, "bob")[1].toggle()
    _row(window, "cat")[1].toggle()
    _row(window, "cat")[2].set("Kat")
    _apply_and_close(app, settings, window)

    assert transcript.speaker_custom == {"ann": "Ann", "cat": "Kat"}
    turns = app.canvas.reader_display.session.speaker_turns
    assert (turns.starts, turns.speakers) == ((0, 6, 9), ("Ann", "Kat", "Ann"))


def test_back_to_automatic_saves_automatic(app):
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    transcript = _add(app)
    app.store.set_transcript_speakers(transcript.id, {"cat": "Kat"})
    _open(app, transcript)
    assert app.canvas.reader_display.session.speaker_turns.starts == (6,)

    settings, window = _open_the_window(app)
    click_button(window.back_to_automatic_button)
    _apply_and_close(app, settings, window)

    assert transcript.speaker_custom is None
    assert app.canvas.reader_display.session.speaker_turns.starts == AUTO_STARTS


def test_the_list_reaches_the_detached_window(app):
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    transcript = _add(app)
    _open(app, transcript)
    app.canvas._handle_detach()
    settle(app, 300)
    detached = app.canvas._detached_window.reader_display

    settings, window = _open_the_window(app)
    _row(window, "ann")[1].toggle()
    _apply_and_close(app, settings, window)

    assert transcript.speaker_custom == {"bob": "Bob"}
    # Bob's second line follows his first with only switched-off names in
    # between, so it isn't a new turn.
    assert detached.session.speaker_turns.starts == (3,)


def test_the_list_reaches_the_detached_window_while_another_is_open_here(app):
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    held = _add(app, "Held")
    other = _add(app, "Other")
    _open(app, held)
    app.canvas._handle_detach()
    settle(app, 300)
    detached = app.canvas._detached_window.reader_display
    _open(app, other)
    main = app.canvas.reader_display

    # The window shows the transcript open here, so it's the one that changes.
    settings, window = _open_the_window(app)
    assert window._transcript is other
    _row(window, "ann")[1].toggle()
    _apply_and_close(app, settings, window)

    assert other.speaker_custom == {"bob": "Bob"}
    assert held.speaker_custom is None
    assert main.session.speaker_turns.starts == (3,)
    assert detached.session.speaker_turns.starts == AUTO_STARTS


def test_a_selection_being_played_follows_the_new_list(app):
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    transcript = _add(app, stopped=True)
    _open(app, transcript)
    # SELECTION's words: there(0) Bob:(1) hello you Ann:(4) and.
    app.canvas.play_selection("there\nBob: hello you\nAnn: and")
    settle(app, 100)
    reader = app.canvas.reader_display
    assert reader.session.speaker_turns.starts == (1, 4)

    settings, window = _open_the_window(app)
    _row(window, "ann")[1].toggle()
    _apply_and_close(app, settings, window)

    assert reader.session.speaker_turns.starts == (1,)


def test_a_selection_being_played_goes_back_to_the_whole_transcripts_automatic_list(app):
    # Automatic for a selection means what Auto finds in the whole transcript,
    # not in the selection alone, where each name is only once (see
    # play_selection()).
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    transcript = _add(app, stopped=True)
    app.store.set_transcript_speakers(transcript.id, {"cat": "Kat"})
    _open(app, transcript)
    app.canvas.play_selection("there\nBob: hello you\nAnn: and")
    settle(app, 100)
    reader = app.canvas.reader_display
    assert reader.session.speaker_turns.starts == ()

    settings, window = _open_the_window(app)
    click_button(window.back_to_automatic_button)
    _apply_and_close(app, settings, window)

    assert reader.session.speaker_turns.starts == (1, 4)


def test_only_the_readers_showing_the_changed_transcript_follow(app):
    # Both lists are changed in the store, but the canvas is told about only
    # one at a time, the way the app tells it after an Apply.
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    held = _add(app, "Held")
    other = _add(app, "Other")
    _open(app, held)
    app.canvas._handle_detach()
    settle(app, 300)
    detached = app.canvas._detached_window.reader_display
    _open(app, other)
    main = app.canvas.reader_display
    app.store.set_transcript_speakers(held.id, {"cat": "Cat"})
    app.store.set_transcript_speakers(other.id, {"bob": "Bob"})

    app.canvas.refresh_transcript_speakers(other.id)
    assert main.session.speaker_turns.starts == (3,)
    assert detached.session.speaker_turns.starts == AUTO_STARTS

    app.canvas.refresh_transcript_speakers(held.id)
    assert main.session.speaker_turns.starts == (3,)
    assert detached.session.speaker_turns.starts == (6,)
    # Main, told about held, must not have picked up held's list either.
    app.store.set_transcript_speakers(other.id, {"ann": "Ann"})
    app.canvas.refresh_transcript_speakers(held.id)
    assert main.session.speaker_turns.starts == (3,)


def test_a_change_made_in_the_edit_box_is_read_when_reading_starts(app):
    app.settings_store.set_speaker_cues_enabled(True)
    app.canvas.set_speaker_cues_enabled(True)
    transcript = _add(app, stopped=True)
    _open(app, transcript)
    assert app.canvas.reader_display.session is None

    settings, window = _open_the_window(app)
    _row(window, "ann")[1].toggle()
    _apply_and_close(app, settings, window)
    app.store.set_transcript_stopped(transcript.id, False)
    _open(app, transcript)

    assert app.canvas.reader_display.session.speaker_turns.starts == (3,)
