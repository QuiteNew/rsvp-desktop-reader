import os
import sys

import customtkinter as ctk
from dataclasses import dataclass
from tkinter import colorchooser, filedialog
from core.colors import blend_colors
from core.font_choice import font_switch_notes
from core.letter_spacing import LEVEL_NAMES, clamp_level
from core.settings_search import matches, query_words
from core.settings_store import (
    AppSettings,
    WINDOW_WIDTH_RANGE, WINDOW_HEIGHT_RANGE,
    SIDEBAR_WIDTH_RANGE, BOTTOM_BAND_HEIGHT_RANGE,
    WPM_RANGE, SKIP_WORD_COUNT_RANGE, FONT_SIZE_RANGE, FONT_SIZE_STEP_RANGE,
    HIGHLIGHT_OFFSET_RANGE, GUIDE_MARK_THICKNESS_RANGE, GUIDE_MARK_LENGTH_PERCENT_RANGE,
    RESUME_REWIND_WORDS_RANGE,
)
from core.timing import format_duration
from gui.components.about_dialog import AboutDialog
from gui.components.profiles_tab import ProfilesTab
from gui.components.search_box import SearchBox
from gui.components.separator_line import SeparatorLine
from gui.components.wrapping_label import WrappingLabel
from gui.icons import description_icon, info_icon
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_HEADING, FONT_BODY, DYSLEXIA_FONT_FELL_BACK, apply_app_icon, center_over_parent

# The tab where this window's own Apply button is hidden: the Profiles tab's
# buttons apply whatever is pending first, so a second Apply would only be in
# the way (see _update_apply_button()).
PROFILES_TAB_NAME = "Profiles"


def _app_loads_its_fonts() -> bool:
    """Whether the app registers its own font files on this system. This
    mirrors register_fonts() in gui/theme.py, which only does anything on
    Windows. Everywhere else the OpenDyslexic family has to be installed."""
    return os.name == "nt"


@dataclass
class _DefaultsItem:
    """One entry of the Defaults tab, as the Settings search sees it. All of an
    entry's widgets live inside its own transparent holder frame, so showing or
    hiding the entry is one pack or forget of that holder and nothing inside is
    touched. Searchable entries are settings, found by name, keywords and
    description. The others (the grey notes and the reset row) have nothing to
    search and are simply hidden while a search is active.

    separator is the thin line under the entry's explanation, if it has one
    (see _separate()). It lives inside the holder, so it comes and goes with
    the entry, and _layout_separators() leaves it off the last entry shown."""
    holder: ctk.CTkFrame
    searchable: bool
    name: str = ""
    keywords: str = ""
    description: str = ""
    separator: SeparatorLine | None = None

class SettingsWindow(ctk.CTkToplevel):
    """App-wide settings: new-transcript defaults, layout sizing (including
    free-form drag-resize), where transcript data is stored, colour theme,
    font and letter spacing, saved reading profiles, and per-transcript reading
    stats. Header height is a fixed constant, not user-configurable; see
    gui/app.py. Theme changes take effect on next launch, not live: every
    widget's color is set explicitly at creation, so a live switch would mean
    reconfiguring the entire widget tree at once. The font switch works the
    same way, since fonts are settled at startup (see gui/theme.py); the letter
    spacing level is applied live."""

    def __init__(
        self, master,
        window_width, window_height,
        sidebar_width, bottom_band_height,
        freeform_resize_enabled,
        default_wpm, default_font_color, default_highlight_color, default_background_color,
        default_font_size, font_size_step, highlight_offset_px,
        skip_word_count, pause_on_skip,
        length_pacing_enabled,
        split_long_paragraphs_enabled,
        resume_rewind_enabled,
        resume_rewind_words,
        warm_up_enabled,
        scrub_pause_enabled,
        peripheral_context_enabled,
        guide_mark_horizontal_enabled,
        guide_mark_thickness_px,
        guide_mark_length_percent,
        guide_mark_color,
        data_directory,
        appearance_mode,
        dyslexia_font_enabled,
        letter_spacing_level,
        transcripts,
        on_apply,
        on_export_requested,
        on_import_requested,
        profile_names,
        on_profile_save,
        on_profile_update,
        on_profile_apply,
        on_profile_rename,
        on_profile_delete,
        on_skip_word_count_changed=None,
        on_pause_on_skip_changed=None,
        on_configure_chunking=None,
    ):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # very end of __init__). CustomTkinter's own CTkToplevel.__init__,
        # which super().__init__() above just ran, withdraws this window
        # itself for a moment to apply Windows' native dark/light title
        # bar (DWM's DWMWA_USE_IMMERSIVE_DARK_MODE), then schedules its
        # own deiconify() ~5ms later. CTkToplevel.resizable(), called a
        # few lines down, independently triggers that same hide/DWM-set/
        # reveal dance a second time via its own delayed callback (see
        # customtkinter/windows/ctk_toplevel.py), so a plain withdraw()-
        # flag cooperation only covers the first cycle and the window
        # would still visibly flash a second time when resizable() fires.
        # Making the window fully transparent instead sidesteps the whole
        # mechanism: it doesn't touch Tk's own map/withdraw state machine
        # at all, so CustomTkinter's internal hide-and-reshow cycles can
        # run their course invisibly however many times they fire (this
        # also happens again if the appearance mode changes later),
        # without us needing to track their timing.
        self.attributes("-alpha", 0)

        self.title("Settings")
        apply_app_icon(self)
        center_over_parent(self, 500, 650)
        self.minsize(420, 420)
        self.resizable(True, True)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_apply = on_apply
        self.on_export_requested = on_export_requested
        self.on_import_requested = on_import_requested
        self.profile_names = profile_names
        self.on_profile_save = on_profile_save
        self.on_profile_update = on_profile_update
        self.on_profile_apply = on_profile_apply
        self.on_profile_rename = on_profile_rename
        self.on_profile_delete = on_profile_delete
        self.on_skip_word_count_changed = on_skip_word_count_changed
        self.on_pause_on_skip_changed = on_pause_on_skip_changed
        self.on_configure_chunking = on_configure_chunking
        self._data_directory = data_directory
        self._defaults_scroll = None  # set once the Defaults tab's scrollable frame exists
        self._defaults_items = []  # the Defaults tab's entries, in display order; see _defaults_item()
        self._defaults_search = None  # the Defaults tab's SearchBox, once built
        self._about_dialog = None  # the About popup while it is open, see _open_about()

        self.label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self.small_font = ctk.CTkFont(family=FONT_BODY, size=11)
        self.button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        self._build_info_button()

        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=1,
            fg_color=HEARTH_PAPER,
            segmented_button_fg_color=WARM_TAUPE,
            segmented_button_selected_color=EMBER_GLOW,
            segmented_button_selected_hover_color=EMBER_GLOW_HOVER,
            segmented_button_unselected_color=WARM_TAUPE,
            segmented_button_unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK,
            command=self._handle_tab_changed,
        )

        self.tabview.pack(fill="both", expand=True, padx=(15, 0), pady=(4, 5))

        defaults_tab = self.tabview.add("Defaults")
        layout_tab = self.tabview.add("Layout")
        storage_tab = self.tabview.add("Storage")
        appearance_tab = self.tabview.add("Appearance")
        profiles_tab = self.tabview.add(PROFILES_TAB_NAME)
        stats_tab = self.tabview.add("Stats")

        self._build_defaults_tab(
            defaults_tab, default_wpm, default_font_color, default_highlight_color,
            default_background_color, default_font_size, font_size_step, highlight_offset_px,
            skip_word_count, pause_on_skip, length_pacing_enabled, split_long_paragraphs_enabled,
            resume_rewind_enabled, resume_rewind_words, warm_up_enabled, scrub_pause_enabled,
            peripheral_context_enabled,
            guide_mark_horizontal_enabled,
            guide_mark_thickness_px, guide_mark_length_percent, guide_mark_color,
        )
        self._build_layout_tab(layout_tab, window_width, window_height, sidebar_width, bottom_band_height, freeform_resize_enabled)
        self._build_storage_tab(storage_tab, data_directory)
        self._build_appearance_tab(appearance_tab, appearance_mode, dyslexia_font_enabled, letter_spacing_level)
        self._build_profiles_tab(profiles_tab)
        self._build_stats_tab(stats_tab, transcripts)

        self.error_label = ctk.CTkLabel(self, text="", text_color="#E74C3C", font=self.small_font)
        self.error_label.pack(padx=15, pady=(0, 5), anchor="w")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(
            button_row, text="Close", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=self.destroy,
        ).pack(side="left")
        # Kept on self so it can be hidden while the Profiles tab is showing.
        self.apply_button = ctk.CTkButton(
            button_row, text="Apply", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=self._handle_apply,
        )
        self.apply_button.pack(side="right")

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # Reveal only now, once everything above is built and colored
        # and comfortably after CustomTkinter's own internal Windows
        # titlebar dance has had time to finish (its slowest leg,
        # triggered by resizable() above, can take up to ~15ms to
        # settle; see the alpha note near the top of __init__). 80ms
        # leaves a wide margin while staying well under what's
        # perceptible as a delay. update_idletasks() right before flipping
        # alpha forces any still-queued layout/redraw work (including CTk
        # widgets, and there are a lot of them on this window's tabs, that
        # defer their own first paint via their own internal after() calls)
        # to actually finish first, rather than letting the reveal catch
        # some of that mid-flight and show pieces of the window popping in
        # over a white background instead of one clean paint.
        self.after(80, self._reveal_now)


    def _reveal_now(self) -> None:
        # Every CTk widget redraws itself on a real <Configure> event once
        # its size actually changes (core_widget_classes/ctk_base_class.py,
        # _update_dimensions_event); update_idletasks() doesn't dispatch
        # those, only update() does (same root cause as the
        # CTkScrollableFrame fix on Space Selection).
        #
        # _parent_canvas.bbox("all") is CustomTkinter's own computed
        # bounding box of everything inside the Defaults tab's scrollable
        # area (see ctk_scrollable_frame.py), the deepest, most
        # widget-dense part of this window, and the same private attribute
        # _redirect_scroll_to_defaults_frame() above already reaches into.
        # Looping until it's identical two passes in a row is a genuine
        # "is it finished" signal rather than a guessed pass count,
        # capped so this can never hang if that attribute name ever
        # changes across a CustomTkinter version. This loop itself
        # typically finishes in under 1ms; the visible delay before this
        # window appears is construction time in __init__ above, not this
        # loop.
        last_bbox = None
        for _ in range(30):
            self.update()
            try:
                current_bbox = self._defaults_scroll._parent_canvas.bbox("all")
            except AttributeError:
                break
            if current_bbox == last_bbox:
                break
            last_bbox = current_bbox
        self.attributes("-alpha", 1)


    def _handle_tab_changed(self) -> None:
        """Runs when someone clicks a tab. CustomTkinter only calls this for a
        click, not when code switches tabs with tabview.set(), which is fine
        here because nothing in the app does that."""
        self._update_apply_button()

    def _update_apply_button(self) -> None:
        """Show this window's Apply button on every tab except Profiles, where
        it would only be a second way to do what the tab's own buttons already
        do (they apply any pending changes first, see _build_profiles_tab()).
        Close is packed on the left of the same row, so the row keeps its height
        and nothing moves when the button comes and goes.

        The button is packed again with the same side it was first given. It has
        no padding, so there is nothing for CustomTkinter to scale a second
        time on a high-DPI screen."""
        showing = self.apply_button.winfo_manager() == "pack"
        if self.tabview.get() == PROFILES_TAB_NAME:
            if showing:
                self.apply_button.pack_forget()
        elif not showing:
            self.apply_button.pack(side="right")

    def _open_native_dialog(self, dialog_fn, **kwargs):
        self.grab_release()
        result = dialog_fn(parent=self, **kwargs)
        self.after(50, self._regrab_if_still_open)
        return result

    def _regrab_if_still_open(self) -> None:
        # Only re-grab if nothing else currently holds the grab. Without
        # this check, this races any dialog Export/Import opens right
        # after the native file dialog closes (the success/failure
        # MessageDialog on export, ImportConfirmDialog on a valid
        # import): that new dialog sets its own grab ~10ms after it's
        # constructed, but this callback was already scheduled 50ms
        # earlier, at the moment the native dialog closed, before the new
        # dialog even existed. Both fire; this one fires second and
        # silently steals the grab back. The new dialog stays visually on
        # top (nothing here affects stacking, a separate concern; see
        # gui/app.py's _settings_window handling) but stops receiving
        # clicks, since Tk only delivers input to whichever window
        # currently holds the grab.
        if self.winfo_exists() and self.grab_current() is None:
            self.grab_set()

    def _build_info_button(self) -> None:
        """The small round "i" button at the top right that opens the About
        popup. It gets a thin strip of its own above the tabs rather than
        floating over the tab bar, so it can never sit on top of a tab however
        wide or narrow the window is.

        Same look and behaviour as the search box's clear button: a soft chip
        that deepens on hover, with the glyph muted at rest and full ink on
        hover. The muted shade is blended from the theme's own colours so it
        reads on both the light and the dark chip.

        Kept deliberately small, a 20px chip with a 12px glyph, so it sits
        quietly in the corner. The glyph is drawn in proportion to its size,
        so a smaller one also has a thinner stroke."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=(15, 12), pady=(10, 0))

        self._info_rest_icon = info_icon(12, blend_colors(COCOA_INK, WARM_TAUPE, 0.25))
        self._info_hover_icon = info_icon(12, COCOA_INK)
        self._info_button = ctk.CTkButton(
            header, text="", image=self._info_rest_icon, width=20, height=20, corner_radius=10,
            fg_color=WARM_TAUPE, hover_color=WARM_LINE, cursor="hand2", command=self._open_about,
        )
        self._info_button.pack(side="right")
        self._info_button.bind("<Enter>", lambda _event: self._info_button.configure(image=self._info_hover_icon))
        self._info_button.bind("<Leave>", lambda _event: self._info_button.configure(image=self._info_rest_icon))

    def _open_about(self) -> None:
        """Opens the About popup over this window, one at a time. The popup
        takes its input grab a few milliseconds after it appears, so a quick
        second click on the button could otherwise open another before the
        first is in the way."""
        if self._about_dialog is not None and self._about_dialog.winfo_exists():
            self._about_dialog.lift()
            self._about_dialog.focus_force()
            return
        self._about_dialog = AboutDialog(self, on_close=self._handle_about_closed)

    def _handle_about_closed(self) -> None:
        """The About popup is gone. Its own input grab replaced this window's,
        and destroying it does not give that back, so take it again. The helper
        checks that nothing else holds the grab first, and the short delay is
        the same one _open_native_dialog() uses."""
        self._about_dialog = None
        self.after(50, self._regrab_if_still_open)

    def _set_entry_value(self, entry: ctk.CTkEntry, value) -> None:
        entry.delete(0, "end")
        entry.insert(0, str(value))

    def _styled_entry(self, master) -> ctk.CTkEntry:
        return ctk.CTkEntry(
            master, fg_color=WARM_TAUPE, border_color=WARM_LINE, border_width=1,
            text_color=COCOA_INK, font=self.label_font,
        )

    def _redirect_scroll_to_defaults_frame(self, event) -> str:
        """Prevents this slider from changing its own value when the
        mouse wheel scrolls over it. CTkSlider is drawn on a Tkinter
        Canvas internally, and Canvas widgets have a built-in default
        where the wheel adjusts the canvas's own content, unrelated to
        CustomTkinter. This stops that and manually forwards the same
        scroll to the enclosing CTkScrollableFrame instead, so hovering a
        slider scrolls the page, same as hovering anywhere else in this tab.

        Handles both of CustomTkinter's own two wheel-event conventions,
        not just one: CTkSlider binds its own value-changing scroll
        handler to <MouseWheel> on Windows/macOS, but to <Button-4> and
        <Button-5> on Linux instead, since X11 reports the wheel as
        button presses rather than a MouseWheel event at all. event.num
        is used for the Linux buttons; event.delta (Windows/macOS) is
        used otherwise, the same discrimination CustomTkinter's own
        _mouse_scroll_event() uses internally, so this mirrors an
        already-proven-safe pattern rather than inventing a new one.

        Reaches into CTkScrollableFrame's `_parent_canvas`; there's no
        public API for this in the installed CustomTkinter version.
        Wrapped defensively: if that attribute name differs on your exact
        version, scrolling over a slider will simply do nothing rather
        than crash or keep changing the value."""
        try:
            canvas = self._defaults_scroll._parent_canvas
            if event.num == 4:      # Linux scroll up
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:    # Linux scroll down
                canvas.yview_scroll(1, "units")
            else:                    # Windows/macOS <MouseWheel>
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except AttributeError:
            pass
        return "break"

    def _styled_slider(self, master, from_, to, steps, command) -> ctk.CTkSlider:
        slider = ctk.CTkSlider(
            master, from_=from_, to=to, number_of_steps=steps,
            progress_color=EMBER_GLOW, button_color=EMBER_GLOW, button_hover_color=EMBER_GLOW_HOVER,
            fg_color=WARM_LINE, command=command,
        )
        # See _redirect_scroll_to_defaults_frame()'s docstring: which
        # event name to intercept is platform-dependent, matching
        # whichever one the installed CTkSlider itself actually binds.
        if "linux" in sys.platform:
            slider._canvas.unbind("<Button-4>")
            slider._canvas.unbind("<Button-5>")
            slider._canvas.bind("<Button-4>", self._redirect_scroll_to_defaults_frame)
            slider._canvas.bind("<Button-5>", self._redirect_scroll_to_defaults_frame)
        else:
            slider._canvas.unbind("<MouseWheel>")
            slider._canvas.bind("<MouseWheel>", self._redirect_scroll_to_defaults_frame)
        return slider

    def _styled_switch(self, master, text, command=None) -> ctk.CTkSwitch:
        return ctk.CTkSwitch(
            master, text=text, font=self.label_font, text_color=COCOA_INK,
            progress_color=EMBER_GLOW, fg_color=WARM_LINE,
            button_color=COCOA_INK, button_hover_color=COCOA_INK,
            command=command,
        )

    def _styled_button(self, master, text, command, width=140) -> ctk.CTkButton:
        return ctk.CTkButton(
            master, text=text, width=width, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=command,
        )

    # ---- Defaults tab ----

    def _defaults_item(self, scroll, name="", keywords="", description="", searchable=True) -> ctk.CTkFrame:
        """Starts one entry of the Defaults tab and returns its holder frame.
        The caller builds that entry's widgets inside the holder and nowhere
        else. The holder is not packed here: _layout_defaults() packs it, in
        the order the entries were started, which is the order they show in.

        name is the text the person sees for the setting, so that typing what
        is on screen finds it. keywords are extra words that are not on screen
        ("color", "crosshair"), and description is the explanation shown under
        the setting. See core/settings_search.py for how the three are used.
        Notes and the reset row pass searchable=False."""
        holder = ctk.CTkFrame(scroll, fg_color="transparent")
        self._defaults_items.append(_DefaultsItem(holder, searchable, name, keywords, description))
        return holder

    def _layout_defaults(self, query: str = "", include_description: bool = False) -> None:
        """Shows the entries of the Defaults tab that fit the query, always in
        their original order. A blank query shows everything, which is the tab
        exactly as built. While a query is typed, the grey notes and the reset
        row are hidden; a small note takes the reset row's place, and if nothing
        matches at all, a "no settings match" message is shown in their stead.

        Every holder is forgotten and the visible ones are packed again, rather
        than touching only the ones that changed: a widget packed again after
        pack_forget() joins the end of its parent's packing list, so packing
        in order from scratch is what keeps the order right. Only the holders
        are packed and forgotten. The widgets inside them keep the padding they
        were given when built, so nothing is scaled a second time on a
        high-DPI screen (CTkBaseClass.pack scales padding on every call)."""
        searching = bool(query_words(query))
        self._defaults_no_match.pack_forget()
        self._defaults_reset_note.pack_forget()
        for item in self._defaults_items:
            item.holder.pack_forget()
        any_match = False
        for item in self._defaults_items:
            if item.searchable:
                visible = matches(query, item.name, item.keywords, item.description, include_description)
                if visible:
                    any_match = True
            else:
                visible = not searching
            if visible:
                item.holder.pack(fill="x")
        self._layout_separators()
        # The reset row is one of the hidden non-searchable items while
        # searching; a short note takes its place so its absence is explained,
        # unless nothing matched at all, when only the no-match message shows.
        if searching and not any_match:
            self._defaults_no_match.pack(anchor="w", pady=(5, 15))
        elif searching:
            self._defaults_reset_note.pack(anchor="w", pady=(20, 0))

    def _separate(self, holder) -> None:
        """Put a separator line under the explanation just added to this
        Defaults entry. Only entries with an explanation get one; a setting that
        is only a switch or a slider doesn't. _layout_separators() decides
        whether it is actually shown."""
        for item in self._defaults_items:
            if item.holder is holder:
                item.separator = SeparatorLine(holder)
                return
        raise ValueError("_separate() needs the holder of a Defaults entry")

    def _layout_separators(self) -> None:
        """Show the separator of every entry on screen except the last one, so
        a line only ever sits between two settings, never after the last thing
        in the list. That last entry changes while searching, which is why this
        runs after every layout. Each line is taken off and put back, which puts
        it back at the bottom of its entry, under the explanation."""
        shown = [item for item in self._defaults_items if item.holder.winfo_manager() == "pack"]
        for item in self._defaults_items:
            if item.separator is not None:
                item.separator.pack_forget()
        for item in shown[:-1]:
            if item.separator is not None:
                item.separator.pack_line()

    def _build_defaults_tab(self, tab, wpm, font_color, highlight_color, background_color, font_size, font_size_step, highlight_offset_px, skip_word_count, pause_on_skip, length_pacing_enabled, split_long_paragraphs_enabled, resume_rewind_enabled, resume_rewind_words, warm_up_enabled, scrub_pause_enabled, peripheral_context_enabled, guide_mark_horizontal_enabled, guide_mark_thickness_px, guide_mark_length_percent, guide_mark_color) -> None:

        # The search row sits above the list and belongs to this tab alone:
        # the other tabs are short and are not searched. Typing re-lays out the
        # list below through _handle_defaults_search_changed, so the list
        # changes live as you type. The row is a taupe strip (like the
        # transcript list's toolbar) so the paper search box reads as a bright
        # field against it, and it also holds the "search descriptions" toggle
        # to the box's right.
        self._search_descriptions = False
        search_row = ctk.CTkFrame(tab, fg_color=WARM_TAUPE, corner_radius=8)
        search_row.pack(fill="x", padx=(0, 4), pady=(2, 8))

        # Packed before the box, same reason as the transcript list's sort
        # button: reserve the fixed-size control's slot on the right first so
        # the box, which fills what is left, can never push it out of the row.
        self._descriptions_icon = description_icon(16, COCOA_INK)
        self._descriptions_button = ctk.CTkButton(
            search_row, text="", image=self._descriptions_icon, width=28, height=28, corner_radius=8,
            fg_color=HEARTH_PAPER, hover_color=WARM_LINE, border_width=1, border_color=WARM_LINE,
            text_color=COCOA_INK, command=self._toggle_search_descriptions,
        )
        self._descriptions_button.pack(side="right", padx=(0, 8), pady=6)

        self._defaults_search = SearchBox(search_row, placeholder_text="Search settings…", on_change=self._handle_defaults_search_changed)
        self._defaults_search.pack(side="left", fill="x", expand=True, padx=(8, 6), pady=6)

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=(0, 0))

        self._defaults_scroll = scroll

        # Shown by _layout_defaults() in place of the list, never at the same
        # time as it: the no-match message when a search finds nothing, the
        # reset note in the hidden reset row's place while a search has matches.
        self._defaults_no_match = ctk.CTkLabel(
            scroll, text="No settings match your search.",
            text_color=COCOA_INK, font=self.small_font,
        )
        self._defaults_reset_note = ctk.CTkLabel(
            scroll, text="Clear the search to show the reset button.",
            text_color=COCOA_INK, font=self.small_font,
        )

        holder = self._defaults_item(scroll, searchable=False)
        ctk.CTkLabel(holder, text="Applied to newly created transcripts only", text_color=COCOA_INK, font=self.small_font).pack(anchor="w", pady=(5, 15))

        holder = self._defaults_item(scroll, "Speed", "wpm words per minute rate pace tempo fast slow")
        wpm_row = ctk.CTkFrame(holder, fg_color="transparent")
        wpm_row.pack(fill="x", pady=6)
        ctk.CTkLabel(wpm_row, text="Speed", width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.default_wpm_label = ctk.CTkLabel(wpm_row, text=f"{wpm} WPM", width=70, text_color=COCOA_INK, font=self.label_font)
        self.default_wpm_label.pack(side="right")
        self.default_wpm_slider = self._styled_slider(
            holder, WPM_RANGE[0], WPM_RANGE[1], 90,
            lambda v: self.default_wpm_label.configure(text=f"{int(v)} WPM"),
        )
        self.default_wpm_slider.set(wpm)
        self.default_wpm_slider.pack(fill="x", pady=(0, 10))

        holder = self._defaults_item(scroll, "Font colour", "color text letters words")
        self.default_font_color = font_color
        self.default_font_swatch = self._color_row(holder, "Font colour", font_color, self._pick_default_font_color)

        holder = self._defaults_item(scroll, "Highlight colour", "color accent focus letter orp optimal recognition point")
        self.default_highlight_color = highlight_color
        self.default_highlight_swatch = self._color_row(holder, "Highlight colour", highlight_color, self._pick_default_highlight_color)

        holder = self._defaults_item(scroll, "Background colour", "color backdrop canvas reading area")
        self.default_background_color = background_color
        self.default_background_swatch = self._color_row(holder, "Background colour", background_color, self._pick_default_background_color)

        holder = self._defaults_item(scroll, "Word size", "font size text size px pixels bigger smaller larger zoom scale")
        self.default_font_size = font_size
        size_row = ctk.CTkFrame(holder, fg_color="transparent")
        size_row.pack(fill="x", pady=6)
        ctk.CTkLabel(size_row, text="Word size", width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.default_font_size_label = ctk.CTkLabel(size_row, text=f"{font_size} px", width=70, text_color=COCOA_INK, font=self.label_font)
        self.default_font_size_label.pack(side="right")
        self.default_font_size_slider = self._styled_slider(
            holder, FONT_SIZE_RANGE[0], FONT_SIZE_RANGE[1], FONT_SIZE_RANGE[1] - FONT_SIZE_RANGE[0],
            lambda v: (self.default_font_size_label.configure(text=f"{int(v)} px"), setattr(self, "default_font_size", int(v))),
        )
        self.default_font_size_slider.set(font_size)
        self.default_font_size_slider.pack(fill="x", pady=(0, 8))

        holder = self._defaults_item(scroll, searchable=False)
        ctk.CTkLabel(
            holder, text="Changes for the WPM slider take effect after clicking Apply.",
            text_color=COCOA_INK, font=self.small_font,
        ).pack(anchor="w", pady=(0, 20))
        self._separate(holder)

        chunking_description = "Flash several words at once instead of one at a time, so your eyes move less across each flash. Opens a window where you can turn this on for the transcript open now or for new transcripts, pick a fixed number of words or an adaptive width, and set the size."
        holder = self._defaults_item(
            scroll, "Configure chunking",
            "chunk chunks chunking group grouping words at a time several multiple phrase adaptive fixed",
            chunking_description,
        )
        self._styled_button(holder, "Configure chunking…", self._handle_configure_chunking, width=180).pack(anchor="w", pady=(0, 5))
        WrappingLabel(
            holder,
            text=chunking_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        holder = self._defaults_item(
            scroll, "Increase the word size by this many pixels each time +/- is clicked",
            "font size step increment plus minus buttons zoom change amount",
        )
        step_row = ctk.CTkFrame(holder, fg_color="transparent")
        step_row.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(
            step_row, text="Increase the word size by this many pixels each time +/- is clicked:",
            text_color=COCOA_INK, font=self.label_font, wraplength=300, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.font_size_step_entry = self._styled_entry(step_row)
        self.font_size_step_entry.configure(width=40)
        self.font_size_step_entry.insert(0, str(font_size_step))
        self.font_size_step_entry.pack(side="left", padx=(8, 0))

        low, high = HIGHLIGHT_OFFSET_RANGE
        offset_description = f"Applies globally, to every transcript. Allowed range: {low} to {high}."
        holder = self._defaults_item(
            scroll, "Shift the highlighted letter vertically by this many pixels (positive = up, negative = down)",
            "highlight position offset vertical move nudge up down focus letter orp",
            offset_description,
        )
        offset_row = ctk.CTkFrame(holder, fg_color="transparent")
        offset_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            offset_row, text="Shift the highlighted letter vertically by this many pixels (positive = up, negative = down):",
            text_color=COCOA_INK, font=self.label_font, wraplength=300, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.highlight_offset_entry = self._styled_entry(offset_row)
        self.highlight_offset_entry.configure(width=40)
        self.highlight_offset_entry.insert(0, str(highlight_offset_px))
        self.highlight_offset_entry.pack(side="left", padx=(8, 0))

        WrappingLabel(
            holder, text=offset_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        low, high = GUIDE_MARK_THICKNESS_RANGE
        thickness_description = f"Applies globally, to every transcript. Allowed range: {low} to {high}."
        holder = self._defaults_item(
            scroll, "Thickness of the vertical guide marks, in pixels",
            "guide marks lines width stroke thick thin crosshair",
            thickness_description,
        )
        thickness_row = ctk.CTkFrame(holder, fg_color="transparent")
        thickness_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            thickness_row, text="Thickness of the vertical guide marks, in pixels:",
            text_color=COCOA_INK, font=self.label_font, wraplength=300, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.guide_mark_thickness_entry = self._styled_entry(thickness_row)
        self.guide_mark_thickness_entry.configure(width=40)
        self.guide_mark_thickness_entry.insert(0, str(guide_mark_thickness_px))
        self.guide_mark_thickness_entry.pack(side="left", padx=(8, 0))

        WrappingLabel(
            holder, text=thickness_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        length_description = "Length of the vertical guide marks, as a percentage of the current word so they keep scaling with the Word Size setting above. Applies globally."
        holder = self._defaults_item(
            scroll, "Mark length",
            "guide marks vertical lines height size percent percentage crosshair",
            length_description,
        )
        length_row = ctk.CTkFrame(holder, fg_color="transparent")
        length_row.pack(fill="x", pady=6)
        ctk.CTkLabel(length_row, text="Mark length", width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.guide_mark_length_label = ctk.CTkLabel(length_row, text=f"{guide_mark_length_percent}%", width=70, text_color=COCOA_INK, font=self.label_font)
        self.guide_mark_length_label.pack(side="right")
        self.default_guide_mark_length_percent = guide_mark_length_percent
        self.guide_mark_length_slider = self._styled_slider(
            holder, GUIDE_MARK_LENGTH_PERCENT_RANGE[0], GUIDE_MARK_LENGTH_PERCENT_RANGE[1],
            GUIDE_MARK_LENGTH_PERCENT_RANGE[1] - GUIDE_MARK_LENGTH_PERCENT_RANGE[0],
            lambda v: (self.guide_mark_length_label.configure(text=f"{int(v)}%"), setattr(self, "default_guide_mark_length_percent", int(v))),
        )
        self.guide_mark_length_slider.set(guide_mark_length_percent)
        self.guide_mark_length_slider.pack(fill="x", pady=(0, 4))
        WrappingLabel(
            holder,
            text=length_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        mark_color_description = "Colour of the vertical guide marks above and below the highlighted letter. Applies globally, to every transcript."
        holder = self._defaults_item(
            scroll, "Mark colour",
            "color guide marks lines vertical crosshair",
            mark_color_description,
        )
        self.default_guide_mark_color = guide_mark_color
        self.guide_mark_color_swatch = self._color_row(holder, "Mark colour", guide_mark_color, self._pick_guide_mark_color)
        WrappingLabel(
            holder,
            text=mark_color_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        horizontal_description = "Adds a fixed grey line above and below the vertical guide marks, sized close to the width of the reading area, to help keep your eyes centered while reading."
        holder = self._defaults_item(
            scroll, "Show horizontal guide lines",
            "crosshair grey gray above below centered centred",
            horizontal_description,
        )
        self.guide_mark_horizontal_switch = self._styled_switch(holder, "Show horizontal guide lines")
        (self.guide_mark_horizontal_switch.select() if guide_mark_horizontal_enabled else self.guide_mark_horizontal_switch.deselect())
        self.guide_mark_horizontal_switch.pack(anchor="w", pady=(0, 5))
        WrappingLabel(
            holder,
            text=horizontal_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        pacing_description = "Gives longer words a bit more time on screen, in three steps based on length (short words are unaffected). If a word is both long and ends a sentence or clause, only the longer of the two pauses applies, since they don't stack. Applies globally, takes effect after clicking Apply."
        holder = self._defaults_item(
            scroll, "Slow down for long words",
            "length long pacing pause delay timing longer pace speed",
            pacing_description,
        )
        self.length_pacing_switch = self._styled_switch(holder, "Slow down for long words")
        (self.length_pacing_switch.select() if length_pacing_enabled else self.length_pacing_switch.deselect())
        self.length_pacing_switch.pack(anchor="w", pady=(0, 5))
        WrappingLabel(
            holder,
            text=pacing_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        warm_up_description = "Starts each reading session at about half speed and builds up to your chosen speed over the first several words, so you settle in instead of being hit with full speed right away. It stacks with the pacing above. Applies globally, to the main and detached windows, and takes effect after clicking Apply."
        holder = self._defaults_item(
            scroll, "Ease in at the start of reading",
            "warm up warmup warm-up ramp gradually slow start half speed build up begin",
            warm_up_description,
        )
        self.warm_up_switch = self._styled_switch(holder, "Ease in at the start of reading")
        (self.warm_up_switch.select() if warm_up_enabled else self.warm_up_switch.deselect())
        self.warm_up_switch.pack(anchor="w", pady=(0, 5))
        WrappingLabel(
            holder,
            text=warm_up_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        split_description = "When you click Normalize, also break a long wall of text into paragraphs at sentence ends, so it's easier to read in the edit box. This only changes how the text is laid out for editing, never what gets read or the reading speed. Applies globally; takes effect the next time you click Normalize."
        holder = self._defaults_item(
            scroll, "Split long paragraphs when normalizing",
            "normalize normalise paragraphs break wall of text sentences edit box layout",
            split_description,
        )
        self.split_long_paragraphs_switch = self._styled_switch(holder, "Split long paragraphs when normalizing")
        (self.split_long_paragraphs_switch.select() if split_long_paragraphs_enabled else self.split_long_paragraphs_switch.deselect())
        self.split_long_paragraphs_switch.pack(anchor="w", pady=(0, 5))
        WrappingLabel(
            holder,
            text=split_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        low, high = RESUME_REWIND_WORDS_RANGE
        rewind_description = (
            "When you resume after pausing, reading first steps back this many words, "
            "so you pick up with a little context instead of exactly where you stopped. "
            f"Applies globally, to the main and detached windows. Allowed range: {low} to {high}. "
            "Takes effect after clicking Apply, and only while the toggle above is on."
        )
        holder = self._defaults_item(
            scroll, "Rewind a few words when resuming",
            "back step back replay context resume pause words to rewind on resume",
            rewind_description,
        )
        self.resume_rewind_switch = self._styled_switch(holder, "Rewind a few words when resuming")
        (self.resume_rewind_switch.select() if resume_rewind_enabled else self.resume_rewind_switch.deselect())
        self.resume_rewind_switch.pack(anchor="w", pady=(0, 5))

        rewind_row = ctk.CTkFrame(holder, fg_color="transparent")
        rewind_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            rewind_row, text="Words to rewind on resume:",
            text_color=COCOA_INK, font=self.label_font, wraplength=300, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.resume_rewind_words_entry = self._styled_entry(rewind_row)
        self.resume_rewind_words_entry.configure(width=40)
        self.resume_rewind_words_entry.insert(0, str(resume_rewind_words))
        self.resume_rewind_words_entry.pack(side="left", padx=(8, 0))

        WrappingLabel(
            holder,
            text=rewind_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        scrub_description = "When you drag the progress bar to a new spot and let go, reading pauses there, so you can get your bearings before pressing play. Turn this off to have reading keep going from the new spot if it was already playing. Applies globally, to the main and detached windows, and takes effect after clicking Apply."
        holder = self._defaults_item(
            scroll, "Pause after using the scrubber",
            "scrub scrubber progress bar seek drag jump position slider stop",
            scrub_description,
        )
        self.scrub_pause_switch = self._styled_switch(holder, "Pause after using the scrubber")
        (self.scrub_pause_switch.select() if scrub_pause_enabled else self.scrub_pause_switch.deselect())
        self.scrub_pause_switch.pack(anchor="w", pady=(0, 5))
        WrappingLabel(
            holder,
            text=scrub_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        peripheral_description = "Shows a dim line beneath the flashing word with the words just before and after it, so you keep a little sense of the sentence around what you're reading without your eyes leaving the centre. Applies globally, to the main and detached windows, and takes effect after clicking Apply."
        holder = self._defaults_item(
            scroll, "Show surrounding words",
            "peripheral context ribbon sentence before after dim line neighbours neighbors nearby",
            peripheral_description,
        )
        self.peripheral_context_switch = self._styled_switch(holder, "Show surrounding words")
        (self.peripheral_context_switch.select() if peripheral_context_enabled else self.peripheral_context_switch.deselect())
        self.peripheral_context_switch.pack(anchor="w", pady=(0, 5))
        WrappingLabel(
            holder,
            text=peripheral_description,
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 20))
        self._separate(holder)

        holder = self._defaults_item(scroll, searchable=False)
        WrappingLabel(
            holder, text="Skip controls below apply immediately, to the current transcript and all future ones",
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 10))

        holder = self._defaults_item(scroll, "Skip amount", "skip jump forward backward words arrows buttons")
        skip_row = ctk.CTkFrame(holder, fg_color="transparent")
        skip_row.pack(fill="x", pady=6)
        ctk.CTkLabel(skip_row, text="Skip amount", width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.skip_word_count_label = ctk.CTkLabel(skip_row, text=f"{skip_word_count} words", width=70, text_color=COCOA_INK, font=self.label_font)
        self.skip_word_count_label.pack(side="right")
        self.skip_word_count_slider = self._styled_slider(
            holder, SKIP_WORD_COUNT_RANGE[0], SKIP_WORD_COUNT_RANGE[1], SKIP_WORD_COUNT_RANGE[1] - SKIP_WORD_COUNT_RANGE[0],
            self._handle_skip_word_count_slide,
        )
        self.skip_word_count_slider.set(skip_word_count)
        self.skip_word_count_slider.pack(fill="x", pady=(0, 10))

        holder = self._defaults_item(scroll, "Pause playback when skipping", "skip jump stop halt play")
        self.pause_on_skip_switch = self._styled_switch(holder, "Pause playback when skipping", self._handle_pause_on_skip_toggle)
        (self.pause_on_skip_switch.select() if pause_on_skip else self.pause_on_skip_switch.deselect())
        self.pause_on_skip_switch.pack(anchor="w", pady=(5, 15))

        holder = self._defaults_item(scroll, searchable=False)
        self._reset_row(holder, self._handle_reset_defaults)

        self._layout_defaults()

    def _handle_defaults_search_changed(self) -> None:
        """Re-lays out the Defaults list for the text now in the search box,
        then returns it to the top: the list just got shorter or longer, so
        keeping the old scroll offset would leave the first matches off screen.
        Reaches into CTkScrollableFrame's `_parent_canvas`, the same private
        attribute _redirect_scroll_to_defaults_frame() already uses."""
        self._layout_defaults(self._defaults_search.get(), self._search_descriptions)
        try:
            self._defaults_scroll._parent_canvas.yview_moveto(0)
        except AttributeError:
            pass

    def _toggle_search_descriptions(self) -> None:
        """Turns searching inside each setting's description on or off and
        shows the button's pressed state (solid ember on, pale off). Re-filters
        at once, so a query already typed updates."""
        self._search_descriptions = not self._search_descriptions
        if self._search_descriptions:
            self._descriptions_button.configure(fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER)
        else:
            self._descriptions_button.configure(fg_color=HEARTH_PAPER, hover_color=WARM_LINE)
        self._handle_defaults_search_changed()

    def _reset_row(self, tab, command) -> None:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=(20, 0))
        self._styled_button(row, "Reset to Original Defaults", command, width=200).pack(anchor="w")

    def _color_row(self, tab, label, color, command) -> ctk.CTkButton:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text=label, width=90, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        swatch = ctk.CTkButton(
            row, text="", width=28, height=28, corner_radius=8,
            border_width=2, border_color=WARM_LINE, fg_color=color, command=command,
        )
        swatch.pack(side="left", padx=(12, 0))
        return swatch

    def _pick_default_font_color(self) -> None:
        color = self._open_native_dialog(colorchooser.askcolor, color=self.default_font_color)[1]
        if color:
            self.default_font_color = color
            self.default_font_swatch.configure(fg_color=color)

    def _pick_default_highlight_color(self) -> None:
        color = self._open_native_dialog(colorchooser.askcolor, color=self.default_highlight_color)[1]
        if color:
            self.default_highlight_color = color
            self.default_highlight_swatch.configure(fg_color=color)

    def _pick_default_background_color(self) -> None:
        color = self._open_native_dialog(colorchooser.askcolor, color=self.default_background_color)[1]
        if color:
            self.default_background_color = color
            self.default_background_swatch.configure(fg_color=color)

    def _pick_guide_mark_color(self) -> None:
        color = self._open_native_dialog(colorchooser.askcolor, color=self.default_guide_mark_color)[1]
        if color:
            self.default_guide_mark_color = color
            self.guide_mark_color_swatch.configure(fg_color=color)

    def _handle_skip_word_count_slide(self, value) -> None:
        count = int(value)
        self.skip_word_count_label.configure(text=f"{count} words")
        if self.on_skip_word_count_changed:
            self.on_skip_word_count_changed(count)

    def _handle_pause_on_skip_toggle(self) -> None:
        enabled = bool(self.pause_on_skip_switch.get())
        if self.on_pause_on_skip_changed:
            self.on_pause_on_skip_changed(enabled)

    def _handle_configure_chunking(self) -> None:
        if self.on_configure_chunking:
            self.on_configure_chunking()

    def _handle_reset_defaults(self) -> None:
        original = AppSettings()

        self.default_wpm_slider.set(original.default_wpm)
        self.default_wpm_label.configure(text=f"{original.default_wpm} WPM")

        self.default_font_color = original.default_font_color
        self.default_font_swatch.configure(fg_color=original.default_font_color)

        self.default_highlight_color = original.default_highlight_color
        self.default_highlight_swatch.configure(fg_color=original.default_highlight_color)

        self.default_background_color = original.default_background_color
        self.default_background_swatch.configure(fg_color=original.default_background_color)

        self.default_font_size = original.default_font_size
        self.default_font_size_slider.set(original.default_font_size)
        self.default_font_size_label.configure(text=f"{original.default_font_size} px")

        self._set_entry_value(self.font_size_step_entry, original.font_size_step)
        self._set_entry_value(self.highlight_offset_entry, original.highlight_offset_px)
        self._set_entry_value(self.guide_mark_thickness_entry, original.guide_mark_thickness_px)

        self.default_guide_mark_length_percent = original.guide_mark_length_percent
        self.guide_mark_length_slider.set(original.guide_mark_length_percent)
        self.guide_mark_length_label.configure(text=f"{original.guide_mark_length_percent}%")

        self.default_guide_mark_color = original.guide_mark_color
        self.guide_mark_color_swatch.configure(fg_color=original.guide_mark_color)

        (self.guide_mark_horizontal_switch.select() if original.guide_mark_horizontal_enabled else self.guide_mark_horizontal_switch.deselect())

        (self.length_pacing_switch.select() if original.length_pacing_enabled else self.length_pacing_switch.deselect())

        (self.warm_up_switch.select() if original.warm_up_enabled else self.warm_up_switch.deselect())

        (self.split_long_paragraphs_switch.select() if original.split_long_paragraphs_enabled else self.split_long_paragraphs_switch.deselect())

        (self.resume_rewind_switch.select() if original.resume_rewind_enabled else self.resume_rewind_switch.deselect())
        self._set_entry_value(self.resume_rewind_words_entry, original.resume_rewind_words)

        (self.scrub_pause_switch.select() if original.scrub_pause_enabled else self.scrub_pause_switch.deselect())

        (self.peripheral_context_switch.select() if original.peripheral_context_enabled else self.peripheral_context_switch.deselect())

        self.skip_word_count_slider.set(original.skip_word_count)
        self.skip_word_count_label.configure(text=f"{original.skip_word_count} words")
        if self.on_skip_word_count_changed:
            self.on_skip_word_count_changed(original.skip_word_count)

        (self.pause_on_skip_switch.select() if original.pause_on_skip else self.pause_on_skip_switch.deselect())
        if self.on_pause_on_skip_changed:
            self.on_pause_on_skip_changed(original.pause_on_skip)

    # ---- Layout tab ----

    def _build_layout_tab(self, tab, window_width, window_height, sidebar_width, bottom_band_height, freeform_resize_enabled) -> None:
        self.freeform_switch = self._styled_switch(tab, "Free-form resize (drag borders in the main window)")
        (self.freeform_switch.select() if freeform_resize_enabled else self.freeform_switch.deselect())
        self.freeform_switch.pack(anchor="w", pady=(5, 5))
        WrappingLabel(
            tab, text="When on, hover over the sidebar or bottom-band border in the main window and drag it directly.",
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 15))
        # The explanation leaves 15 below it and the first size row 4 above it,
        # so the line adds 5 and 16 to sit 20 from each.
        SeparatorLine(tab, above=5, below=16).pack_line()

        self.window_width_entry = self._number_row(tab, "Window width", window_width)
        self.window_height_entry = self._number_row(tab, "Window height", window_height)
        self.sidebar_width_entry = self._number_row(tab, "Sidebar width", sidebar_width)
        self.bottom_band_height_entry = self._number_row(tab, "Bottom band height", bottom_band_height)

        self._reset_row(tab, self._handle_reset_layout)

    def _number_row(self, tab, label, value) -> ctk.CTkEntry:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=label, width=140, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        entry = self._styled_entry(row)
        entry.insert(0, str(value))
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _handle_reset_layout(self) -> None:
        original = AppSettings()

        (self.freeform_switch.select() if original.freeform_resize_enabled else self.freeform_switch.deselect())
        self._set_entry_value(self.window_width_entry, original.window_width)
        self._set_entry_value(self.window_height_entry, original.window_height)
        self._set_entry_value(self.sidebar_width_entry, original.sidebar_width)
        self._set_entry_value(self.bottom_band_height_entry, original.bottom_band_height)

    # ---- Storage tab ----

    def _build_storage_tab(self, tab, data_directory) -> None:
        ctk.CTkLabel(
            tab, text="Transcripts are saved as a JSON file in this folder:",
            text_color=COCOA_INK, font=self.small_font,
        ).pack(anchor="w", pady=(5, 10))
        self.data_directory_label = WrappingLabel(tab, text=data_directory, text_color=COCOA_INK, font=self.small_font)
        self.data_directory_label.pack(fill="x", pady=(0, 10))
        self._styled_button(tab, "Choose folder…", self._pick_data_directory, width=140).pack(anchor="w")

        WrappingLabel(
            tab, text="Move your transcripts, spaces, and settings to or from another machine:",
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(20, 10))
        export_import_row = ctk.CTkFrame(tab, fg_color="transparent")
        export_import_row.pack(fill="x", pady=(0, 10))
        self._styled_button(export_import_row, "Export Data…", self._handle_export_data, width=140).pack(side="left")
        self._styled_button(export_import_row, "Import Data…", self._handle_import_data, width=140).pack(side="left", padx=(10, 0))

        self._reset_row(tab, self._handle_reset_storage)

    def _pick_data_directory(self) -> None:
        chosen = self._open_native_dialog(filedialog.askdirectory, initialdir=self._data_directory)
        if chosen:
            self._data_directory = chosen
            self.data_directory_label.configure(text=chosen)

    def _handle_export_data(self) -> None:
        """Collects a destination path via a native save dialog and hands
        it straight to on_export_requested. Unlike "Choose folder…" above,
        which only stages a value the Apply button submits later, Export
        and Import are immediate, one-shot actions with real side effects
        of their own (writing a file; overwriting stored data), so they
        bubble straight up to gui/app.py instead of going through
        _handle_apply()'s values dict."""
        path = self._open_native_dialog(
            filedialog.asksaveasfilename,
            title="Export Data",
            defaultextension=".json",
            filetypes=[("RSVP Reader export", "*.json")],
            initialfile="rsvp-reader-export.json",
        )
        if path:
            self.on_export_requested(path)

    def _handle_import_data(self) -> None:
        path = self._open_native_dialog(
            filedialog.askopenfilename,
            title="Import Data",
            filetypes=[("RSVP Reader export", "*.json")],
        )
        if path:
            self.on_import_requested(path)

    def _handle_reset_storage(self) -> None:
        original = AppSettings()
        self._data_directory = original.data_directory
        self.data_directory_label.configure(text=original.data_directory)

    # ---- Appearance tab ----

    def _build_appearance_tab(self, tab, appearance_mode: str, dyslexia_font_enabled: bool, letter_spacing_level: int) -> None:
        """The colour theme, the font and the letter spacing. The theme and the
        font are read once at startup, so those two say they need a relaunch;
        the spacing level applies as soon as Apply is pressed. The tab scrolls,
        because it holds more than fits when the window is made small."""
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._appearance_scroll = scroll

        ctk.CTkLabel(
            scroll, text="Colour theme", text_color=COCOA_INK, font=self.label_font,
        ).pack(anchor="w", pady=(10, 8))

        self.appearance_mode_selector = ctk.CTkSegmentedButton(
            scroll, values=["Light", "Dark", "System"],
            fg_color=WARM_TAUPE, selected_color=EMBER_GLOW, selected_hover_color=EMBER_GLOW_HOVER,
            unselected_color=WARM_TAUPE, unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK, font=self.label_font,
        )
        self.appearance_mode_selector.set(appearance_mode.capitalize())
        self.appearance_mode_selector.pack(fill="x", pady=(0, 10))

        WrappingLabel(
            scroll,
            text="Takes effect the next time you launch the app.",
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 10))

        WrappingLabel(
            scroll,
            text=(
                "Note: a new transcript's reading colours (font, highlight, "
                "background) come from the Defaults tab, not from this theme "
                "setting, so they won't automatically match Light or Dark. "
                "Adjust them under Defaults, or per-transcript from the "
                "control band at the bottom of the main window, if you'd "
                "like the reading canvas itself to match."
            ),
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 10))
        # The note leaves 10 below it and the Font heading 10 above it.
        SeparatorLine(scroll, above=10, below=10).pack_line()

        # The font. The notes under the switch come from core/font_choice.py,
        # so their wording is tested without a window.
        ctk.CTkLabel(
            scroll, text="Font", text_color=COCOA_INK, font=self.label_font,
        ).pack(anchor="w", pady=(10, 8))

        self.dyslexia_font_switch = self._styled_switch(scroll, "Use the OpenDyslexic font")
        (self.dyslexia_font_switch.select() if dyslexia_font_enabled else self.dyslexia_font_switch.deselect())
        self.dyslexia_font_switch.pack(anchor="w", pady=(0, 8))

        self.dyslexia_font_notes = []
        for note in font_switch_notes(_app_loads_its_fonts(), DYSLEXIA_FONT_FELL_BACK):
            label = WrappingLabel(scroll, text=note, text_color=COCOA_INK, font=self.small_font)
            label.pack(fill="x", pady=(0, 8))
            self.dyslexia_font_notes.append(label)
        # The last note leaves 8 below it and the Letter spacing heading 10
        # above it.
        SeparatorLine(scroll, above=12, below=10).pack_line()

        # The letter spacing. One button per level, named in core/letter_spacing.py.
        ctk.CTkLabel(
            scroll, text="Letter spacing", text_color=COCOA_INK, font=self.label_font,
        ).pack(anchor="w", pady=(10, 8))

        self.letter_spacing_selector = ctk.CTkSegmentedButton(
            scroll, values=list(LEVEL_NAMES),
            fg_color=WARM_TAUPE, selected_color=EMBER_GLOW, selected_hover_color=EMBER_GLOW_HOVER,
            unselected_color=WARM_TAUPE, unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK, font=self.label_font,
        )
        self.letter_spacing_selector.set(LEVEL_NAMES[clamp_level(letter_spacing_level)])
        self.letter_spacing_selector.pack(fill="x", pady=(0, 10))

        WrappingLabel(
            scroll,
            text=(
                "Adds room between the letters of the flashing word, and between "
                "the words of a chunk. It applies as soon as you press Apply and "
                "is saved in reading profiles. The right amount differs from "
                "person to person, so try the levels by eye."
            ),
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(0, 10))

    # ---- Profiles tab ----

    def _build_profiles_tab(self, tab) -> None:
        """Saved reading profiles (see gui/components/profiles_tab.py). The tab
        does all of its own drawing and only calls back here for the three
        things that belong to this window: running Apply first, the error line,
        and the input grab.

        Saving, updating and applying a profile all start with _handle_apply().
        The other tabs copy their values in when the window opens and only write
        them back on Apply, so without that a profile would miss anything that
        hasn't been applied yet. That is also why this window's own Apply button
        is hidden on this tab (see _update_apply_button()). After a profile has
        been applied the window closes: its controls would otherwise still show
        the old values, and pressing Apply later would quietly write those back
        over the profile."""
        self.profiles_tab = ProfilesTab(
            tab,
            profile_names=self.profile_names,
            on_prepare=self._handle_apply,
            on_save=self.on_profile_save,
            on_update=self.on_profile_update,
            on_apply=self.on_profile_apply,
            on_applied=self.destroy,
            on_rename=self.on_profile_rename,
            on_delete=self.on_profile_delete,
            on_message=self._show_message,
            on_popup_closed=self._handle_profile_popup_closed,
        )
        self.profiles_tab.pack(fill="both", expand=True, padx=(8, 4))

    def _show_message(self, text: str) -> None:
        """Put text on the red line at the bottom of the window, or clear it
        when text is empty."""
        self.error_label.configure(text=text)

    def _handle_profile_popup_closed(self) -> None:
        """A popup opened from the Profiles tab is gone. Its own input grab
        replaced this window's, and destroying it does not give that back, so
        take it again (the same hand-back as _handle_about_closed)."""
        self.after(50, self._regrab_if_still_open)

    # ---- Stats tab ----

    def _build_stats_tab(self, tab, transcripts) -> None:
        """Read-only overview of per-transcript reading stats (see
        core/models.py's times_read / total_words_read /
        total_time_spent_seconds, and TranscriptStore.add_session_stats()).
        Deliberately shows every transcript across every space, not just
        the currently selected one: this window has no notion of "the
        current space" anywhere else, so silently filtering here would
        look like missing data rather than a deliberate scope. Sorted by
        time spent, descending, so what's actually been read surfaces
        first and untouched transcripts (all zeros) settle to the bottom.

        The explanatory label at the top exists because these numbers are
        not live: they're only reported to the store when a reading
        session actually ends (gui/components/canvas.py calls
        reader_display.stop(), which reports them, from the Stop button,
        switching transcripts, detaching, or deleting, plus a direct
        finalize_session() call on app close). Pausing only stops the
        active-time clock; it does not report anything, so pausing
        mid-read and opening Settings shows stale numbers, hence spelling
        that out here instead of leaving it to look like a bug."""
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=(0, 0))

        WrappingLabel(
            scroll,
            text=(
                "These totals update once a reading session ends, by "
                "clicking Stop, switching to another transcript, detaching "
                "the window, or closing the app, not while it's simply "
                "paused. If you've been reading and want the latest "
                "numbers, stop or switch away from the transcript first, "
                "then reopen Settings."
            ),
            text_color=COCOA_INK, font=self.small_font,
        ).pack(fill="x", pady=(5, 15))

        if not transcripts:
            ctk.CTkLabel(
                scroll, text="No transcripts yet.",
                text_color=COCOA_INK, font=self.label_font,
            ).pack(anchor="w", pady=(10, 0))
            return

        ordered = sorted(transcripts, key=lambda t: (-t.total_time_spent_seconds, t.title.lower()))

        for t in ordered:
            row = ctk.CTkFrame(scroll, fg_color=WARM_TAUPE, corner_radius=8)
            row.pack(fill="x", pady=(0, 8))

            WrappingLabel(
                row, text=f"{t.title}  ·  {t.space}",
                text_color=COCOA_INK, font=self.label_font,
            ).pack(fill="x", padx=12, pady=(10, 2))

            reads_word = "read" if t.times_read == 1 else "reads"
            stats_text = (
                f"{t.times_read} {reads_word}  ·  "
                f"{t.total_words_read:,} words read  ·  "
                f"{format_duration(t.total_time_spent_seconds)} total"
            )
            WrappingLabel(
                row, text=stats_text,
                text_color=COCOA_INK, font=self.small_font,
            ).pack(fill="x", padx=12, pady=(0, 10))

    # ---- Apply ----

    def _handle_apply(self) -> bool:
        """Check what is typed and chosen in the tabs and, if it is all fine,
        hand it to the app to apply. Returns whether that happened. On a bad
        value it shows the reason on the error line, applies nothing and returns
        False. The Apply button ignores the result; the Profiles tab uses it to
        stop when there is something to fix first."""
        entries = {
            "window_width": (self.window_width_entry, *WINDOW_WIDTH_RANGE),
            "window_height": (self.window_height_entry, *WINDOW_HEIGHT_RANGE),
            "sidebar_width": (self.sidebar_width_entry, *SIDEBAR_WIDTH_RANGE),
            "bottom_band_height": (self.bottom_band_height_entry, *BOTTOM_BAND_HEIGHT_RANGE),
            "font_size_step": (self.font_size_step_entry, *FONT_SIZE_STEP_RANGE),
            "guide_mark_thickness_px": (self.guide_mark_thickness_entry, *GUIDE_MARK_THICKNESS_RANGE),
            "resume_rewind_words": (self.resume_rewind_words_entry, *RESUME_REWIND_WORDS_RANGE),
        }

        values = {}
        for key, (entry, low, high) in entries.items():
            text = entry.get().strip()
            label = key.replace("_", " ").title()
            if not text.isdigit():
                self.error_label.configure(text=f"{label} must be a whole number.")
                return False
            number = int(text)
            if not (low <= number <= high):
                self.error_label.configure(text=f"{label} must be between {low} and {high}.")
                return False
            values[key] = number

        offset_text = self.highlight_offset_entry.get().strip()
        digits = offset_text[1:] if offset_text.startswith("-") else offset_text
        offset_value = int(offset_text) if digits and digits.isdigit() else None
        low, high = HIGHLIGHT_OFFSET_RANGE
        if offset_value is None:
            self.error_label.configure(text="Highlight Position must be a whole number.")
            return False
        if not (low <= offset_value <= high):
            self.error_label.configure(text=f"Highlight Position must be between {low} and {high}.")
            return False
        values["highlight_offset_px"] = offset_value

        values["freeform_resize_enabled"] = bool(self.freeform_switch.get())
        values["default_wpm"] = int(self.default_wpm_slider.get())
        values["default_font_color"] = self.default_font_color
        values["default_highlight_color"] = self.default_highlight_color
        values["default_background_color"] = self.default_background_color
        values["default_font_size"] = self.default_font_size
        values["skip_word_count"] = int(self.skip_word_count_slider.get())
        values["pause_on_skip"] = bool(self.pause_on_skip_switch.get())
        values["guide_mark_horizontal_enabled"] = bool(self.guide_mark_horizontal_switch.get())
        values["length_pacing_enabled"] = bool(self.length_pacing_switch.get())
        values["split_long_paragraphs_enabled"] = bool(self.split_long_paragraphs_switch.get())
        values["warm_up_enabled"] = bool(self.warm_up_switch.get())
        values["resume_rewind_enabled"] = bool(self.resume_rewind_switch.get())
        values["scrub_pause_enabled"] = bool(self.scrub_pause_switch.get())
        values["peripheral_context_enabled"] = bool(self.peripheral_context_switch.get())
        values["guide_mark_length_percent"] = self.default_guide_mark_length_percent
        values["guide_mark_color"] = self.default_guide_mark_color
        values["data_directory"] = self._data_directory
        values["appearance_mode"] = self.appearance_mode_selector.get().lower()
        values["dyslexia_font_enabled"] = bool(self.dyslexia_font_switch.get())
        values["letter_spacing_level"] = LEVEL_NAMES.index(self.letter_spacing_selector.get())

        self.error_label.configure(text="")
        self.on_apply(values)
        return True