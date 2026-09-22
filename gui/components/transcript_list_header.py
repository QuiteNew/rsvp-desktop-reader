import tkinter as tk
import customtkinter as ctk
from gui.theme import WARM_TAUPE, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_HEADING


class TranscriptListHeader(ctk.CTkFrame):
    """Top of the sidebar: 'List of Transcripts' title and a '+' button.
    "+" opens a small menu with the two ways to add a transcript: a blank
    one (the original flow), or one seeded from an imported file."""

    def __init__(self, master, on_add=None, on_add_from_file=None):
        super().__init__(master, fg_color=WARM_TAUPE, corner_radius=0)
        self.on_add = on_add
        self.on_add_from_file = on_add_from_file

        title_font = ctk.CTkFont(family=FONT_HEADING, size=15)
        ctk.CTkLabel(self, text="List of Transcripts", text_color=COCOA_INK, font=title_font).pack(side="left", padx=12)

        self.add_button = ctk.CTkButton(
            self, text="+", width=28, height=28, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            command=self._show_add_menu,
        )
        self.add_button.pack(side="right", padx=12)

        # A plain tkinter Menu, not a CTk widget -- CustomTkinter has no
        # lightweight "momentary popup" menu of its own (CTkOptionMenu is
        # a full dropdown *select*, which isn't what this is), and
        # tkinter's own Menu works perfectly well on top of a CTk app,
        # since every CTk widget is still a real tkinter widget
        # underneath. Built once here, not per-click, since its two
        # commands never change.
        self._add_menu = tk.Menu(self, tearoff=False)
        self._add_menu.add_command(label="Blank transcript…", command=self._handle_add)
        self._add_menu.add_command(label="Add from file…", command=self._handle_add_from_file)

    def _show_add_menu(self) -> None:
        # Anchored just under the "+" button using its own screen
        # position, since CTkButton's command callback doesn't hand us a
        # click event to read coordinates from the way a raw tkinter
        # <Button-1> binding would.
        x = self.add_button.winfo_rootx()
        y = self.add_button.winfo_rooty() + self.add_button.winfo_height()
        try:
            self._add_menu.tk_popup(x, y)
        finally:
            # The standard tk_popup cleanup: releases the menu's own grab
            # even if it was dismissed without picking an item (e.g. a
            # click elsewhere, or Escape), so nothing is left holding
            # input hostage.
            self._add_menu.grab_release()

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()

    def _handle_add_from_file(self) -> None:
        if self.on_add_from_file:
            self.on_add_from_file()