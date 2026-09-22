import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY, apply_app_icon, center_over_parent

class AddTranscriptDialog(ctk.CTkToplevel):
    """Popup for creating a new transcript: asks for a title and a space.
    Reused as-is for both ways of creating a transcript -- a blank one
    from the sidebar's "+", and one seeded from an imported file (see
    gui/app.py's _handle_add_from_file_requested()) -- the only
    difference being initial_title/window_title, both optional so the
    blank-transcript flow is completely unaffected."""

    def __init__(
        self, master, spaces: list[str], default_space: str, on_submit,
        initial_title: str = "", window_title: str = "New Transcript",
    ):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # end of __init__, and gui/components/settings_window.py for the
        # fuller explanation of why this uses -alpha rather than
        # withdraw()/deiconify()).
        self.attributes("-alpha", 0)

        self.title(window_title)
        apply_app_icon(self)
        center_over_parent(self, 340, 240)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_submit = on_submit

        label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        entry_font = ctk.CTkFont(family=FONT_BODY, size=13)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        ctk.CTkLabel(self, text="Title", text_color=COCOA_INK, font=label_font).pack(anchor="w", padx=20, pady=(20, 4))
        self.title_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. Lecture 3 notes",
            fg_color=WARM_TAUPE, border_color=WARM_LINE, border_width=1,
            text_color=COCOA_INK, font=entry_font,
        )
        self.title_entry.pack(fill="x", padx=20)
        if initial_title:
            # Pre-filled from the picked file's name for a file import --
            # selected (not just inserted) and given keyboard focus, so
            # the user can immediately overwrite it by typing, without
            # first having to clear it themselves. Left untouched for the
            # blank-transcript flow, where initial_title is always "".
            self.title_entry.insert(0, initial_title)
            self.title_entry.select_range(0, "end")
            self.title_entry.icursor("end")
            self.title_entry.focus_set()

        ctk.CTkLabel(self, text="Space", text_color=COCOA_INK, font=label_font).pack(anchor="w", padx=20, pady=(16, 4))
        self.space_menu = ctk.CTkOptionMenu(
            self, values=spaces,
            fg_color=WARM_TAUPE, button_color=EMBER_GLOW, button_hover_color=EMBER_GLOW_HOVER,
            dropdown_fg_color=WARM_TAUPE, dropdown_hover_color=WARM_LINE, dropdown_text_color=COCOA_INK,
            text_color=COCOA_INK, font=entry_font,
        )
        self.space_menu.set(default_space)
        self.space_menu.pack(fill="x", padx=20)

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            button_row, text="Cancel", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            button_row, text="Create", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_create,
        ).pack(side="right")

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # Reveal now that everything above is built, colored, and
        # comfortably past CustomTkinter's own internal titlebar dance
        # (see the alpha note near the top of __init__). update_idletasks()
        # right before flipping alpha forces any still-queued layout/redraw
        # work (including CTk widgets that defer their own first paint via
        # their own internal after() calls) to actually finish first --
        # otherwise the reveal can catch some of that mid-flight, showing
        # pieces of the window popping in over a white background instead
        # of one clean paint.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def _handle_create(self) -> None:
        title = self.title_entry.get().strip()
        space = self.space_menu.get()
        if not title:
            return
        self.on_submit(title, space)
        self.destroy()