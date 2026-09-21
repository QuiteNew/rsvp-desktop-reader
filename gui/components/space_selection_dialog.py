import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, FONT_HEADING, FONT_BODY, apply_app_icon, center_over_parent

class SpaceSelectionDialog(ctk.CTkToplevel):
    """Popup listing every space — the active one shown at full color and
    unclickable, the others shown grey-toned and clickable to switch."""

    def __init__(self, master, spaces: list[str], current_space: str, on_select):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # end of __init__, and gui/components/settings_window.py for the
        # fuller explanation of why this uses -alpha rather than
        # withdraw()/deiconify()).
        self.attributes("-alpha", 0)

        self.title("Select Space")
        apply_app_icon(self)
        center_over_parent(self, 280, 320)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_select = on_select

        title_font = ctk.CTkFont(family=FONT_HEADING, size=15)
        ctk.CTkLabel(self, text="Spaces", text_color=COCOA_INK, font=title_font).pack(anchor="w", padx=20, pady=(20, 10))

        list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=(20, 3), pady=(0, 20))

        active_font = ctk.CTkFont(family=FONT_HEADING, size=15)
        inactive_font = ctk.CTkFont(family=FONT_BODY, size=13)

        for space_name in spaces:
            if space_name == current_space:
                # A plain label, not a button — full color, not clickable,
                # and can't pick up any washed-out "disabled" button styling.
                ctk.CTkLabel(
                    list_frame, text=space_name, anchor="w",
                    text_color=COCOA_INK, font=active_font,
                ).pack(fill="x", pady=5, padx=4)
            else:
                ctk.CTkButton(
                    list_frame, text=space_name, anchor="w",
                    fg_color="transparent", hover_color=WARM_TAUPE,
                    text_color=WARM_LINE, font=inactive_font,
                    command=lambda s=space_name: self._handle_select(s),
                ).pack(fill="x", pady=3)

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
        # A plain update_idletasks() (as used in the other dialogs) isn't
        # enough here: this window uses CTkScrollableFrame, whose internal
        # scroll-region and inner-frame sizing (see ctk_scrollable_frame.py,
        # lines 78-79 in the installed CustomTkinter) are driven by real
        # <Configure> events, not idle tasks -- update_idletasks() doesn't
        # dispatch those, only update() does. Without this, the scrollable
        # area's own layout can still be settling after the alpha flip,
        # which is what caused the remaining piecemeal/white-gap reveal on
        # this window specifically.
        self.update()
        self.attributes("-alpha", 1)

    def _handle_select(self, space_name: str) -> None:
        self.on_select(space_name)
        self.destroy()