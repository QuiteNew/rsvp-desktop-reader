import tkinter

import customtkinter as ctk
from core.text_fit import fit_text
from gui.theme import WARM_TAUPE, COCOA_INK, WARM_LINE, FONT_HEADING, FONT_BODY


class Header(ctk.CTkFrame):
    """Slim top row: active transcript name (left) and a settings button (right).

    A title is cut down with an ellipsis when it is longer than the room beside
    the button, so a long one (a file import names the transcript after the
    file) can never push the button out of the row."""

    def __init__(self, master, on_settings=None):
        super().__init__(master, fg_color=WARM_TAUPE, corner_radius=0)
        self.on_settings = on_settings
        self._full_title = "No transcript selected"

        # The button is packed before the title on purpose. Pack gives space
        # in the order widgets are packed, and a label asks for as much width
        # as its whole text needs, so a long title packed first would take the
        # entire row and leave the button none. Packed first, the button keeps
        # its place, and the title only gets what is left.
        button_font = ctk.CTkFont(family=FONT_BODY, size=12)
        self.settings_button = ctk.CTkButton(
            self, text="Settings", width=80, corner_radius=10,
            fg_color="transparent", border_width=1, border_color=WARM_LINE,
            text_color=COCOA_INK, hover_color=WARM_LINE, font=button_font,
            command=self._handle_settings,
        )
        self.settings_button.pack(side="right", padx=15, pady=18)

        title_font = ctk.CTkFont(family=FONT_HEADING, size=16)
        self.title_label = ctk.CTkLabel(
            self, text=self._full_title, anchor="w", text_color=COCOA_INK, font=title_font,
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=(15, 0), pady=18)

        # Added next to CustomTkinter's own handler on the label's frame, never
        # in its place (CTkLabel.bind() would bind the inner widgets instead,
        # see gui/components/wrapping_label.py). The title is fitted again
        # whenever the room for it changes, such as when the window is resized.
        tkinter.Frame.bind(self.title_label, "<Configure>", self._fit_title, add="+")

        # A plain label that is never placed on screen. It is only used to ask
        # Tk how wide a piece of text would be drawn, see _text_width().
        self._ruler = tkinter.Label(self, bd=0, padx=0, pady=0, highlightthickness=0)

    def set_title(self, title: str) -> None:
        self._full_title = title
        self._fit_title()

    def _fit_title(self, event=None) -> None:
        """Show as much of the full title as fits. Always starts again from the
        full title, so a title cut down in a narrow window comes back in full
        when the window is made wider.

        The room is the label's width in real screen pixels, and the text is
        measured in the same unit by _text_width(), so no scaling is done
        here."""
        available = event.width if event is not None else self.title_label.winfo_width()
        if available <= 1:
            # Not laid out yet. Show the full title for now; the first resize
            # event brings the real width and cuts it if needed.
            shown = self._full_title
        else:
            shown = fit_text(self._full_title, available, self._text_width)
        if shown != self.title_label.cget("text"):
            self.title_label.configure(text=shown)

    def _text_width(self, text: str) -> int:
        """How wide the title label would draw this text, in real screen pixels.

        It asks a label set up the way the title's inner label is, with the
        font the title label is using right now (that font already has the
        display scaling applied). A font object made from the same description
        gave a width a little off from what the label really draws, by about
        2% at a 150% display, which let the cut text run past the room it was
        cut for. Asking a label gives the width the real one will have."""
        self._ruler.configure(font=self.title_label._label.cget("font"), text=text)
        return self._ruler.winfo_reqwidth()

    def _handle_settings(self) -> None:
        if self.on_settings:
            self.on_settings()