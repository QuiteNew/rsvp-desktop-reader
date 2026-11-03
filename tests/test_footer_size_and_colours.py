"""Tests for the footer's word size buttons and its three colour swatches
(gui/components/footer.py), what the app does with them (gui/app.py,
_handle_font_size_changed() and the three colour handlers), and the store's
colour setters behind them (core/transcript_store.py, set_transcript_font_color()
and its two siblings).

A transcript's reading colours follow the Light/Dark theme until one is picked
by hand (see test_reading_colours_follow_theme.py). Picking a different colour
stops that colour following. Picking the colour it already has is not a choice,
so it keeps following: re-picking the same colour mustn't freeze it.

The first part tests the store on its own. The rest builds the real app with
open_real_app (conftest.py) and presses the real buttons with invoke(). Tk's
colour picker is a system dialog, so it's swapped for a stand-in that hands
back the colour the test chose."""

import json

import pytest

from core.settings_store import FONT_SIZE_RANGE
from core.transcript_store import TranscriptStore

from tk_helpers import settle

PICKED = "#123456"

# (store setter, transcript field, its "follows the theme" flag)
COLOURS = {
    "font": ("set_transcript_font_color", "font_color", "font_color_is_default"),
    "highlight": ("set_transcript_highlight_color", "highlight_color", "highlight_color_is_default"),
    "background": ("set_transcript_background_color", "background_color", "background_color_is_default"),
}


# ---- the store ----

@pytest.fixture
def store(tmp_path):
    return TranscriptStore(data_directory=tmp_path)


@pytest.mark.parametrize("which", COLOURS)
def test_picking_another_colour_stops_it_following_the_theme(store, which):
    setter, field, flag = COLOURS[which]
    transcript = store.add_transcript("A", store.current_space)
    assert getattr(transcript, flag) is True

    getattr(store, setter)(transcript.id, PICKED)

    assert getattr(transcript, field) == PICKED
    assert getattr(transcript, flag) is False


@pytest.mark.parametrize("which", COLOURS)
def test_picking_the_colour_it_already_has_keeps_it_following_the_theme(store, which):
    """And so the next theme change at startup still reaches it."""
    setter, field, flag = COLOURS[which]
    transcript = store.add_transcript("A", store.current_space)
    current = getattr(transcript, field)

    getattr(store, setter)(transcript.id, current)
    assert getattr(transcript, flag) is True

    store.resync_default_reading_colors("#010101", "#020202", "#030303")
    assert getattr(transcript, field) != current


@pytest.mark.parametrize("which", COLOURS)
def test_a_picked_colour_is_saved(store, tmp_path, which):
    setter, field, flag = COLOURS[which]
    transcript = store.add_transcript("A", store.current_space)
    getattr(store, setter)(transcript.id, PICKED)

    reloaded = TranscriptStore(data_directory=tmp_path).transcripts[0]
    assert getattr(reloaded, field) == PICKED
    assert getattr(reloaded, flag) is False


# ---- the footer, in the real app ----

def _open_a_transcript(app, font_size=32, paused=True):
    store = app.store
    transcript = store.add_transcript("A", store.current_space)
    store.set_transcript_text(transcript.id, "one two three four five six")
    store.set_transcript_paused(transcript.id, paused)
    store.set_transcript_font_size(transcript.id, font_size)
    app._refresh_transcript_list()
    settle(app, 200)
    app._handle_open_transcript(transcript)
    settle(app, 300)
    return transcript


def _saved(app, data_dir, transcript):
    app.store.flush()
    saved = json.loads((data_dir / "data.json").read_text(encoding="utf-8"))
    return next(t for t in saved["transcripts"] if t["id"] == transcript.id)


@pytest.fixture
def picker(monkeypatch):
    """Tk's colour picker, swapped for one that hands back picker.answer
    (None for Cancel) and notes the colour it was opened with."""
    from gui.components import footer

    class Picker:
        answer = PICKED
        opened_with = []

        def askcolor(self, color=None, **kwargs):
            self.opened_with.append(color)
            if self.answer is None:
                return None, None
            return (0, 0, 0), self.answer

    stand_in = Picker()
    stand_in.opened_with = []
    monkeypatch.setattr(footer, "colorchooser", stand_in)
    return stand_in


def test_with_nothing_open_the_footer_does_nothing(tmp_path, open_real_app):
    """Its controls are off, and if a change reaches the app anyway, there is
    no transcript to save it to."""
    with open_real_app(tmp_path) as app:
        footer = app.footer
        assert footer.size_increase_button.cget("state") == "disabled"
        assert footer.font_swatch.cget("state") == "disabled"

        app._handle_font_size_changed(40)
        app._handle_font_color_changed(PICKED)
        assert app.store.transcripts == []


def test_opening_a_transcript_shows_its_size_and_colours(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        transcript = _open_a_transcript(app, font_size=44)
        footer = app.footer

        assert footer.size_increase_button.cget("state") == "normal"
        assert footer.size_label.cget("text") == "44px"
        assert footer.font_swatch.cget("fg_color") == transcript.font_color
        assert footer.highlight_swatch.cget("fg_color") == transcript.highlight_color
        assert footer.background_swatch.cget("fg_color") == transcript.background_color


def test_the_size_buttons_change_the_word_size_by_the_step(tmp_path, open_real_app):
    """It's shown, saved, and handed to the reader. The step is the one set
    in Settings."""
    with open_real_app(tmp_path) as app:
        transcript = _open_a_transcript(app, font_size=32)
        footer = app.footer
        footer.set_font_size_step(5)

        footer.size_increase_button.invoke()
        footer.size_increase_button.invoke()
        settle(app, 100)
        assert footer.size_label.cget("text") == "42px"
        assert transcript.font_size == 42
        assert app.canvas.reader_display._chosen_font_size == 42

        footer.size_decrease_button.invoke()
        settle(app, 100)
        assert transcript.font_size == 37
        assert _saved(app, tmp_path, transcript)["font_size"] == 37


@pytest.mark.parametrize("button, start, end", [
    ("size_increase_button", FONT_SIZE_RANGE[1] - 2, FONT_SIZE_RANGE[1]),
    ("size_decrease_button", FONT_SIZE_RANGE[0] + 2, FONT_SIZE_RANGE[0]),
], ids=["largest", "smallest"])
def test_the_word_size_stops_at_each_end(tmp_path, open_real_app, button, start, end):
    with open_real_app(tmp_path) as app:
        transcript = _open_a_transcript(app, font_size=start)
        footer = app.footer
        footer.set_font_size_step(5)

        getattr(footer, button).invoke()
        getattr(footer, button).invoke()
        settle(app, 100)

        assert transcript.font_size == end
        assert footer.size_label.cget("text") == f"{end}px"


def _reader_colour(reader, which):
    if which == "font":
        return reader.before_label.cget("text_color")
    if which == "highlight":
        return reader.focus_label.cget("text_color")
    return reader.cget("fg_color")


@pytest.mark.parametrize("which", COLOURS)
def test_a_swatch_picks_a_colour_for_the_open_transcript(tmp_path, open_real_app, picker, which):
    """The picker opens on the colour in use. The one picked shows on the
    swatch and in the reader, and is saved as picked by hand."""
    _, field, flag = COLOURS[which]
    with open_real_app(tmp_path) as app:
        transcript = _open_a_transcript(app)
        swatch = getattr(app.footer, f"{which}_swatch")
        before = getattr(transcript, field)

        swatch.invoke()
        settle(app, 100)

        assert picker.opened_with == [before]
        assert swatch.cget("fg_color") == PICKED
        assert getattr(transcript, field) == PICKED
        assert _reader_colour(app.canvas.reader_display, which) == PICKED
        saved = _saved(app, tmp_path, transcript)
        assert saved[field] == PICKED
        assert saved[flag] is False


@pytest.mark.parametrize("which", COLOURS)
def test_cancelling_the_picker_changes_nothing(tmp_path, open_real_app, picker, which):
    _, field, flag = COLOURS[which]
    with open_real_app(tmp_path) as app:
        transcript = _open_a_transcript(app)
        swatch = getattr(app.footer, f"{which}_swatch")
        before = getattr(transcript, field)
        picker.answer = None

        swatch.invoke()
        settle(app, 100)

        assert swatch.cget("fg_color") == before
        assert getattr(transcript, field) == before
        assert getattr(transcript, flag) is True


def test_picking_the_colour_already_in_use_leaves_it_following_the_theme(tmp_path, open_real_app, picker):
    with open_real_app(tmp_path) as app:
        transcript = _open_a_transcript(app)
        picker.answer = transcript.font_color

        app.footer.font_swatch.invoke()
        settle(app, 100)

        assert transcript.font_color_is_default is True
        assert _saved(app, tmp_path, transcript)["font_color_is_default"] is True