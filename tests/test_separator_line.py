"""Tests for the thin black lines between settings
(gui/components/separator_line.py), and for where the Settings window puts them.

The rules for the lines, as agreed: they go on the Defaults, Layout and
Appearance tabs only, only under a setting's explanation (never under a setting
that is just a switch or a slider), never after the last thing on a tab, and
always plain black, centred and not touching the sides.

These run against a real Tk with one hidden root for the whole module, like
test_wrapping_label.py, and for the same reasons every window is given real time
to settle and sizes are read back from the window's own scaling instead of
assuming a 100% display."""

import time
import tkinter
from dataclasses import asdict

import customtkinter as ctk
import pytest

from gui.components.separator_line import GAP, LINE_COLOR, THICKNESS, WIDTH_FRACTION, SeparatorLine
from gui.components.wrapping_label import WrappingLabel


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


@pytest.fixture
def scaling():
    """Sets CustomTkinter's extra scaling factor for one test and always puts it
    back to 1.0. It stacks on top of the display's own scaling."""
    def set_to(factor):
        ctk.set_widget_scaling(factor)
        ctk.set_window_scaling(factor)

    yield set_to
    set_to(1.0)


def _settle(window, milliseconds=300):
    """Let a window finish appearing and laying itself out. On Windows a new
    CTkToplevel hides itself to colour its title bar and comes back on a timer,
    so the event loop is run for a while rather than once."""
    end = time.monotonic() + milliseconds / 1000
    while time.monotonic() < end:
        window.update()
        time.sleep(0.005)


def shown_line(root, width=400, **kwargs):
    """A line under a label in a mapped window of the given width, the way the
    Settings window uses one. Returns (window, holder, line); the caller
    destroys the window."""
    top = ctk.CTkToplevel(root)
    top.geometry(f"{width}x300")
    holder = ctk.CTkFrame(top, fg_color="transparent")
    holder.pack(fill="x")
    ctk.CTkLabel(holder, text="An explanation").pack(fill="x")
    line = SeparatorLine(holder, **kwargs)
    line.pack_line()
    _settle(top)
    assert holder.winfo_width() > 1, "the window was not laid out"
    return top, holder, line


def scale_of(widget) -> float:
    from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker
    return ScalingTracker.get_widget_scaling(widget)


def pady_of(line) -> tuple[int, int]:
    """The line's space above and below, as Tk reports it (one number when both
    are the same)."""
    pady = line.pack_info()["pady"]
    if isinstance(pady, int):
        return pady, pady
    return tuple(int(part) for part in pady)


# ---- the line on its own ----

def test_the_line_is_black(root):
    top, _, line = shown_line(root)
    try:
        assert line.cget("bg") == LINE_COLOR == "#000000"
    finally:
        top.destroy()


def test_the_line_takes_its_share_of_the_width_and_is_centred(root):
    top, holder, line = shown_line(root, 500)
    try:
        assert line.winfo_width() == round(holder.winfo_width() * WIDTH_FRACTION)
        left = line.winfo_x()
        right = holder.winfo_width() - (left + line.winfo_width())
        assert left > 0 and right > 0, "the line touches a side"
        assert abs(left - right) <= 1
    finally:
        top.destroy()


def test_the_line_follows_its_parent_when_the_window_changes_size(root):
    top, holder, line = shown_line(root, 600)
    try:
        wide = line.winfo_width()
        top.geometry("350x300")
        _settle(top)
        assert line.winfo_width() < wide
        assert line.winfo_width() == round(holder.winfo_width() * WIDTH_FRACTION)
    finally:
        top.destroy()


def test_thickness_and_space_follow_the_display_scaling(root):
    top, _, line = shown_line(root)
    try:
        scale = scale_of(line)
        assert line.winfo_height() == max(1, round(THICKNESS * scale))
        assert pady_of(line) == (0, round(GAP * scale))
    finally:
        top.destroy()


@pytest.mark.parametrize("factor", [1.5, 2.0])
def test_on_a_scaled_display_the_line_is_thicker_and_the_space_larger(root, scaling, factor):
    """A plain Tk frame is not scaled by CustomTkinter, so the line has to do it
    itself. At 2.0 or more a 1 pixel line is 2 real pixels."""
    scaling(factor)
    top, _, line = shown_line(root, above=5, below=16)
    try:
        scale = scale_of(line)
        assert scale > 1.0
        assert line.winfo_height() == max(1, round(THICKNESS * scale))
        assert pady_of(line) == (round(5 * scale), round(16 * scale))
    finally:
        top.destroy()


def test_a_change_of_scaling_updates_a_line_already_shown(root, scaling):
    top, _, line = shown_line(root)
    try:
        before = scale_of(line)
        scaling(2.0)
        _settle(top)
        scale = scale_of(line)
        assert scale == before * 2.0
        assert line.winfo_height() == max(1, round(THICKNESS * scale))
        assert pady_of(line) == (0, round(GAP * scale))
    finally:
        top.destroy()


def test_a_line_can_be_hidden_and_shown_again_and_goes_back_to_the_bottom(root):
    top, holder, line = shown_line(root)
    try:
        line.pack_forget()
        ctk.CTkLabel(holder, text="Added while the line was hidden").pack(fill="x")
        line.pack_line()
        _settle(top)
        assert holder.pack_slaves()[-1] is line
    finally:
        top.destroy()


def test_the_parents_own_resize_handling_still_runs(root):
    """The line adds its handler to the parent's next to CustomTkinter's, never
    in its place. CustomTkinter's handler keeps the frame's own size up to date,
    so that size is read back after a resize."""
    top, holder, _ = shown_line(root, 600)
    try:
        before = holder._current_width
        top.geometry("350x300")
        _settle(top)
        assert holder._current_width < before
        assert holder._current_width == round(holder._reverse_widget_scaling(holder.winfo_width()))
    finally:
        top.destroy()


# ---- the Settings window ----

def _settings_window(owner):
    """A Settings window built straight from the default settings, with plain
    callbacks in place of the app (the same as in test_wrapping_label.py)."""
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
        on_apply=nothing,
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
def settings(root):
    """A Settings window at its default size. It is opened from a shown window,
    because Tk keeps a transient window hidden while its owner is hidden."""
    owner = ctk.CTkToplevel(root)
    owner.geometry("600x700+0+0")
    owner.update()
    window = _settings_window(owner)
    window.geometry("500x650+10+10")
    _settle(window)
    assert window.winfo_ismapped(), "Settings did not appear"
    yield window
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()
    owner.destroy()


def _all_widgets(widget):
    found = [widget]
    for child in widget.winfo_children():
        found.extend(_all_widgets(child))
    return found


def _lines(widget):
    return [w for w in _all_widgets(widget) if isinstance(w, SeparatorLine)]


def _shown_lines(widget):
    return [line for line in _lines(widget) if line.winfo_manager() == "pack"]


def _search(settings, text):
    settings._defaults_search.set_text(text)
    _settle(settings, 100)


def _shown_items(settings):
    return [item for item in settings._defaults_items if item.holder.winfo_manager() == "pack"]


def test_only_defaults_layout_and_appearance_have_lines(settings):
    assert len(_lines(settings.tabview.tab("Defaults"))) == 13
    assert len(_lines(settings.tabview.tab("Layout"))) == 1
    assert len(_lines(settings.tabview.tab("Appearance"))) == 2
    for tab in ("Storage", "Profiles", "Stats"):
        assert _lines(settings.tabview.tab(tab)) == [], f"{tab} should have no lines"


def test_every_line_sits_right_under_an_explanation(settings):
    """The widget packed just before each line is the grey explanation text, so
    a line is never under a switch, a slider or a number box on its own."""
    for tab in ("Defaults", "Layout", "Appearance"):
        for line in _shown_lines(settings.tabview.tab(tab)):
            before = line.master.pack_slaves()
            above = before[before.index(line) - 1]
            assert isinstance(above, ctk.CTkLabel), f"a line on {tab} is under a {type(above).__name__}"
            assert above.cget("font") is settings.small_font, f"a line on {tab} is under a setting name"


def test_every_defaults_setting_with_an_explanation_has_a_line_and_no_other_does(settings):
    for item in settings._defaults_items:
        if not item.searchable:
            continue
        explained = any(
            isinstance(w, WrappingLabel) and w.cget("text") == item.description
            for w in item.holder.winfo_children()
        ) if item.description else False
        assert (item.separator is not None) == explained, item.name


def test_no_line_after_the_last_thing_on_a_tab(settings):
    """Defaults ends with the skip settings and the reset button, and the last
    explanation on Appearance (letter spacing) is the end of the tab, so neither
    tab ends with a line."""
    shown = _shown_items(settings)
    assert shown[-1].separator is None or shown[-1].separator.winfo_manager() == ""
    appearance = settings._appearance_scroll
    assert not isinstance(appearance.pack_slaves()[-1], SeparatorLine)


def test_all_defaults_lines_show_when_nothing_is_searched(settings):
    assert len(_shown_lines(settings.tabview.tab("Defaults"))) == 13


def test_a_search_shows_lines_between_its_matches_but_not_after_the_last(settings):
    _search(settings, "mark")
    shown = _shown_items(settings)
    assert len(shown) >= 2
    for item in shown[:-1]:
        if item.separator is not None:
            assert item.separator.winfo_manager() == "pack", item.name
    last = shown[-1]
    assert last.separator is not None, "the test needs a last match with an explanation"
    assert last.separator.winfo_manager() == "", "a line was left after the last match"


def test_clearing_the_search_brings_the_lines_back(settings):
    _search(settings, "mark")
    _search(settings, "")
    assert len(_shown_lines(settings.tabview.tab("Defaults"))) == 13
    for item in _shown_items(settings):
        if item.separator is not None:
            assert item.holder.pack_slaves()[-1] is item.separator, f"{item.name}'s line is not at the bottom"


def test_a_search_with_one_match_shows_no_line(settings):
    _search(settings, "horizontal")
    shown = _shown_items(settings)
    assert [item.name for item in shown] == ["Show horizontal guide lines"]
    assert _shown_lines(settings.tabview.tab("Defaults")) == []