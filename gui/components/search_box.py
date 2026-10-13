import customtkinter as ctk

from gui.icons import clear_icon
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_LINE, FONT_BODY
from core.colors import blend_colors


class SearchBox(ctk.CTkFrame):
    """A one-line search box with a small clear ("X") button at its right end.
    Shared by the transcript list and the Settings window so both look and
    behave the same.

    It is a single ordinary CTkEntry (its own paper fill, border and "Search…"
    placeholder) with the X laid over its right end. Nothing is nested inside
    the entry and nothing is drawn on top of its text, so it renders exactly
    like any other entry in the app: one border, one set of rounded corners,
    the placeholder sitting where typed text sits.

    The box does not use a textvariable. CustomTkinter only shows an entry's
    placeholder when it has no textvariable, and the placeholder is worth more
    than the convenience of a traced variable. Instead the caller passes
    on_change, which is called after every change to the text (typing, pasting,
    cutting, or the X), and reads the text with get(). get() returns "" while
    the placeholder is showing, so an empty box always reads as an empty
    query."""

    HEIGHT = 28

    def __init__(self, master, placeholder_text: str = "Search…", on_change=None):
        # A plain transparent wrapper, sized to the entry, that gives the X a
        # place to sit over the entry's right end. width is only a small
        # request; the caller packs this with fill="x", so the real width is
        # whatever space it is given.
        super().__init__(master, width=10, height=self.HEIGHT, fg_color="transparent")
        self.pack_propagate(False)

        self._on_change = on_change

        font = ctk.CTkFont(family=FONT_BODY, size=13)
        self._entry = ctk.CTkEntry(
            self, placeholder_text=placeholder_text, height=self.HEIGHT,
            fg_color=HEARTH_PAPER, border_color=WARM_LINE, border_width=1,
            text_color=COCOA_INK, font=font,
        )
        self._entry.pack(fill="both", expand=True)

        # The X is laid over the entry's right end rather than packed beside it,
        # so it sits inside the one field. Its fill is the entry's own paper
        # colour, so at rest only the little grey glyph shows; hovering gives it
        # a soft chip. Greyed at rest, full ink on hover, with the grey blended
        # from the theme so it reads in both light and dark mode.
        muted = blend_colors(COCOA_INK, HEARTH_PAPER, 0.55)
        self._clear_rest_icon = clear_icon(10, muted)
        self._clear_hover_icon = clear_icon(10, COCOA_INK)
        self._clear_button = ctk.CTkButton(
            self, text="", image=self._clear_rest_icon, width=20, height=20, corner_radius=6,
            fg_color=HEARTH_PAPER, hover_color=WARM_LINE, cursor="hand2", command=self.clear,
        )
        self._clear_button.bind("<Enter>", lambda _event: self._clear_button.configure(image=self._clear_hover_icon))
        self._clear_button.bind("<Leave>", lambda _event: self._clear_button.configure(image=self._clear_rest_icon))
        self._clear_visible = False

        # Every way the text can change without a textvariable: a key going up
        # catches typing, backspace, delete and Ctrl+V/Ctrl+X; the virtual
        # events catch a paste, cut or clear from the right-click menu, which
        # fire no key event. All land on the same handler, which is idempotent,
        # so a paste firing both is harmless.
        for sequence in ("<KeyRelease>", "<<Paste>>", "<<Cut>>", "<<Clear>>"):
            self._entry.bind(sequence, self._on_entry_event)

    def get(self) -> str:
        """The text currently typed, or "" while the placeholder is showing."""
        return self._entry.get()

    def clear(self) -> None:
        """Empties the box and leaves the cursor in it, ready to type again."""
        self._entry.delete(0, "end")
        self._entry.focus_set()
        self._changed()

    def set_text(self, text: str) -> None:
        """Replaces the text, as if it had been typed. For callers and tests
        that drive the box directly."""
        self._entry.delete(0, "end")
        self._entry.insert(0, text)
        self._changed()

    def focus_entry(self) -> None:
        self._entry.focus_set()

    def _on_entry_event(self, _event=None) -> None:
        self._changed()

    def _changed(self) -> None:
        """Shows or hides the X to match whether there is text, then tells the
        caller the text changed."""
        self._update_clear_button()
        if self._on_change is not None:
            self._on_change()

    def _update_clear_button(self) -> None:
        has_text = bool(self.get())
        if has_text == self._clear_visible:
            return
        self._clear_visible = has_text
        if has_text:
            # Over the entry's right end, a few pixels in from the border.
            self._clear_button.place(relx=1.0, rely=0.5, anchor="e", x=-6)
        else:
            self._clear_button.place_forget()
            # Put it back to its resting look now: it may have been hidden while
            # the pointer was over it, so its own <Leave> will never arrive.
            self._clear_button.configure(image=self._clear_rest_icon)
            try:
                self._clear_button._on_leave()
            except AttributeError:
                pass