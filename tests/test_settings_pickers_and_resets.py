"""The parts of the Settings window that open a system dialog or put a tab back to
its defaults, used in a real app: the four colour swatches on the Defaults tab,
"Choose folder…" on the Storage tab, the "Reset to Original Defaults" buttons on
the Layout and Storage tabs, and the mouse wheel over a slider.

The colour picker and the folder picker are system dialogs a test can't click,
so each is swapped for a stand-in that hands back what the test chose (or
nothing, the way Cancel does) and remembers what it was opened with. Everything
else is the real window: real clicks on the swatches and buttons, then Apply.

While a system dialog is open, Settings lets go of its grab so the dialog can be
used, and takes it back once the dialog has closed. The stand-ins check that.
"""
import sys
from pathlib import Path

import customtkinter as ctk
import pytest

from core.settings_store import AppSettings, SettingsStore
from core.transcript_store import TranscriptStore
from gui.components import settings_window as settings_module
from tk_helpers import all_widgets, click_button, settle

PICKED = "#123456"


# ---- helpers ----

class _Dialogs:
    """Stand-ins for the colour picker and the folder picker. answer is what the
    next one hands back; None is what a cancelled dialog gives."""

    def __init__(self):
        self.answer = None
        self.opened_with = []
        self.grab_while_open = []

    def askcolor(self, parent=None, color=None, **options):
        self.opened_with.append(color)
        self.grab_while_open.append(parent.grab_current())
        if self.answer is None:
            return None, None
        return (0, 0, 0), self.answer

    def askdirectory(self, parent=None, initialdir=None, **options):
        self.opened_with.append(initialdir)
        self.grab_while_open.append(parent.grab_current())
        return self.answer or ""


@pytest.fixture
def dialogs(monkeypatch):
    stand_in = _Dialogs()
    monkeypatch.setattr(settings_module, "colorchooser", stand_in)
    monkeypatch.setattr(settings_module.filedialog, "askdirectory", stand_in.askdirectory)
    return stand_in


@pytest.fixture
def app(tmp_path, open_real_app):
    with open_real_app(tmp_path) as app:
        app.callback_errors = []
        app.report_callback_exception = lambda *details: app.callback_errors.append(details)
        yield app
        assert app.callback_errors == []


def _open_settings(app, tab):
    app._open_settings_window()
    settle(app, 300)
    window = app._settings_window
    window.tabview.set(tab)
    settle(window, 150)
    return window


def _button(window, text, tab):
    (button,) = [w for w in all_widgets(window.tabview.tab(tab))
                 if isinstance(w, ctk.CTkButton) and w.cget("text") == text]
    return button


def _apply(app, window):
    click_button(window.apply_button)
    settle(app, 300)
    assert not window.winfo_exists(), "Apply closes Settings when everything is valid"


def _type(entry, value):
    entry.delete(0, "end")
    entry.insert(0, str(value))


# ---- the colour swatches ----

# (the swatch on the window, the window's own copy of the colour, where Apply puts it)
SWATCHES = {
    "font": ("default_font_swatch", "default_font_color", "default_font_color"),
    "highlight": ("default_highlight_swatch", "default_highlight_color", "default_highlight_color"),
    "background": ("default_background_swatch", "default_background_color", "default_background_color"),
    "guide mark": ("guide_mark_color_swatch", "default_guide_mark_color", "guide_mark_color"),
}


@pytest.mark.parametrize("which", SWATCHES)
def test_a_colour_picked_on_a_swatch_shows_and_is_saved_on_apply(app, dialogs, which):
    swatch_name, kept, setting = SWATCHES[which]
    before = getattr(app.settings_store, setting)
    assert before != PICKED
    window = _open_settings(app, "Defaults")
    swatch = getattr(window, swatch_name)
    dialogs.answer = PICKED

    click_button(swatch)
    settle(window, 100)

    assert dialogs.opened_with == [before], "the picker opens on the colour it has now"
    assert swatch.cget("fg_color") == PICKED
    assert getattr(window, kept) == PICKED
    assert getattr(app.settings_store, setting) == before, "nothing is saved before Apply"

    _apply(app, window)

    assert getattr(app.settings_store, setting) == PICKED
    assert getattr(SettingsStore(), setting) == PICKED, "and it is on disk"


@pytest.mark.parametrize("which", SWATCHES)
def test_cancelling_the_colour_picker_changes_nothing(app, dialogs, which):
    swatch_name, kept, setting = SWATCHES[which]
    before = getattr(app.settings_store, setting)
    window = _open_settings(app, "Defaults")
    swatch = getattr(window, swatch_name)
    shown = swatch.cget("fg_color")
    dialogs.answer = None

    click_button(swatch)
    settle(window, 100)

    assert len(dialogs.opened_with) == 1
    assert swatch.cget("fg_color") == shown
    assert getattr(window, kept) == before
    _apply(app, window)
    assert getattr(app.settings_store, setting) == before


def test_a_picked_guide_mark_colour_reaches_the_reader_and_stops_following_the_theme(app, dialogs):
    assert app.settings_store.guide_mark_color_is_default is True
    window = _open_settings(app, "Defaults")
    dialogs.answer = PICKED
    click_button(window.guide_mark_color_swatch)
    settle(window, 100)

    _apply(app, window)

    assert app.canvas._guide_mark_color == PICKED
    assert app.settings_store.guide_mark_color_is_default is False


def test_settings_lets_go_of_its_grab_while_the_picker_is_open_and_takes_it_back(app, dialogs):
    window = _open_settings(app, "Defaults")
    settle(window, 100)
    assert window.grab_current() == window
    dialogs.answer = PICKED

    click_button(window.default_font_swatch)
    assert dialogs.grab_while_open == [None], "the picker can be used"
    settle(window, 150)

    assert window.grab_current() == window, "Settings has its grab back"


# ---- the data folder ----

def test_a_chosen_data_folder_shows_and_the_transcripts_move_there_on_apply(app, dialogs, tmp_path):
    transcript = app.store.add_transcript("Book", app.store.current_space)
    app.store.set_transcript_text(transcript.id, "one two three")
    chosen = tmp_path / "elsewhere"
    chosen.mkdir()
    before = app.settings_store.data_directory
    window = _open_settings(app, "Storage")
    dialogs.answer = str(chosen)

    click_button(_button(window, "Choose folder…", "Storage"))
    settle(window, 100)

    assert dialogs.opened_with == [before], "the picker opens on the folder in use"
    assert window.data_directory_label.cget("text") == str(chosen)
    assert app.settings_store.data_directory == before, "nothing changes before Apply"
    assert not (chosen / "data.json").exists()

    _apply(app, window)

    assert SettingsStore().data_directory == str(chosen)
    assert [t.title for t in TranscriptStore(data_directory=str(chosen)).transcripts] == ["Book"]


def test_cancelling_the_folder_picker_changes_nothing(app, dialogs):
    before = app.settings_store.data_directory
    window = _open_settings(app, "Storage")
    dialogs.answer = None

    click_button(_button(window, "Choose folder…", "Storage"))
    settle(window, 100)

    assert len(dialogs.opened_with) == 1
    assert window.data_directory_label.cget("text") == before
    _apply(app, window)
    assert app.settings_store.data_directory == before


def test_reset_on_the_storage_tab_goes_back_to_the_original_folder(app, dialogs, tmp_path):
    original = AppSettings().data_directory
    moved = tmp_path / "moved"
    moved.mkdir()
    app.settings_store.set_data_directory(str(moved))
    app.store.set_data_directory(str(moved))
    window = _open_settings(app, "Storage")
    assert window.data_directory_label.cget("text") == str(moved)

    click_button(_button(window, "Reset to Original Defaults", "Storage"))
    settle(window, 100)

    assert window.data_directory_label.cget("text") == original
    assert app.settings_store.data_directory == str(moved), "nothing changes before Apply"
    _apply(app, window)
    assert app.settings_store.data_directory == original
    assert Path(original, "data.json").exists()


# ---- the Layout tab's reset ----

def test_reset_on_the_layout_tab_puts_the_sizes_and_free_resizing_back(app):
    original = AppSettings()
    window = _open_settings(app, "Layout")
    if not window.freeform_switch.get():
        window.freeform_switch._canvas.event_generate("<Button-1>", x=5, y=5)
    entries = {
        "window_width": window.window_width_entry,
        "window_height": window.window_height_entry,
        "sidebar_width": window.sidebar_width_entry,
        "bottom_band_height": window.bottom_band_height_entry,
    }
    for name, entry in entries.items():
        _type(entry, getattr(original, name) + 13)
    assert window.freeform_switch.get()

    click_button(_button(window, "Reset to Original Defaults", "Layout"))
    settle(window, 100)

    for name, entry in entries.items():
        assert entry.get() == str(getattr(original, name)), name
    assert bool(window.freeform_switch.get()) is original.freeform_resize_enabled
    _apply(app, window)
    saved = app.settings_store
    assert (saved.sidebar_width, saved.bottom_band_height) == (original.sidebar_width, original.bottom_band_height)
    assert saved.freeform_resize_enabled is original.freeform_resize_enabled


def test_reset_on_the_layout_tab_leaves_the_other_tabs_alone(app):
    window = _open_settings(app, "Layout")
    _type(window.font_size_step_entry, 7)
    window.skip_word_count_slider.set(30)

    click_button(_button(window, "Reset to Original Defaults", "Layout"))
    settle(window, 100)

    assert window.font_size_step_entry.get() == "7"
    assert window.skip_word_count_slider.get() == 30


# ---- the mouse wheel over a slider ----

def _wheel(widget, down):
    """One notch of the mouse wheel over a widget, the way each system sends it:
    X11 as buttons 4 and 5, Windows and macOS as a MouseWheel event."""
    if sys.platform.startswith("linux"):
        widget.event_generate("<Button-5>" if down else "<Button-4>", x=5, y=5)
    else:
        widget.event_generate("<MouseWheel>", delta=-120 if down else 120, x=5, y=5)


def test_the_wheel_over_a_slider_scrolls_the_tab_and_leaves_the_slider_alone(app):
    window = _open_settings(app, "Defaults")
    window.geometry("500x400")
    settle(window, 300)
    scroll = window._defaults_scroll._parent_canvas
    scroll.yview_moveto(0)
    settle(window, 100)
    slider = window.default_wpm_slider
    value = slider.get()

    for _ in range(3):
        _wheel(slider._canvas, down=True)
    settle(window, 100)

    assert slider.get() == value, "the wheel didn't move the slider"
    top = scroll.yview()[0]
    assert top > 0, "the tab scrolled down"

    _wheel(slider._canvas, down=False)
    settle(window, 100)
    assert slider.get() == value
    assert scroll.yview()[0] < top, "and back up"
