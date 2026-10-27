import customtkinter as ctk

from core.colors import blend_colors
from core.profiles import ProfileError
from gui.components.profile_confirm_dialog import ProfileConfirmDialog
from gui.components.profile_name_dialog import ProfileNameDialog
from gui.components.wrapping_label import WrappingLabel
from gui.theme import COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY

# Explains what a profile is, and what it is not. The second part matters: a
# person who reads "profile" may expect it to change their transcripts or their
# colours, and it changes neither. Speed and Word size are the two sliders on the
# Defaults tab, so they only set where a new transcript starts, which is why the
# text says so.
EXPLANATION = (
    "A profile is a saved set of reader settings: the guide marks, pacing, "
    "rewind on resume, surrounding words, skipping, the +/- step, the "
    "scrubber and paragraph switches, the letter spacing, and the Speed and "
    "Word size sliders. "
    "Applying one never changes a transcript, your colours or chunking, and "
    "Speed and Word size only set where new transcripts start. To keep "
    "different texts apart, use spaces."
)

# Saving, updating or applying a profile starts by applying whatever has been
# changed in the other tabs (see ProfilesTab's on_prepare). This says so up
# front, so it doesn't come as a surprise. The Settings window hides its own
# Apply button on this tab, so the note doesn't point at it.
APPLY_FIRST_NOTE = (
    "Saving, updating or applying a profile first applies any changes you've "
    "made in the other tabs."
)

# How tall the list asks to be. It grows to fill the tab when there is room, and
# this is all it needs at the smallest Settings window, where it scrolls.
LIST_MIN_HEIGHT = 50


class ProfilesTab(ctk.CTkFrame):
    """The Profiles tab of the Settings window: a short explanation, a button
    to save the current settings as a new profile, the list of saved profiles,
    and buttons to apply, update, rename or delete the one that is selected.

    Clicking a row selects its profile, and clicking the selected row again
    unselects it, which switches the four action buttons back off.

    This class only deals with what is on screen. It knows nothing about stores
    or the reader, everything real goes through the callbacks it is given, which
    the Settings window passes on from gui/app.py:

    - profile_names() gives the saved names, in order.
    - on_prepare() makes sure the app already has whatever is typed in the other
      tabs, by running the Settings window's own Apply. It returns False if that
      failed (a bad number, say, which it has already reported). It is called
      before saving, updating or applying, because those use the app's current
      settings and would otherwise miss changes that haven't been applied yet.
    - on_save(name), on_update(name), on_apply(name), on_rename(name, new_name)
      and on_delete(name) do the work. They may raise ProfileError with a
      message that is fine to show, which ends up in on_message.
    - on_applied() runs after a profile has been applied. The Settings window
      closes itself there: its other tabs still show the old values, and pressing
      Apply later would otherwise write those back over the profile.
    - on_message(text) shows a line of text in the Settings window's error
      line, or clears it when the text is empty.
    - on_popup_closed() runs after one of this tab's popups goes away, so the
      Settings window can take back the input grab."""

    def __init__(
        self, master, *, profile_names, on_prepare, on_save, on_update, on_apply,
        on_applied, on_rename, on_delete, on_message, on_popup_closed,
    ):
        super().__init__(master, fg_color="transparent")

        self._profile_names = profile_names
        self._on_prepare = on_prepare
        self._on_save = on_save
        self._on_update = on_update
        self._on_apply = on_apply
        self._on_applied = on_applied
        self._on_rename = on_rename
        self._on_delete = on_delete
        self._on_message = on_message
        self._on_popup_closed = on_popup_closed

        self._selected = None  # name of the selected profile, or None
        self._rows = {}  # profile name -> its button in the list
        self._popup = None  # the name or confirm popup while one is open

        self.label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self.small_font = ctk.CTkFont(family=FONT_BODY, size=11)
        self.button_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self._disabled_text = blend_colors(COCOA_INK, WARM_TAUPE, 0.45)

        # Both notes wrap to the width the tab has, the same way as the
        # descriptions on the other Settings tabs (see wrapping_label.py).
        WrappingLabel(self, text=EXPLANATION, text_color=COCOA_INK, font=self.small_font).pack(fill="x", pady=(5, 4))
        WrappingLabel(self, text=APPLY_FIRST_NOTE, text_color=COCOA_INK, font=self.small_font).pack(fill="x", pady=(0, 8))

        self.save_button = self._make_button(self, "Save current settings as…", self._handle_save_clicked, width=200)
        self.save_button.pack(anchor="w", pady=(0, 8))

        # The action buttons are packed before the list, on the bottom edge. Pack
        # hands out space in the order widgets are packed, so doing it this way
        # keeps the buttons on screen when the window is small and lets the list,
        # which scrolls anyway, take whatever is left.
        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(side="bottom", fill="x", pady=(8, 4))
        self.apply_button = self._make_button(action_row, "Apply", self._handle_apply_clicked, width=82)
        self.update_button = self._make_button(action_row, "Update", self._handle_update_clicked, width=82)
        self.rename_button = self._make_button(action_row, "Rename", self._handle_rename_clicked, width=82)
        self.delete_button = self._make_button(action_row, "Delete", self._handle_delete_clicked, width=82)
        self._action_buttons = [self.apply_button, self.update_button, self.rename_button, self.delete_button]
        for button in self._action_buttons:
            button.pack(side="left", padx=(0, 8))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=WARM_TAUPE, corner_radius=8, height=LIST_MIN_HEIGHT)
        self.list_frame.pack(fill="both", expand=True)
        # A CTkScrollableFrame's scrollbar asks for 200px of height whatever
        # height the frame is given, which would make this tab ask for far more
        # room than the smallest Settings window has and push the Close and Apply
        # buttons off the bottom. Ask for a short one instead. The list still
        # stretches to fill whatever space is left. Reaches into the private
        # _scrollbar, and if that name ever changes the only effect is that the
        # list asks for more room again.
        try:
            self.list_frame._scrollbar.configure(height=LIST_MIN_HEIGHT)
        except AttributeError:
            pass

        self.refresh()

    # ---- What the tab shows ----

    @property
    def selected_name(self):
        """The name of the selected profile, or None when nothing is selected."""
        return self._selected

    def refresh(self, select=None) -> None:
        """Rebuild the list from the saved profiles. select names a profile to
        select, for example one that was just saved or renamed. Otherwise the
        current selection is kept if that profile is still there."""
        names = list(self._profile_names())
        if select is not None:
            self._selected = select
        if self._selected not in names:
            self._selected = None

        for child in self.list_frame.winfo_children():
            child.destroy()
        self._rows = {}

        if not names:
            WrappingLabel(
                self.list_frame,
                text="No profiles yet. Set things up the way you like in Settings, then save them here.",
                text_color=COCOA_INK, font=self.small_font,
            ).pack(fill="x", padx=8, pady=8)
        for name in names:
            self._add_row(name)

        self._show_selection()

    def select(self, name) -> None:
        """Select the profile with this name. Always selects, even if it is
        already the selected one; a click on a row goes through
        _handle_row_clicked() instead, which can also unselect."""
        if name in self._rows:
            self._selected = name
            self._show_selection()

    def deselect(self) -> None:
        """Unselect whatever is selected, so nothing is, and the action buttons
        switch off. Harmless when nothing is selected."""
        self._selected = None
        self._show_selection()

    def _handle_row_clicked(self, name: str) -> None:
        """A click on a row. Clicking the selected row again unselects it,
        anything else selects the row clicked."""
        if name == self._selected:
            self.deselect()
        else:
            self.select(name)

    def _add_row(self, name: str) -> None:
        """One row of the list, a button that selects its profile. Its own
        method rather than a loop body in refresh() so the lambda closes over
        this call's name, not whichever name the loop reached last (the same
        reason SpaceSelectionDialog builds its rows this way)."""
        button = ctk.CTkButton(
            self.list_frame, text=name, anchor="w", height=30, corner_radius=6,
            fg_color="transparent", hover_color=WARM_LINE, text_color=COCOA_INK,
            font=self.label_font, command=lambda: self._handle_row_clicked(name),
        )
        button.pack(fill="x", pady=2, padx=4)
        self._rows[name] = button

    def _show_selection(self) -> None:
        """Mark the selected row, and switch the action buttons on only while
        something is selected."""
        for name, button in self._rows.items():
            if name == self._selected:
                button.configure(fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER)
            else:
                button.configure(fg_color="transparent", hover_color=WARM_LINE)

        for button in self._action_buttons:
            if self._selected is None:
                button.configure(state="disabled", fg_color=WARM_TAUPE, text_color_disabled=self._disabled_text)
            else:
                button.configure(state="normal", fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK)

    def _make_button(self, master, text, command, width) -> ctk.CTkButton:
        return ctk.CTkButton(
            master, text=text, width=width, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=command,
        )

    # ---- Buttons ----

    def _handle_save_clicked(self) -> None:
        if self._popup_is_open() or not self._on_prepare():
            return
        self._open_name_dialog("Save Profile", "Save", self._save_named)

    def _handle_apply_clicked(self) -> None:
        name = self._selected
        if name is None or self._popup_is_open() or not self._on_prepare():
            return
        if self._run(self._on_apply, name):
            # The Settings window closes here, so nothing below may touch it.
            self._on_applied()

    def _handle_update_clicked(self) -> None:
        name = self._selected
        if name is None or self._popup_is_open() or not self._on_prepare():
            return
        self._popup = ProfileConfirmDialog(
            self.winfo_toplevel(), "Update Profile",
            f'Replace what "{name}" holds with the settings you are using now? The old settings can\'t be brought back.',
            "Update", on_confirm=lambda: self._run(self._on_update, name),
            on_close=self._handle_popup_closed,
        )

    def _handle_rename_clicked(self) -> None:
        name = self._selected
        if name is None or self._popup_is_open():
            return
        self._open_name_dialog(
            "Rename Profile", "Rename", lambda new_name: self._rename(name, new_name),
            initial_name=name, own_name=name,
        )

    def _handle_delete_clicked(self) -> None:
        name = self._selected
        if name is None or self._popup_is_open():
            return
        self._popup = ProfileConfirmDialog(
            self.winfo_toplevel(), "Delete Profile",
            f'Delete the profile "{name}"? This can\'t be undone.',
            "Delete", on_confirm=lambda: self._delete(name), destructive=True,
            on_close=self._handle_popup_closed,
        )

    # ---- Doing the work ----

    def _save_named(self, name: str) -> None:
        if self._run(self._on_save, name):
            self.refresh(select=name)

    def _rename(self, name: str, new_name: str) -> None:
        if new_name == name:
            return
        if self._run(self._on_rename, name, new_name):
            self.refresh(select=new_name)

    def _delete(self, name: str) -> None:
        if self._run(self._on_delete, name):
            self._selected = None
            self.refresh()

    def _run(self, action, *args) -> bool:
        """Run one of the callbacks. A ProfileError (a name that turned out to be
        taken, a profile that is no longer there) is shown in the Settings
        window's error line instead of being raised, and the list is rebuilt so
        it matches what is really saved. Returns whether the action worked."""
        try:
            action(*args)
        except ProfileError as problem:
            self._on_message(str(problem))
            self.refresh()
            return False
        self._on_message("")
        return True

    # ---- Popups ----

    def _popup_is_open(self) -> bool:
        """Only one popup at a time. A popup takes its input grab a few
        milliseconds after it appears, so a quick second click could otherwise
        open another before the first is in the way."""
        return self._popup is not None and self._popup.winfo_exists()

    def _open_name_dialog(self, title, button_text, on_submit, initial_name="", own_name=None) -> None:
        self._popup = ProfileNameDialog(
            self.winfo_toplevel(), title, button_text, self._profile_names(), on_submit,
            initial_name=initial_name, own_name=own_name, on_close=self._handle_popup_closed,
        )

    def _handle_popup_closed(self) -> None:
        self._popup = None
        self._on_popup_closed()