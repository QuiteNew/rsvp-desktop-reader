import customtkinter as ctk

from core.profiles import clean_name, name_problem
from gui.components.dialog_keys import bind_dialog_keys, focus_for_typing
from gui.theme import (
    HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER,
    FONT_BODY, apply_app_icon, center_over_parent,
)

# The same red the Settings window uses for its error line.
ERROR_COLOR = "#E74C3C"


class ProfileNameDialog(ctk.CTkToplevel):
    """Popup that asks for a profile's name. The same dialog is used to save a
    new profile and to rename an existing one, so the title, the button text
    and the starting name are all passed in.

    The name is checked with core/profiles.py's name_problem() when the button
    is pressed. If it can't be used (empty, too long, or already taken), the
    reason is shown under the box and the dialog stays open, so a typo doesn't
    cost the person the whole dialog. When renaming, pass the profile's current
    name as own_name so that keeping it, or only changing its capitals, isn't
    reported as a clash with itself.

    on_submit gets the cleaned-up name. on_close, if given, is called once after
    the dialog is gone however it was closed (the Settings window uses it to
    take back the input grab, see AboutDialog for the same arrangement)."""

    def __init__(
        self, master, title, button_text, existing_names, on_submit,
        initial_name="", own_name=None, on_close=None,
    ):
        super().__init__(master)

        # Hidden until fully built, see gui/components/settings_window.py for
        # why this uses -alpha rather than withdraw()/deiconify().
        self.attributes("-alpha", 0)

        self.title(title)
        apply_app_icon(self)
        center_over_parent(self, 340, 220)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_submit = on_submit
        self.on_close = on_close
        self._existing_names = list(existing_names)
        self._own_name = own_name

        # The window's own close control does the same as Cancel.
        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)

        label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        small_font = ctk.CTkFont(family=FONT_BODY, size=11)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(self, text="Profile name", text_color=COCOA_INK, font=label_font).pack(anchor="w", padx=20, pady=(20, 4))

        self.name_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. Fast skim",
            fg_color=WARM_TAUPE, border_color=WARM_LINE, border_width=1,
            text_color=COCOA_INK, font=label_font,
        )
        self.name_entry.pack(fill="x", padx=20)
        if initial_name:
            self.name_entry.insert(0, initial_name)

        self.error_label = ctk.CTkLabel(
            self, text="", text_color=ERROR_COLOR, font=small_font,
            wraplength=300, justify="left", anchor="w",
        )
        self.error_label.pack(fill="x", padx=20, pady=(6, 0))

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=(8, 20))

        ctk.CTkButton(
            button_row, text="Cancel", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_cancel,
        ).pack(side="left")
        ctk.CTkButton(
            button_row, text=button_text, width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_submit,
        ).pack(side="right")

        # Enter saves and Esc cancels. Enter used to be bound on the name box
        # alone; bound on the popup it works wherever the cursor is, so the box
        # no longer needs its own.
        bind_dialog_keys(self, on_enter=self._handle_submit, on_escape=self._handle_cancel)

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # Same delayed reveal as the other popups, see delete_transcript_dialog.py.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        if not self.winfo_exists():
            return
        self.update_idletasks()
        self.attributes("-alpha", 1)
        # The cursor goes in the box so the person can type straight away. When
        # renaming, the current name is selected so typing replaces it. The
        # helper waits a moment first, see focus_for_typing() for why.
        focus_for_typing(self.name_entry, select=True)

    def _handle_submit(self, _event=None) -> None:
        name = self.name_entry.get()
        problem = name_problem(name, self._existing_names, self._own_name)
        if problem:
            self.error_label.configure(text=problem)
            return
        self.destroy()
        self.on_submit(clean_name(name))
        if self.on_close:
            self.on_close()

    def _handle_cancel(self) -> None:
        self.destroy()
        if self.on_close:
            self.on_close()