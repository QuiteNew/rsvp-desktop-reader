import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, WARM_MOCHA, FONT_HEADING, FONT_BODY, apply_app_icon, center_over_parent

class SpaceSelectionDialog(ctk.CTkToplevel):
    """Popup listing every space -- the active one shown at full color and
    unclickable (to switch), the others shown grey-toned and clickable to
    switch. Every row is its own WARM_TAUPE card (corner_radius=10, the
    same "surface sitting on the dialog's own HEARTH_PAPER background"
    relationship AddSpaceDialog's entry field already uses) with a
    delete (X) icon that's hover-revealed across the whole card, same
    mechanism as gui/components/transcript_list_body.py's sidebar rows.

    Renaming is double-click-only -- there's no separate pencil icon
    here anymore, just the "Double click to rename a space" hint printed
    above the list. Double-click has to work differently depending on
    the row, though: see _add_space_row()'s docstring for why an
    inactive row's single click can't fire the switch immediately the
    way the sidebar's click-to-select does.

    Deliberately does NOT auto-close after a rename, the way it already
    does after picking a space to switch to (see _handle_select()) -- a
    rename only ever changes that one row's own label, in place, with no
    need to leave the dialog to see the result. A delete DOES close the
    whole dialog (see gui/app.py's _handle_space_delete_confirmed()) --
    it's already gated behind its own separate confirmation popup
    (DeleteSpaceDialog, built by gui/app.py), and closing alongside that
    second popup is simpler and more robust than trying to surgically
    remove just the deleted row from a dialog that's been sitting open
    through an async confirm step."""

    # How long an inactive row's single click waits before actually
    # switching spaces -- see _add_space_row()'s docstring. Long enough
    # for a real second click to land and register as a double-click,
    # short enough that switching still feels effectively instant.
    _SELECT_DELAY_MS = 250

    def __init__(
        self, master, spaces: list[str], current_space: str,
        on_select, on_rename_requested, on_delete_requested,
    ):
        super().__init__(master)

        # Hidden until fully built (see the matching alpha restore at the
        # end of __init__, and gui/components/settings_window.py for the
        # fuller explanation of why this uses -alpha rather than
        # withdraw()/deiconify()).
        self.attributes("-alpha", 0)

        self.title("Select Space")
        apply_app_icon(self)
        center_over_parent(self, 320, 320)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_select = on_select
        self.on_rename_requested = on_rename_requested
        self.on_delete_requested = on_delete_requested

        # size=34 -- well over double the dialog's original 15 -- still
        # fits "Spaces" on one line within this dialog's 320px width
        # (minus the 20px side padding) without wrapping.
        title_font = ctk.CTkFont(family=FONT_HEADING, size=34)
        # No anchor="w" here -- pack()'s default anchor is "center", so
        # dropping the old left-alignment centers the label (and, since
        # CTkLabel sizes itself to its text, the text along with it)
        # within the dialog's full width instead.
        ctk.CTkLabel(self, text="Spaces", text_color=COCOA_INK, font=title_font).pack(padx=20, pady=(22, 4))

        # Small caption naming the (otherwise undiscoverable, now that
        # there's no pencil icon) double-click gesture -- centered under
        # the title, same reasoning as the title's own centering: the
        # two read as one short header block sitting above the list, not
        # two independently-placed pieces of text. WARM_LINE -- the same
        # muted tone the inactive space names below use for their own
        # "soft grey filter" look -- reads as genuinely grey against
        # HEARTH_PAPER, unlike COCOA_INK_LIGHT (theme.py's "one step
        # lighter than the main ink" token), which is really just a
        # lighter brown rather than a grey.
        hint_font = ctk.CTkFont(family=FONT_BODY, size=11)
        ctk.CTkLabel(self, text="Double click to rename a space", text_color=WARM_LINE, font=hint_font).pack(pady=(0, 14))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=(20, 3), pady=(0, 20))

        # Active and inactive rows keep their original two DIFFERENT font
        # FAMILIES -- FONT_HEADING ("Fredoka SemiBold") is already
        # noticeably bolder-looking than FONT_BODY ("Quicksand Medium")
        # purely by being a different, heavier typeface -- so equalizing
        # just the SIZE here (both now 16) keeps the active row reading
        # as the bolder one without introducing a separate weight
        # override or a same-vs-different-size split.
        self._active_font = ctk.CTkFont(family=FONT_HEADING, size=16)
        self._inactive_font = ctk.CTkFont(family=FONT_BODY, size=16)
        self._rename_font = ctk.CTkFont(family=FONT_BODY, size=16)

        for space_name in spaces:
            self._add_space_row(space_name, is_current=(space_name == current_space))

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # Reveal now that everything above is built, colored, and
        # comfortably past CustomTkinter's own internal titlebar dance
        # (see the alpha note near the top of __init__). update() rather
        # than just update_idletasks() -- see the original docstring this
        # was carried over from: this window uses CTkScrollableFrame,
        # whose internal scroll-region sizing is driven by real
        # <Configure> events, which only update() dispatches.
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        self.update()
        self.attributes("-alpha", 1)

    def _add_space_row(self, space_name: str, is_current: bool) -> None:
        """Build one row: a WARM_TAUPE card holding a name (a plain,
        full-color, non-interactive label for the active space; a
        muted, clickable-to-switch label for every other one) plus a
        delete icon, hover-revealed across the whole card. Renaming has
        no dedicated control of its own -- it's reached by double-
        clicking the name, on either kind of row.

        Double-click works differently depending on the row, because a
        plain click means something different on each:

        - The ACTIVE row's name isn't clickable-to-select at all (it's
          already the current space), so its <Double-Button-1> binding
          just calls start_rename() directly, same as
          transcript_list_body.py's title_label.

        - An INACTIVE row's name switches spaces on click -- and
          _handle_select() closes this whole dialog the instant it
          runs. A real double-click's first press fires <Button-1>
          before Tk recognizes the second press as a double-click at
          all; if that first <Button-1> switched spaces immediately,
          the dialog would already be gone before a second click could
          ever land, so <Double-Button-1> could never fire in practice.
          Instead, <Button-1> only SCHEDULES the switch _SELECT_DELAY_MS
          out via self.after(), and <Double-Button-1> -- which Tk fires
          in addition to that same click's own <Button-1>, right after
          it -- cancels the pending switch and starts a rename instead.
          A plain single click still switches spaces, just
          _SELECT_DELAY_MS later rather than instantly.

        A real method call, not a bare loop body -- this row's closures
        need to close over THIS row's own local variables (space_state,
        name_widget, name_entry, click_state), and a loop body directly
        inside __init__ doesn't get a fresh scope per iteration the way
        a method call does -- see gui/components/transcript_list_body.py's
        add_entry() for the fuller version of this same reasoning."""
        row = ctk.CTkFrame(self.list_frame, fg_color=WARM_TAUPE, corner_radius=10)
        row.pack(fill="x", pady=3, padx=2)

        # Mutable holder for this row's current space name -- updated in
        # place after a successful rename (see commit_rename() below), so
        # a second rename or a delete on the SAME row afterward acts on
        # the new name, not a now-stale one captured when the row was
        # first built.
        space_state = {"name": space_name}

        # Packed before the name, same reasoning as
        # transcript_list_body.py's add_entry(): packing the fixed-size
        # button first reserves its cavity on the right before the name
        # (packed after, with fill="x" + expand=True) can claim the
        # whole row and push it out.
        #
        # Unrevealed text_color is WARM_TAUPE -- exactly the row's own
        # card color -- so the glyph is genuinely invisible, not just
        # faint, until reveal() below fires. hover_color is WARM_MOCHA
        # rather than WARM_LINE (the revealed text color) specifically
        # so hovering directly over an already-revealed icon never lands
        # text and fill on the same color at once, which would make the
        # glyph disappear again right where you're pointing at it.
        delete_button = ctk.CTkButton(
            row, text="X", width=24, height=24, corner_radius=8,
            fg_color="transparent", hover_color=WARM_MOCHA,
            text_color=WARM_TAUPE, cursor="hand2",
            command=lambda: self._handle_delete_requested(space_state["name"]),
        )
        delete_button.pack(side="right", padx=(4, 6))

        row_pady = 10
        # (left, right) -- a small deliberate nudge off the row's left
        # edge, purely cosmetic. The right side stays 4 to match
        # delete_button's own left padding of 4, keeping the gap on
        # either side of the name visually even-ish.
        name_padx = (8, 4)

        # Rename entry -- built up front but never packed until
        # start_rename() below. Swaps into name_widget's exact pack slot
        # for the edit, then back out on commit or cancel, same pattern
        # as transcript_list_body.py's inline rename. Built before
        # name_widget itself, since name_widget's own click bindings
        # below need start_rename to already exist as a name to close
        # over.
        name_entry = ctk.CTkEntry(row, text_color=COCOA_INK, font=self._rename_font)

        # Same closure-flag guard as transcript_list_body.py's inline
        # rename, and for the same reason: committing or cancelling both
        # end with pack_forget(), which can itself raise a synchronous
        # <FocusOut> on the entry, so a plain winfo_ismapped() check
        # isn't reliable here. This flag is set False before
        # pack_forget() runs, so commit_rename()/cancel_rename() are
        # both safe to call a second time and simply no-op.
        rename_state = {"editing": False}

        def start_rename() -> None:
            if rename_state["editing"]:
                return
            rename_state["editing"] = True
            name_entry.delete(0, "end")
            name_entry.insert(0, space_state["name"])
            name_widget.pack_forget()
            name_entry.pack(side="left", fill="x", expand=True, pady=row_pady, padx=name_padx)
            name_entry.focus_set()
            name_entry.select_range(0, "end")
            name_entry.icursor("end")

        def end_rename() -> None:
            rename_state["editing"] = False
            name_entry.pack_forget()
            name_widget.pack(side="left", fill="x", expand=True, pady=row_pady, padx=name_padx)

        def commit_rename(event=None) -> None:
            if not rename_state["editing"]:
                return
            new_name = name_entry.get().strip()
            end_rename()
            if new_name and new_name != space_state["name"]:
                # rename_space() (via on_rename_requested) returns
                # whether the rename actually happened -- a blank,
                # unchanged, or already-used name is silently rejected
                # by the store, same convention AddSpaceDialog already
                # uses for a blank new-space name. Only update this
                # row's own display once that's confirmed true, or a
                # rejected rename could leave this row showing a name
                # that was never actually applied underneath it.
                if self._handle_rename_requested(space_state["name"], new_name):
                    space_state["name"] = new_name
                    name_widget.configure(text=new_name)

        def cancel_rename(event=None) -> None:
            if not rename_state["editing"]:
                return
            end_rename()

        name_entry.bind("<Return>", commit_rename)
        name_entry.bind("<FocusOut>", commit_rename)
        name_entry.bind("<Escape>", cancel_rename)

        if is_current:
            # A plain, non-interactive label -- full color, no click-to-
            # select binding, no hand2 cursor -- since the active space
            # can't be switched to (it's already the one showing). No
            # delay needed for its double-click either, since there's no
            # competing single-click action to guard against.
            name_widget = ctk.CTkLabel(
                row, text=space_name, anchor="w",
                text_color=COCOA_INK, font=self._active_font,
            )
            name_widget.bind("<Double-Button-1>", lambda event: start_rename())
        else:
            # click_state["pending_select_id"] holds the self.after() id
            # for a switch that hasn't fired yet -- see this method's
            # docstring for why this can't just switch immediately on
            # <Button-1> the way the sidebar does.
            click_state = {"pending_select_id": None}

            def fire_pending_select() -> None:
                click_state["pending_select_id"] = None
                self._handle_select(space_state["name"])

            def handle_click(event=None) -> None:
                if click_state["pending_select_id"] is not None:
                    self.after_cancel(click_state["pending_select_id"])
                click_state["pending_select_id"] = self.after(self._SELECT_DELAY_MS, fire_pending_select)

            def handle_double_click(event=None) -> None:
                # Tk fires <Button-1> for the second click BEFORE
                # <Double-Button-1>, so by the time this runs,
                # handle_click() has just scheduled another pending
                # select that needs cancelling -- otherwise the rename
                # box that start_rename() is about to open would get
                # yanked out from under the user _SELECT_DELAY_MS later.
                if click_state["pending_select_id"] is not None:
                    self.after_cancel(click_state["pending_select_id"])
                    click_state["pending_select_id"] = None
                start_rename()

            name_widget = ctk.CTkLabel(
                row, text=space_name, anchor="w", cursor="hand2",
                text_color=WARM_LINE, font=self._inactive_font,
            )
            name_widget.bind("<Button-1>", handle_click)
            name_widget.bind("<Double-Button-1>", handle_double_click)
        name_widget.pack(side="left", fill="x", expand=True, pady=row_pady, padx=name_padx)

        # Hover-reveal for the delete "X", spanning the row's entire
        # card -- bound to row, name_widget, AND the button itself (not
        # just row) so moving the mouse from the name straight onto the
        # icon, or vice versa, never passes through a gap that would
        # flicker the reveal off and back on.
        def reveal(event=None) -> None:
            delete_button.configure(text_color=WARM_LINE)

        def unreveal(event=None) -> None:
            delete_button.configure(text_color=WARM_TAUPE)

        for widget in (row, name_widget, delete_button):
            widget.bind("<Enter>", reveal)
            widget.bind("<Leave>", unreveal)

    def _handle_select(self, space_name: str) -> None:
        self.on_select(space_name)
        self.destroy()

    def _handle_rename_requested(self, old_name: str, new_name: str) -> bool:
        return self.on_rename_requested(old_name, new_name)

    def _handle_delete_requested(self, space_name: str) -> None:
        self.on_delete_requested(space_name)