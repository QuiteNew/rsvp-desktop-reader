"""Speaker cues wired through the app: the settings reach every reader the app
builds (the main window's, the detached window's and a selection preview's),
each one reads with the right speaker list, and the app's one chime player is
shared by all of them and closed with the app.

What each reader does with the settings is tested in
test_reader_display_speaker_cues.py, and the speaker lists themselves in
test_speakers.py and test_whole_transcript_speakers.py. Everything here runs on
the real app, built with open_real_app from conftest.py. Saved settings are
written before the app is built, so the app has to read them at start.

A played selection (right-click Play) and a detached one (right-click Detach)
are started by calling the methods the right-click menu calls, play_selection()
and open_selection_preview(). The menu itself is tested in
test_selection_preview.py and test_detach_selection.py.

TEXT's words, by number: Ann:(0) hi there Bob:(3) hello you Cat:(6) just once
Ann:(9) and so Bob:(12) we go. Ann and Bob start two lines each, so Auto
switches them on. Cat starts only one, so Auto leaves her off.

SELECTION's words: there(0) Bob:(1) hello you Ann:(4) and. Each name is in it
only once, so on its own Auto would find no speakers in it at all."""

import core.settings_store as settings_store

from tk_helpers import click_button, settle

TEXT = "Ann: hi there\nBob: hello you\nCat: just once\nAnn: and so\nBob: we go"
SELECTION = "there\nBob: hello you\nAnn: and"
AUTO_STARTS = (0, 3, 9, 12)


def _saved(cues=True, name_tag=True, flash=True, sound="off", style="bell"):
    """A before_start for open_real_app that saves these speaker cue settings."""
    def save():
        store = settings_store.SettingsStore()
        store.set_speaker_cues_enabled(cues)
        store.set_speaker_cue_name_tag_enabled(name_tag)
        store.set_speaker_cue_flash_enabled(flash)
        store.set_speaker_cue_sound(sound)
        store.set_speaker_cue_style(style)
    return save


def _add(app, title="Talk", text=TEXT, custom=None, stopped=False):
    """A transcript of text, paused so nothing moves while a test looks, and
    left in the edit box when stopped is True. custom is its own speaker list
    (None for Auto)."""
    transcript = app.store.add_transcript(title, app.store.current_space, wpm=60)
    app.store.set_transcript_text(transcript.id, text)
    app.store.set_transcript_paused(transcript.id, True)
    app.store.set_transcript_stopped(transcript.id, stopped)
    if custom is not None:
        app.store.set_transcript_speakers(transcript.id, custom)
    app._refresh_transcript_list()
    settle(app, 100)
    return transcript


def _open(app, transcript):
    app._handle_open_transcript(transcript)
    settle(app, 200)


def _detach(app):
    app.canvas._handle_detach()
    settle(app, 300)
    return app.canvas._detached_window


def _look(reader):
    """The speaker cue look a reader was given: name tag, flash, sound, style."""
    return (reader._speaker_tag_enabled, reader._speaker_flash_enabled, reader._speaker_sound, reader._speaker_style)


def _starts(reader):
    return reader.session.speaker_turns.starts


# --- The main window ----------------------------------------------------------

def test_the_app_starts_with_the_saved_settings(tmp_path, open_real_app):
    # The name tag off and the flash on, so mixing the two up shows.
    saved = _saved(cues=True, name_tag=False, flash=True, sound="per_speaker", style="glass")
    with open_real_app(tmp_path, before_start=saved) as app:
        _open(app, _add(app))

        reader = app.canvas.reader_display
        assert _look(reader) == (False, True, "per_speaker", "glass")
        assert reader._chime_player is app.chime_player
        assert reader.session.speaker_cues_enabled is True
        assert _starts(reader) == AUTO_STARTS


def test_with_nothing_saved_there_are_no_cues(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        _open(app, _add(app))

        reader = app.canvas.reader_display
        assert _look(reader) == (True, True, "off", "bell")
        assert reader._chime_player is app.chime_player
        assert reader.session.speaker_cues_enabled is False
        assert _starts(reader) == ()


def test_the_transcripts_own_list_is_used(tmp_path, open_real_app):
    with open_real_app(tmp_path, before_start=_saved()) as app:
        _open(app, _add(app, custom={"cat": "Cat"}))

        turns = app.canvas.reader_display.session.speaker_turns
        assert turns.starts == (6,)
        assert turns.speakers == ("Cat",)


def test_turning_cues_on_and_off_works_on_the_reader_on_screen(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _add(app, custom={"cat": "Cat"})
        app.store.set_transcript_position(transcript.id, 7)
        _open(app, transcript)
        reader = app.canvas.reader_display
        session = reader.session

        app.canvas.set_speaker_cues_enabled(True)
        assert reader.session is session, "the same session, worked out again in place"
        assert _starts(reader) == (6,), "with the transcript's own list"
        assert session.index == 7

        app.canvas.set_speaker_cues_enabled(False)
        assert _starts(reader) == ()
        assert session.index == 7


def test_the_look_reaches_the_reader_on_screen(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        _open(app, _add(app))

        app.canvas.set_speaker_cue_options(True, False, "change", "wood")

        assert _look(app.canvas.reader_display) == (True, False, "change", "wood")


def test_a_reader_opened_after_a_change_uses_it(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _add(app)

        app.canvas.set_speaker_cues_enabled(True)
        app.canvas.set_speaker_cue_options(False, True, "change", "glass")
        _open(app, transcript)

        reader = app.canvas.reader_display
        assert _starts(reader) == AUTO_STARTS
        assert _look(reader) == (False, True, "change", "glass")


# --- The detached window ------------------------------------------------------

def test_the_detached_window_reads_with_the_settings_and_the_transcripts_list(tmp_path, open_real_app):
    saved = _saved(cues=True, name_tag=False, flash=True, sound="change", style="soft")
    with open_real_app(tmp_path, before_start=saved) as app:
        _open(app, _add(app, custom={"cat": "Cat"}))

        reader = _detach(app).reader_display

        assert _look(reader) == (False, True, "change", "soft")
        assert reader._chime_player is app.chime_player
        assert reader.session.speaker_cues_enabled is True
        assert _starts(reader) == (6,)


def test_changes_reach_the_detached_window_whichever_transcript_it_holds(tmp_path, open_real_app):
    with open_real_app(tmp_path, before_start=_saved()) as app:
        held = _add(app, "Held", custom={"cat": "Cat"})
        other = _add(app, "Other")
        _open(app, held)
        detached = _detach(app).reader_display
        _open(app, other)
        main = app.canvas.reader_display

        app.canvas.set_speaker_cues_enabled(False)
        assert (_starts(main), _starts(detached)) == ((), ())

        app.canvas.set_speaker_cues_enabled(True)
        assert _starts(main) == AUTO_STARTS
        assert _starts(detached) == (6,), "the detached window keeps its own transcript's list"

        app.canvas.set_speaker_cue_options(False, True, "per_speaker", "wood")
        assert _look(main) == _look(detached) == (False, True, "per_speaker", "wood")


def test_a_change_reaches_a_detached_window_that_starts_reading_later(tmp_path, open_real_app):
    # Detached while in the edit box, so its reader is only built when Start
    # reading is clicked there, after the change.
    with open_real_app(tmp_path) as app:
        _open(app, _add(app, stopped=True))
        window = _detach(app)

        app.canvas.set_speaker_cues_enabled(True)
        click_button(window.input_view.start_button)
        settle(window, 200)

        assert _starts(window.reader_display) == AUTO_STARTS


def test_a_window_detached_after_a_change_gets_it(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        _open(app, _add(app))

        app.canvas.set_speaker_cues_enabled(True)
        app.canvas.set_speaker_cue_options(False, True, "per_speaker", "glass")
        reader = _detach(app).reader_display

        assert _starts(reader) == AUTO_STARTS
        assert _look(reader) == (False, True, "per_speaker", "glass")


# --- A played selection (right-click Play) ------------------------------------

def test_a_played_selection_reads_with_the_whole_transcripts_list(tmp_path, open_real_app):
    with open_real_app(tmp_path, before_start=_saved()) as app:
        _open(app, _add(app, stopped=True))

        app.canvas.play_selection(SELECTION)
        settle(app, 100)

        turns = app.canvas.reader_display.session.speaker_turns
        assert turns.starts == (1, 4)
        assert turns.speakers == ("Bob", "Ann")
        assert turns.speaker_at(0) is None, "no name before the selection's first label"


def test_the_list_comes_from_the_edit_box_as_it_is_now(tmp_path, open_real_app):
    # A second Cat line typed into the box and not saved yet makes Cat a
    # speaker, since the selection was taken from the box.
    with open_real_app(tmp_path, before_start=_saved()) as app:
        _open(app, _add(app, stopped=True))
        app.canvas.input_view.set_text(TEXT + "\nCat: twice now")
        settle(app, 100)

        app.canvas.play_selection("Cat: just once\nAnn: and")
        settle(app, 100)

        assert app.canvas.reader_display.session.speaker_turns.speakers == ("Cat", "Ann")


def test_a_played_selection_uses_the_transcripts_own_list(tmp_path, open_real_app):
    with open_real_app(tmp_path, before_start=_saved()) as app:
        _open(app, _add(app, stopped=True, custom={"ann": "Annie"}))

        app.canvas.play_selection(SELECTION)
        settle(app, 100)

        turns = app.canvas.reader_display.session.speaker_turns
        assert (turns.starts, turns.speakers) == ((4,), ("Annie",))


def test_turning_cues_on_during_a_played_selection_keeps_the_whole_list(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        _open(app, _add(app, stopped=True))
        app.canvas.play_selection(SELECTION)
        settle(app, 100)
        assert _starts(app.canvas.reader_display) == ()

        app.canvas.set_speaker_cues_enabled(True)

        assert _starts(app.canvas.reader_display) == (1, 4)


# --- A detached selection (right-click Detach) --------------------------------

def _preview(app):
    """Detach SELECTION into its own window and start reading it."""
    app.canvas.open_selection_preview(SELECTION)
    settle(app, 300)
    window = app.canvas._selection_previews[-1][0]
    click_button(window.input_view.start_button)
    settle(window, 200)
    return window.reader_display


def test_a_detached_selection_reads_with_the_whole_list_and_the_look(tmp_path, open_real_app):
    saved = _saved(cues=True, name_tag=False, flash=True, sound="per_speaker", style="wood")
    with open_real_app(tmp_path, before_start=saved) as app:
        _open(app, _add(app, stopped=True))

        reader = _preview(app)

        assert reader.session.speaker_cues_enabled is True
        assert _starts(reader) == (1, 4)
        assert _look(reader) == (False, True, "per_speaker", "wood")
        assert reader._chime_player is app.chime_player


def test_a_detached_selection_keeps_what_it_was_opened_with(tmp_path, open_real_app):
    with open_real_app(tmp_path, before_start=_saved()) as app:
        _open(app, _add(app, stopped=True))
        app.canvas.open_selection_preview(SELECTION)
        settle(app, 300)
        window = app.canvas._selection_previews[-1][0]

        app.canvas.set_speaker_cues_enabled(False)
        app.canvas.set_speaker_cue_options(False, False, "change", "glass")
        click_button(window.input_view.start_button)
        settle(window, 200)

        reader = window.reader_display
        assert _starts(reader) == (1, 4)
        assert _look(reader) == (True, True, "off", "bell")


# --- Closing the app ----------------------------------------------------------

def test_closing_the_app_closes_the_chime_player(tmp_path, open_real_app, monkeypatch):
    with open_real_app(tmp_path) as app:
        closed = []
        monkeypatch.setattr(app.chime_player, "close", lambda: closed.append(True))

        app._handle_close()

        assert closed == [True]
