"""Tests for the labels that wrap to the room they have
(gui/components/wrapping_label.py), and for the Settings window that uses them
for its descriptions.

Before this, every description in Settings wrapped at a fixed number of pixels,
and the numbers differed from tab to tab (420, 400, 380, 370 and 360). At the
smallest Settings window some of the text ran past the edge and was cut off on
both sides, and at a wide window it left an empty strip on the right. These tests
check that a wrapping label follows its width at 100% and 200% display scaling,
and that no description on any tab is cut off at the smallest window.

They run against a real Tk with one hidden root for the whole module, like
test_transcript_input_bold_starts.py. A hidden window never gets a real size, so
everything that measures is built in a mapped CTkToplevel.

Two things make these tests hold on any machine, not only on a 100% display.
The expected wrap is worked out from the label's own scaling (what Windows'
display setting gives, times any extra factor a test sets), never from an
assumed 100%. And every window is given real time to settle after it opens or
changes size: on Windows a new CTkToplevel hides itself for a moment to colour
its title bar and comes back on a timer, so a single update() can measure a
window that hasn't really been laid out yet."""

import tkinter
from dataclasses import asdict

import customtkinter as ctk
import pytest

from gui.components.wrapping_label import MIN_WRAP_LENGTH, RIGHT_MARGIN, START_WRAP_LENGTH, WrappingLabel

from tk_helpers import all_widgets, settle

LONG_TEXT = (
    "Gives longer words a bit more time on screen, in three steps based on length, "
    "so short words are unaffected and the long ones get a moment more."
)


@pytest.fixture(scope="module")
def root(fresh_widget_image_caches):
    """The Settings window sets the app icon, and that picture is kept for the
    Tk root it was made in. fresh_widget_image_caches (conftest.py) empties that
    cache, so an icon left over from another test module's root is not reused
    here, and this module's icon is not left behind for the next one."""
    try:
        window = ctk.CTk()
    except tkinter.TclError:
        pytest.skip("no display available for Tk")
    window.withdraw()
    yield window
    # CustomTkinter keeps a few timers going on its windows, and a destroyed app
    # leaves the next round of them pending. They would run during the next test
    # module and report errors about a destroyed app, so cancel them first.
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()
    fresh_widget_image_caches()


@pytest.fixture
def scaling():
    """Sets CustomTkinter's extra scaling factor for one test and always puts it
    back to 1.0. The factor is applied on top of whatever the display setting
    already gives, so a test reads the result back from the label instead of
    assuming it."""
    def set_to(factor):
        ctk.set_widget_scaling(factor)
        ctk.set_window_scaling(factor)

    yield set_to
    set_to(1.0)


def shown_label(root, width=400, text=LONG_TEXT, **kwargs):
    """A wrapping label packed across a mapped window of the given width.
    Returns (window, label); the caller destroys the window."""
    top = ctk.CTkToplevel(root)
    top.geometry(f"{width}x300")
    label = WrappingLabel(top, text=text, **kwargs)
    label.pack(fill="x")
    settle(top, 300)
    assert label.winfo_width() > 1, "the window was not laid out"
    return top, label


def resize(top, width):
    """Change a test window's width and give it time to settle."""
    top.geometry(f"{width}x300")
    settle(top, 300)


def expected_wrap(label, margin=RIGHT_MARGIN) -> int:
    """What the label should wrap at: its width in real screen pixels turned
    back into logical pixels by its own scaling, less the margin."""
    return round(label.winfo_width() / label._get_widget_scaling() - margin)


def text_fits(label) -> bool:
    """Whether the text the label draws fits inside the label itself. The text
    sits on an inner tkinter label, whose requested width is the width of its
    longest wrapped line in real screen pixels."""
    return label._label.winfo_reqwidth() <= label.winfo_width()


# ---- the label on its own ----

def test_the_label_wraps_at_its_width_minus_the_margin(root):
    top, label = shown_label(root, 400)
    try:
        assert label.cget("wraplength") == expected_wrap(label)
        assert text_fits(label)
    finally:
        top.destroy()


def test_a_long_text_really_wraps_onto_more_than_one_line(root):
    # Otherwise the test above could pass on a label that never wraps at all.
    top, label = shown_label(root, 400)
    try:
        one_line = ctk.CTkLabel(top, text=LONG_TEXT, font=label.cget("font"))
        one_line.pack()
        settle(top, 300)
        assert label._label.winfo_reqheight() > one_line._label.winfo_reqheight()
    finally:
        top.destroy()


def test_the_wrap_follows_the_window_when_it_gets_narrower_and_wider(root):
    top, label = shown_label(root, 600)
    try:
        wide = label.cget("wraplength")
        assert wide == expected_wrap(label)
        resize(top, 350)
        narrow = label.cget("wraplength")
        assert narrow < wide
        assert narrow == expected_wrap(label)
        assert text_fits(label)

        resize(top, 600)
        assert label.cget("wraplength") == wide
    finally:
        top.destroy()


@pytest.mark.parametrize("factor", [1.5, 2.0])
def test_the_wrap_is_right_on_a_scaled_display(root, scaling, factor):
    """CTkLabel multiplies wraplength by the scaling, while a resize event
    reports real screen pixels. The label turns the width back into logical
    pixels, so the text ends RIGHT_MARGIN logical pixels from the edge, and not
    twice that or half of it. The window asks for 400 logical pixels, so the
    wrap is 380 whatever the scaling is."""
    scaling(factor)
    top, label = shown_label(root, 400)
    try:
        assert label._get_widget_scaling() > 1.0
        assert label.cget("wraplength") == expected_wrap(label) == 400 - RIGHT_MARGIN
        assert text_fits(label)
    finally:
        top.destroy()


def test_the_wrap_catches_up_after_the_scaling_changes(root, scaling):
    top, label = shown_label(root, 400)
    try:
        before = label._get_widget_scaling()
        scaling(2.0)
        settle(top, 300)
        assert label._get_widget_scaling() == before * 2.0
        assert label.cget("wraplength") == expected_wrap(label)
        assert text_fits(label)
    finally:
        top.destroy()


def test_a_custom_margin_is_used(root):
    top, label = shown_label(root, 400, right_margin=50)
    try:
        assert label.cget("wraplength") == expected_wrap(label, margin=50)
    finally:
        top.destroy()


def test_the_wrap_never_goes_below_the_floor(root):
    top, label = shown_label(root, 400, right_margin=1000)
    try:
        assert label.cget("wraplength") == MIN_WRAP_LENGTH
    finally:
        top.destroy()


def test_before_it_has_a_size_it_wraps_at_the_starting_length(root):
    label = WrappingLabel(root, text=LONG_TEXT)
    try:
        assert label.cget("wraplength") == START_WRAP_LENGTH
    finally:
        label.destroy()


def test_the_text_is_left_aligned_unless_asked_otherwise(root):
    label = WrappingLabel(root, text=LONG_TEXT)
    other = WrappingLabel(root, text=LONG_TEXT, justify="center", anchor="center")
    try:
        assert label._label.cget("justify") == "left"
        assert label.cget("anchor") == "w"
        assert other._label.cget("justify") == "center"
        assert other.cget("anchor") == "center"
    finally:
        label.destroy()
        other.destroy()


def test_customtkinters_own_resize_handling_still_runs(root):
    """The label adds its handler next to CustomTkinter's, never in its place.
    CustomTkinter's handler is what keeps the label's own size up to date, so it
    is checked by resizing the window and reading that size back."""
    top, label = shown_label(root, 600)
    try:
        before = label._current_width
        assert before > 0
        resize(top, 350)
        assert label._current_width < before
        assert label._current_width == round(label._reverse_widget_scaling(label.winfo_width()))
    finally:
        top.destroy()


# ---- the Settings window ----

def _settings_window(root, transcripts):
    """A Settings window built straight from the default settings, with plain
    callbacks in place of the app."""
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
        root,
        **{name: defaults[name] for name in names},
        transcripts=transcripts,
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


def _wrapping_labels(widget):
    return [w for w in all_widgets(widget) if isinstance(w, WrappingLabel)]


@pytest.fixture
def settings(root, wait_until_shown):
    """A Settings window at its smallest size, with one transcript whose long
    title has to wrap on the Stats tab. Shown and settled; destroyed after."""
    from core.models import Transcript

    transcript = Transcript(
        id=1, title="Lecture week seven, the long recording transcript with an extra long title",
        space="General", times_read=1, total_words_read=12345, total_time_spent_seconds=3725,
    )
    # Settings marks itself as transient to the window that opened it, and Tk
    # keeps a transient window hidden for as long as its owner is hidden. The
    # module's root is hidden, so Settings is opened from a shown window here,
    # the way the app opens it from the main window. The owner is fully shown
    # first, like the app's main window always is by the time Settings opens.
    owner = ctk.CTkToplevel(root)
    owner.geometry("600x700+0+0")
    wait_until_shown(owner)
    window = _settings_window(owner, [transcript])
    window.geometry("420x650+10+10")
    wait_until_shown(window)
    yield window
    # The window's own timers (the input grab, the reveal) are cancelled through
    # Tcl directly: after_cancel() only works for a timer the same widget made.
    for timer in window.tk.splitlist(window.tk.call("after", "info")):
        window.tk.call("after", "cancel", timer)
    window.destroy()
    owner.destroy()


TABS = ("Defaults", "Layout", "Storage", "Appearance", "Profiles", "Stats")


def test_every_tab_has_wrapping_descriptions(settings):
    for tab in TABS:
        assert _wrapping_labels(settings.tabview.tab(tab)), f"no wrapping label on {tab}"


def test_no_description_uses_a_fixed_wrap_any_more(settings):
    """Only the setting names beside the number boxes on Defaults keep a fixed
    wrap (they share their row with the box). Every other wrapped text in the
    window is a WrappingLabel."""
    for widget in all_widgets(settings):
        if isinstance(widget, ctk.CTkLabel) and not isinstance(widget, WrappingLabel):
            wrap = widget.cget("wraplength")
            assert wrap in (0, 300), f"{widget.cget('text')[:40]!r} wraps at a fixed {wrap}"


@pytest.mark.parametrize("tab", TABS)
def test_nothing_is_cut_off_at_the_smallest_window(settings, tab):
    settings.tabview.set(tab)
    settle(settings, 150)
    labels = [label for label in _wrapping_labels(settings.tabview.tab(tab)) if label.winfo_ismapped()]
    assert labels
    for label in labels:
        assert label.winfo_width() > 1
        assert text_fits(label), f"{label.cget('text')[:40]!r} is cut off on {tab}"


def test_every_description_on_a_tab_ends_the_same_distance_from_the_edge(settings):
    """The Defaults descriptions all sit straight in the scrolling list, so they
    all get the same width and the same wrap."""
    labels = [label for label in _wrapping_labels(settings.tabview.tab("Defaults")) if label.winfo_ismapped()]
    assert len(labels) > 5
    assert len({label.cget("wraplength") for label in labels}) == 1


def test_every_description_is_packed_to_fill_its_row(settings):
    """A wrapping label has to get its width from its parent. Packed without
    fill it would take its width from its own text instead, and every rewrap
    would make it a little narrower than the last."""
    for tab in TABS:
        for label in _wrapping_labels(settings.tabview.tab(tab)):
            assert label.pack_info()["fill"] in ("x", "both"), f"{label.cget('text')[:40]!r} on {tab}"


def test_the_note_at_the_top_of_defaults_wraps_and_says_which_settings_are_for_new_transcripts(settings):
    """Only Speed, the three colours and the word size are what new transcripts
    start with. The note used to say the whole tab was "Applied to newly created
    transcripts only", which stopped being true as switches that apply straight
    away were added below it."""
    from gui.components.settings_window import DEFAULTS_NOTE

    notes = [
        label for label in _wrapping_labels(settings.tabview.tab("Defaults"))
        if label.cget("text") == DEFAULTS_NOTE
    ]
    assert len(notes) == 1
    assert all(name in DEFAULTS_NOTE for name in ("Speed", "colours", "word size"))
    assert "straight away" in DEFAULTS_NOTE