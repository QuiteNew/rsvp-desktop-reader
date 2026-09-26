import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, FONT_HEADING, FONT_BODY, apply_app_icon, center_over_parent


class MoveTranscriptDialog(ctk.CTkToplevel):
    """Popup listing every space except the transcript's current one:
    picking one moves the transcript there and closes. Only ever opened
    when at least one other space exists to offer (see gui/app.py's
    _handle_move_requested(), which checks that first and shows a
    MessageDialog instead if this is the user's only space), so this
    dialog itself never has to handle an empty list."""

    def __init__(self, master, transcript_title: str, other_spaces: list[str], on_select):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # end of __init__, and gui/components/settings_window.py for the
        # fuller explanation of why this uses -alpha rather than
        # withdraw()/deiconify()).
        self.attributes("-alpha", 0)

        self.title("Move Transcript")
        apply_app_icon(self)
        center_over_parent(self, 300, 280)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_select = on_select

        title_font = ctk.CTkFont(family=FONT_HEADING, size=14)
        ctk.CTkLabel(
            self, text=f"Move \"{transcript_title}\" to:",
            text_color=COCOA_INK, font=title_font,
            wraplength=260, justify="left",
        ).pack(anchor="w", padx=20, pady=(20, 10))

        list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=(20, 3), pady=(0, 20))

        row_font = ctk.CTkFont(family=FONT_BODY, size=13)
        # A bare loop, not a per-row method like SpaceSelectionDialog's
        # _add_space_row(): there's nothing here for a row to close over
        # besides the space name itself (no rename/delete state, no
        # mutable per-row tracking), so the classic late-binding closure
        # bug is avoided just as well with the `s=space_name` default-arg
        # capture below, without the extra indirection of a separate
        # method.
        for space_name in other_spaces:
            ctk.CTkButton(
                list_frame, text=space_name, anchor="w",
                fg_color="transparent", hover_color=WARM_TAUPE,
                text_color=WARM_LINE, font=row_font,
                command=lambda s=space_name: self._handle_select(s),
            ).pack(fill="x", pady=3, padx=2)

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # Reveal now that everything above is built, colored, and
        # comfortably past CustomTkinter's own internal titlebar dance
        # (see the alpha note near the top of __init__). update() rather
        # than just update_idletasks(), matching SpaceSelectionDialog:
        # this window also uses CTkScrollableFrame, whose internal
        # scroll-region sizing is driven by real <Configure> events,
        # which only update() dispatches.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        self.update()
        self.attributes("-alpha", 1)

    def _handle_select(self, space_name: str) -> None:
        self.on_select(space_name)
        self.destroy()