import customtkinter as ctk

from gui.theme import HEARTH_PAPER, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY, apply_app_icon, center_over_parent


class ProfileConfirmDialog(ctk.CTkToplevel):
    """Yes or no popup for the two profile actions that can't be taken back:
    deleting a profile, and updating one with the current settings (which
    replaces what it held). The message is passed in, so one dialog serves
    both. destructive paints the confirm button red, the same red as the other
    delete dialogs, and is meant for deleting.

    on_confirm runs only on the confirm button. on_close, if given, runs once
    after the dialog is gone however it was closed, so the Settings window can
    take back the input grab (see AboutDialog for the same arrangement)."""

    def __init__(self, master, title, message, confirm_text, on_confirm, destructive=False, on_close=None):
        super().__init__(master)

        # Hidden until fully built, see gui/components/settings_window.py for
        # why this uses -alpha rather than withdraw()/deiconify().
        self.attributes("-alpha", 0)

        self.title(title)
        apply_app_icon(self)
        center_over_parent(self, 360, 180)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_confirm = on_confirm
        self.on_close = on_close

        # The window's own close control does the same as Cancel.
        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)

        message_font = ctk.CTkFont(family=FONT_BODY, size=13)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(
            self, text=message, text_color=COCOA_INK, font=message_font,
            wraplength=320, justify="left",
        ).pack(padx=20, pady=(25, 20))

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            button_row, text="Cancel", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_cancel,
        ).pack(side="left")

        if destructive:
            confirm_colors = {"fg_color": "#A33636", "hover_color": "#7E2929", "text_color": "#FFFFFF"}
        else:
            confirm_colors = {"fg_color": EMBER_GLOW, "hover_color": EMBER_GLOW_HOVER, "text_color": COCOA_INK}
        self.confirm_button = ctk.CTkButton(
            button_row, text=confirm_text, width=90, corner_radius=10,
            font=button_font, command=self._handle_confirm, **confirm_colors,
        )
        self.confirm_button.pack(side="right")

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # Same delayed reveal as the other popups, see delete_transcript_dialog.py.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def _handle_confirm(self) -> None:
        self.destroy()
        self.on_confirm()
        if self.on_close:
            self.on_close()

    def _handle_cancel(self) -> None:
        self.destroy()
        if self.on_close:
            self.on_close()