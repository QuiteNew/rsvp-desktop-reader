import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY, apply_app_icon, center_over_parent


class MessageDialog(ctk.CTkToplevel):
    """A single-button popup for telling the user something -- an error
    ("that file isn't a valid export"), a confirmation ("export saved
    to..."), or a notice that has to be acknowledged before something
    else happens (see on_close below). None of the app's other popups
    are generic like this; they're all single-purpose (confirm a
    delete, collect a new space name, etc.). This one exists because
    Export/Import (see gui/components/import_confirm_dialog.py and
    gui/app.py) need to surface plain messages, and building a
    one-off dialog for each message would just be this same shape
    copy-pasted repeatedly.

    on_close, if given, fires after the dialog is dismissed -- by the
    button OR by the window's own OS close control, deliberately treated
    the same way here (see the WM_DELETE_WINDOW binding below). That
    matters for the one caller that actually needs it: after a data
    import, the change has already happened by the time this dialog
    appears, and the app needs to close right afterward regardless of
    which way the user dismisses the message -- there's no "cancel" to
    go back to at that point, unlike every other dialog in this app."""

    def __init__(self, master, title, message, on_close=None, button_text="OK"):
        super().__init__(master)

        # See gui/components/delete_transcript_dialog.py for the fuller
        # explanation of why this uses -alpha rather than
        # withdraw()/deiconify() to stay hidden until fully built.
        self.attributes("-alpha", 0)

        self.title(title)
        apply_app_icon(self)
        center_over_parent(self, 380, 190)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_close = on_close

        # Deliberately routes the window manager's own close control
        # through the same handler as the button -- see the class
        # docstring above.
        self.protocol("WM_DELETE_WINDOW", self._handle_dismiss)

        message_font = ctk.CTkFont(family=FONT_BODY, size=13)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(
            self, text=message, text_color=COCOA_INK, font=message_font,
            wraplength=340, justify="left",
        ).pack(padx=20, pady=(25, 20))

        ctk.CTkButton(
            self, text=button_text, width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_dismiss,
        ).pack(pady=(0, 20))

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # See delete_transcript_dialog.py's matching comment -- same
        # reasoning, same delay.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def _handle_dismiss(self) -> None:
        self.destroy()
        if self.on_close:
            self.on_close()