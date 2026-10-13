import tkinter as tk

import customtkinter as ctk

from core.colors import blend_colors
from gui.icons import clear_icon
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, FONT_BODY


class SearchBox(ctk.CTkFrame):
    """A one-line search box with a small clear ("X") button inside its right
    end. Shared by the transcript list and the Settings window so both look and
    behave the same.

    It is one rounded, bordered frame holding a borderless entry, with the X
    packed beside the entry rather than drawn on top of it, so typed text can
    never run underneath the X. The X only shows while there is something to
    clear.

    The hint ("Search…") is drawn here instead of using CTkEntry's own
    placeholder_text. CustomTkinter only activates that placeholder when the
    entry has no textvariable (it compares the variable object to ""), and the
    live search needs a textvariable so that typing, pasting, cutting and
    clearing all report the same way. Callers read and watch `variable`, the
    same StringVar pattern the transcript list already used."""

    HEIGHT = 28
    CORNER_RADIUS = 6  # CTkEntry's own default, so the box matches a plain entry

    def __init__(self, master, placeholder_text: str = "Search…"):
        # width is only a small requested size: the caller packs this with
        # fill="x", so the real width comes from the space it is given. The
        # height is fixed (pack_propagate off) to match the 28px buttons that
        # sit beside it.
        super().__init__(
            master, width=10, height=self.HEIGHT, corner_radius=self.CORNER_RADIUS,
            border_width=1, border_color=WARM_LINE, fg_color=HEARTH_PAPER,
        )
        self.pack_propagate(False)

        self.variable = tk.StringVar()
        self._clear_visible = False

        # Between the ink and the paper colour, so it reads as greyed out in
        # both the light and the dark theme (a fixed grey would be right in
        # only one of them).
        muted = blend_colors(COCOA_INK, HEARTH_PAPER, 0.55)
        font = ctk.CTkFont(family=FONT_BODY, size=13)

        # The entry's own border is off and its fill is transparent, so only
        # this frame's border shows. The 3px side inset keeps the entry's square
        # canvas clear of this frame's rounded corners.
        self._entry = ctk.CTkEntry(
            self, textvariable=self.variable, height=self.HEIGHT - 2,
            border_width=0, fg_color="transparent", text_color=COCOA_INK, font=font,
        )
        self._entry.pack(side="left", fill="both", expand=True, padx=(3, 3), pady=1)

        self._hint = ctk.CTkLabel(self, text=placeholder_text, text_color=muted, font=font, cursor="xterm")
        self._hint.place(x=9, rely=0.5, anchor="w")

        self._clear_rest_icon = clear_icon(10, muted)
        self._clear_hover_icon = clear_icon(10, COCOA_INK)
        self._clear_button = ctk.CTkButton(
            self, text="", image=self._clear_rest_icon, width=20, height=20, corner_radius=6,
            fg_color="transparent", hover_color=WARM_TAUPE, cursor="hand2", command=self.clear,
        )
        self._clear_button.bind("<Enter>", lambda _event: self._clear_button.configure(image=self._clear_hover_icon))
        self._clear_button.bind("<Leave>", lambda _event: self._clear_button.configure(image=self._clear_rest_icon))

        # Clicking anywhere on the box, including its border and the hint,
        # puts the cursor in the entry.
        for widget in (self, self._hint):
            widget.bind("<Button-1>", lambda _event: self._entry.focus_set())

        self.variable.trace_add("write", lambda *_args: self._sync())
        self._sync()

    def get(self) -> str:
        """The text currently typed."""
        return self.variable.get()

    def clear(self) -> None:
        """Empties the box and leaves the cursor in it, ready to type again."""
        self.variable.set("")
        self._entry.focus_set()

    def focus_entry(self) -> None:
        self._entry.focus_set()

    def _sync(self) -> None:
        """Shows the X (and hides the hint) while there is text, and the other
        way round when empty."""
        has_text = bool(self.variable.get())
        if has_text == self._clear_visible:
            return
        self._clear_visible = has_text
        if has_text:
            self._hint.place_forget()
            # before= puts the X ahead of the entry in the packing order, so it
            # claims its slot at the right edge first and the entry fills what
            # is left. Packed after the entry it would be squeezed out.
            self._clear_button.pack(side="right", padx=(0, 3), before=self._entry)
        else:
            self._clear_button.pack_forget()
            # Hidden while the pointer may have been over it, so no leave event
            # will ever arrive: put it back to its resting look now, or it
            # would reappear still showing the hover chip.
            self._clear_button.configure(image=self._clear_rest_icon)
            try:
                self._clear_button._on_leave()
            except AttributeError:
                pass
            self._hint.place(x=9, rely=0.5, anchor="w")