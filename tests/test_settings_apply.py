"""Tests for what pressing Apply in Settings does.

Three changes are covered here:

- Apply closes the Settings window once everything is applied. When a value is
  wrong nothing is applied and the window stays open.
- A wrong value is reported by the name shown on screen (not by an internal
  name like "Guide Mark Thickness Px"), and the window takes the person to it:
  the right tab, the box scrolled into view, the cursor in it.
- The Layout tab shows the main window's size as it is now, and applying only
  resizes the window when those numbers were changed (gui/app.py,
  _open_settings_window() and _apply_window_size()).

The Settings window is built straight from the default settings with plain
callbacks in place of the app, like in test_wrapping_label.py, so these run
without a whole app. The window size checks call the app's own methods on a
small stand-in for the same reason."""

import time
import tkinter
from dataclasses import asdict

import customtkinter as ctk
import pytest


@pytest.fixture(scope="module")
def root(fresh_widget_image_caches):
    """See test_wrapping_label.py: the cached app icon belongs to one Tk root,
    so the cache is emptied around this module's root."""
    try:
        window = ctk.CTk()
    except tkinter.TclError:
        pytest.skip("no display available for Tk")
    window.withdraw()
    yield window
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()
    fresh_widget_image_caches()


def _settle(window, milliseconds=300):
    """Let a window finish appearing and laying itself out. On Windows a new
    CTkToplevel hides itself to colour its title bar and comes back on a timer,
    so the event loop is run for a while rather than once."""
    end = time.monotonic() + milliseconds / 1000
    while time.monotonic() < end:
        window.update()
        time.sleep(0.005)


class _Recorder:
    """Stands in for the app's on_apply and remembers every call."""

    def __init__(self):
        self.calls = []

    def __call__(self, values):
        self.calls.append(values)


def _settings_window(owner, on_apply):
    from core.settings_store import AppSettings
    from gui.components.settings_window import SettingsWindow

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
    nothing = lambda *args: None
    return SettingsWindow(
        owner,
        **{name: defaults[name] for name in names},
        transcripts=[],
        on_apply=on_apply,
        on_export_requested=nothing,
        on_import_requested=nothing,
        profile_names=lambda: [],
        on_profile_save=nothing,
        on_profile_update=nothing,
        on_profile_apply=nothing,
        on_profile_rename=nothing,
        on_profile_delete=nothing,
    )


@pytest.fixture
def applied():
    return _Recorder()


@pytest.fixture
def settings(root, applied, wait_until_shown):
    """A Settings window at its default size. It is opened from a window that
    is fully shown first, because Tk keeps a transient window hidden while its
    owner is hidden."""
    owner = ctk.CTkToplevel(root)
    owner.geometry("600x700+0+0")
    wait_until_shown(owner)
    window = _settings_window(owner, applied)
    window.geometry("500x650+10+10")
    wait_until_shown(window)
    yield window
    if window.winfo_exists():
        for timer in window.tk.splitlist(window.tk.call("after", "info")):
            window.tk.call("after", "cancel", timer)
        window.destroy()
    owner.destroy()


def _fields(settings):
    """(key, entry, low, high, name, tab) for every number box, plus the
    highlighted letter shift, which is checked on its own because it can be
    negative."""
    from core.settings_store import HIGHLIGHT_OFFSET_RANGE

    low, high = HIGHLIGHT_OFFSET_RANGE
    return [
        *settings._number_fields(),
        ("highlight_offset_px", settings.highlight_offset_entry, low, high, "The highlighted letter shift", "Defaults"),
    ]


def _field(settings, key):
    return next(field for field in _fields(settings) if field[0] == key)


FIELD_KEYS = (
    "window_width", "window_height", "sidebar_width", "bottom_band_height",
    "font_size_step", "guide_mark_thickness_px", "resume_rewind_words", "highlight_offset_px",
)


def _is_in_view(settings, entry) -> bool:
    """Whether the entry is inside the visible part of the Defaults list."""
    canvas = settings._defaults_scroll._parent_canvas
    top = entry.winfo_rooty() - canvas.winfo_rooty()
    return 0 <= top and top + entry.winfo_height() <= canvas.winfo_height()


# ---- Apply closes the window ----

def test_the_apply_button_applies_and_closes_the_window(settings, applied):
    settings.apply_button.invoke()
    assert len(applied.calls) == 1
    assert not settings.winfo_exists()


def test_a_bad_value_keeps_the_window_open_and_applies_nothing(settings, applied):
    settings._set_entry_value(settings.guide_mark_thickness_entry, "abc")
    settings.apply_button.invoke()
    assert applied.calls == []
    assert settings.winfo_exists()


def test_applying_for_a_profile_keeps_the_window_open(settings, applied):
    """The Profiles tab runs the same check before saving, updating or applying
    a profile, and closes the window itself only after a profile is applied."""
    assert settings._handle_apply() is True
    assert len(applied.calls) == 1
    assert settings.winfo_exists()


# ---- a bad value is reported by name and shown ----

@pytest.mark.parametrize("key", FIELD_KEYS)
def test_a_value_that_is_not_a_number_is_named_and_shown(settings, applied, key):
    _, entry, _, _, name, tab = _field(settings, key)
    settings.tabview.set("Stats")
    settings._set_entry_value(entry, "abc")
    settings.apply_button.invoke()
    _settle(settings, 100)

    assert applied.calls == []
    assert settings.error_label.cget("text") == f"{name} must be a whole number."
    assert settings.tabview.get() == tab
    assert entry._entry.focus_lastfor() is entry._entry
    assert entry._entry.selection_present()


@pytest.mark.parametrize("key", FIELD_KEYS)
def test_a_number_out_of_range_is_named_with_its_range(settings, applied, key):
    _, entry, low, high, name, tab = _field(settings, key)
    settings._set_entry_value(entry, high + 1)
    settings.apply_button.invoke()

    assert applied.calls == []
    assert settings.error_label.cget("text") == f"{name} must be between {low} and {high}."
    assert settings.tabview.get() == tab


def test_messages_use_the_names_on_screen_not_internal_ones(settings):
    for key, entry, _, _, name, _ in _fields(settings):
        assert "_" not in name and "Px" not in name, key
        assert name[0].isupper(), key


def test_a_box_hidden_by_a_search_is_shown_again(settings):
    """Searching for something else hides the box. A box that can't be seen
    can't be fixed, so the search is cleared."""
    entry = settings.guide_mark_thickness_entry
    settings._defaults_search.set_text("surrounding")
    _settle(settings, 100)
    assert not entry.winfo_ismapped()

    settings._set_entry_value(entry, "abc")
    settings.apply_button.invoke()
    _settle(settings, 150)

    assert settings._defaults_search.get() == ""
    assert entry.winfo_ismapped()
    assert _is_in_view(settings, entry)


def test_a_box_far_down_the_list_is_scrolled_into_view(settings):
    entry = settings.resume_rewind_words_entry
    settings._defaults_scroll._parent_canvas.yview_moveto(0)
    _settle(settings, 100)
    assert not _is_in_view(settings, entry), "the test needs the box to start out of view"

    settings._set_entry_value(entry, "abc")
    settings.apply_button.invoke()
    _settle(settings, 150)

    assert _is_in_view(settings, entry)


def test_the_apply_button_comes_back_when_a_problem_moves_away_from_profiles(settings):
    """The Apply button is hidden on the Profiles tab. When a profile button
    finds a bad value, the window moves to the tab with the box, and the
    button has to come back there."""
    settings.tabview.set("Profiles")
    settings._update_apply_button()
    assert settings.apply_button.winfo_manager() == ""

    settings._set_entry_value(settings.window_width_entry, "abc")
    assert settings._handle_apply() is False
    assert settings.tabview.get() == "Layout"
    assert settings.apply_button.winfo_manager() == "pack"


# ---- the main window keeps its size unless it was changed ----

class _AppStandIn:
    """Just enough of the app for its window size methods: a settings store,
    and a geometry() that reports a size and remembers what it was asked to
    change. Anything else the app's methods ask for is a callback that does
    nothing. The three methods below run the app's own code on it. gui.app is
    imported inside them, not at the top of this file, like the other tests
    that use it."""

    def __init__(self, store, size="1000x650+20+30"):
        self.settings_store = store
        self.store = _Transcripts()
        self._window_size_in_settings = (store.window_width, store.window_height)
        self.size = size
        self.geometry_calls = []

    def geometry(self, value=None):
        if value is None:
            return self.size
        self.geometry_calls.append(value)

    def __getattr__(self, name):
        return lambda *args, **kwargs: None

    def _current_window_size(self):
        from gui.app import RSVPApp
        return RSVPApp._current_window_size(self)

    def _apply_window_size(self, width, height):
        from gui.app import RSVPApp
        RSVPApp._apply_window_size(self, width, height)

    def _open_settings_window(self):
        from gui.app import RSVPApp
        RSVPApp._open_settings_window(self)


class _Transcripts:
    transcripts = []


@pytest.fixture
def stand_in(tmp_path):
    from core.settings_store import SettingsStore

    store = SettingsStore(str(tmp_path))
    store.set_window_size(1000, 650)
    return _AppStandIn(store)


@pytest.fixture
def opened_with(monkeypatch):
    """Puts a recorder in place of the Settings window in gui/app.py and
    returns what it was opened with."""
    import gui.app

    received = {}
    monkeypatch.setattr(gui.app, "SettingsWindow", lambda master, **kwargs: received.update(kwargs))
    return received


def test_settings_shows_the_size_the_window_has_now(stand_in, opened_with):
    """A window resized by dragging its edge is not saved, so the saved size is
    out of date. The Layout tab shows the real one."""
    stand_in.size = "1300x800+20+30"
    stand_in._open_settings_window()
    assert (opened_with["window_width"], opened_with["window_height"]) == (1300, 800)


@pytest.mark.parametrize("geometry, size", [
    ("2600x1500+0+0", (2000, 1400)),
    ("300x200-8+0", (500, 400)),
])
def test_a_size_outside_the_range_is_shown_inside_it(stand_in, opened_with, geometry, size):
    """A maximized window on a big screen can be wider than the Layout tab
    accepts. Showing that number would make Apply refuse every change."""
    from core.settings_store import WINDOW_HEIGHT_RANGE, WINDOW_WIDTH_RANGE

    stand_in.size = geometry
    stand_in._open_settings_window()
    width, height = opened_with["window_width"], opened_with["window_height"]
    assert (width, height) == size
    assert WINDOW_WIDTH_RANGE[0] <= width <= WINDOW_WIDTH_RANGE[1]
    assert WINDOW_HEIGHT_RANGE[0] <= height <= WINDOW_HEIGHT_RANGE[1]


def test_applying_the_size_settings_showed_leaves_the_window_alone(stand_in, opened_with):
    """Apply always sends the size from the Layout tab. When it is still what
    the tab showed, nothing was changed there, so a window resized by hand
    keeps its size and nothing new is saved."""
    stand_in.size = "1300x800+20+30"
    stand_in._open_settings_window()
    stand_in._apply_window_size(1300, 800)
    assert stand_in.geometry_calls == []
    assert (stand_in.settings_store.window_width, stand_in.settings_store.window_height) == (1000, 650)


def test_typing_the_saved_size_back_in_resizes_the_window(stand_in, opened_with):
    """Undoing a resize by hand: the saved size is typed back into the Layout
    tab. It matches what is saved, but not what the tab showed, so it is a
    change and the window goes back to it."""
    stand_in.size = "1300x800+20+30"
    stand_in._open_settings_window()
    stand_in._apply_window_size(1000, 650)
    assert stand_in.geometry_calls == ["1000x650"]


@pytest.mark.parametrize("width, height", [(1100, 650), (1000, 700), (1200, 800)])
def test_a_changed_size_is_saved_and_applied(stand_in, opened_with, width, height):
    stand_in._open_settings_window()
    stand_in._apply_window_size(width, height)
    assert stand_in.geometry_calls == [f"{width}x{height}"]
    assert (stand_in.settings_store.window_width, stand_in.settings_store.window_height) == (width, height)


def test_applying_the_same_change_twice_resizes_once(stand_in, opened_with):
    """The Profiles tab applies the other tabs first and keeps Settings open,
    so the same numbers can be applied again from the same window. The second
    time they are no longer a change."""
    stand_in._open_settings_window()
    stand_in._apply_window_size(1100, 700)
    stand_in._apply_window_size(1100, 700)
    assert stand_in.geometry_calls == ["1100x700"]