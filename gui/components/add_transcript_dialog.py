import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY, apply_app_icon, center_over_parent

class AddTranscriptDialog(ctk.CTkToplevel):
    """Popup for creating a new transcript: asks for a title and a space.
    Reused as-is for both ways of creating a transcript -- a blank one
    from the sidebar's "+", and one seeded from an imported file (see
    gui/app.py's _handle_add_from_file_requested()) -- the only
    difference being initial_title/window_title/warning, all optional so
    the blank-transcript flow is completely unaffected."""

    # Base fixed size, and the size used instead when `warning` is set --
    # the extra height gives the wrapped warning label room without
    # crowding the Title/Space fields above it. Not computed from the
    # warning text's actual length; just enough for the two-ish line
    # messages _handle_add_from_file_requested() currently builds.
    _DIALOG_SIZE = (340, 240)
    _DIALOG_SIZE_WITH_WARNING = (340, 330)

    def __init__(
        self, master, spaces: list[str], default_space: str, on_submit,
        initial_title: str = "", window_title: str = "New Transcript",
        warning: str | None = None,
    ):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # end of __init__, and gui/components/settings_window.py for the
        # fuller explanation of why this uses -alpha rather than
        # withdraw()/deiconify()).
        self.attributes("-alpha", 0)

        self.title(window_title)
        apply_app_icon(self)
        width, height = self._DIALOG_SIZE_WITH_WARNING if warning else self._DIALOG_SIZE
        center_over_parent(self, width, height)
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
        self._use_chevron_dropdown_arrow(self.space_menu)

        if warning:
            # Reuses DeleteTranscriptDialog's "#A33636" red so a cautionary
            # message reads consistently across the app rather than
            # introducing a new color just for this. Only reachable today
            # via the file-import path (see gui/app.py), never the blank-
            # transcript flow, since warning defaults to None there.
            ctk.CTkLabel(
                self, text=warning, text_color="#A33636", font=label_font,
                wraplength=290, justify="left",
            ).pack(fill="x", padx=20, pady=(16, 0))

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

    @staticmethod
    def _use_chevron_dropdown_arrow(option_menu: ctk.CTkOptionMenu) -> None:
        """CTkOptionMenu draws its own dropdown arrow internally and has no
        public option to change it -- which icon it draws is decided by a
        single GLOBAL customtkinter setting (DrawEngine.
        preferred_drawing_method), which defaults to "font_shapes" on
        Windows: the arrow is a character taken from a bundled private
        icon font. That's what was rendering oddly (reported as looking
        like "2 pencils" rather than a clean arrow) on Windows here.

        FIRST ATTEMPT (superseded -- keeping this note so the mistake
        isn't repeated): forcing preferred_drawing_method to
        "polygon_shapes" on this widget's own DrawEngine instance did
        make the arrow itself a real geometric chevron, but that same
        DrawEngine instance ALSO draws the button's rounded, two-color
        background (draw_rounded_rect_with_border_vertical_split) --
        confirmed broken in practice (reported: the button turned into
        one large bar instead of a small square next to the arrow),
        because that method's "font_shapes" and "polygon_shapes"
        implementations build different, incompatible sets of canvas
        items, and only the arrow's own item was being cleared before
        forcing a redraw.

        This version leaves preferred_drawing_method -- and therefore
        the button's background rendering -- completely untouched, and
        only overrides what character the EXISTING "dropdown_arrow" text
        item displays and which font it uses: a plain "v" in the app's
        own body font (FONT_BODY) instead of the bundled icon font's "Y"
        glyph. Because it stays a text item throughout (never swapped
        for a different canvas item type), every later redraw's
        itemconfigure()/coords() calls stay valid -- no type mismatch,
        no crash.

        The one thing that DOES need handling: _draw() unconditionally
        resets that item's font back to the icon font on every redraw it
        performs (see ctk_optionmenu.py's _draw()), which would undo our
        override the next time anything triggers one (a resize, a
        configure() call). Nothing in THIS app actually reconfigures
        space_menu after it's built -- picking a value doesn't call
        _draw(), and the dialog is fixed-size/non-resizable -- so a
        single override right after construction would likely never get
        undone in practice. But to not depend on that staying true,
        option_menu's own _draw is wrapped (instance-level, so no other
        widget in the app is affected) to re-apply the override
        immediately after every redraw, whatever triggers it. Text color
        is left for CTk's own _draw() to keep setting -- it already
        colors whatever item carries the "dropdown_arrow" tag to match
        _text_color, so this doesn't need to duplicate that.

        Verified against customtkinter==6.0.0 (the version pinned in
        requirements.txt): rendered to an actual image and visually
        confirmed both the "v" and the button/field background look
        correct, then re-confirmed after a forced redraw, hover in/out,
        and resize. Relies on CTkOptionMenu's private _canvas/_draw
        attributes and its "dropdown_arrow" canvas tag, none of which
        are public API -- if customtkinter is ever upgraded past 6.0.0,
        this is the first place to check if the arrow reverts to the old
        icon or looks wrong again."""
        def _apply_chevron() -> None:
            option_menu._canvas.itemconfigure("dropdown_arrow", text="v", font=(FONT_BODY, -13))

        original_draw = option_menu._draw

        def _draw_and_reapply_chevron(*args, **kwargs):
            result = original_draw(*args, **kwargs)
            _apply_chevron()
            return result

        option_menu._draw = _draw_and_reapply_chevron
        _apply_chevron()  # __init__ already ran one _draw() before we got here

    def _handle_create(self) -> None:
        title = self.title_entry.get().strip()
        space = self.space_menu.get()
        if not title:
            return
        self.on_submit(title, space)
        self.destroy()