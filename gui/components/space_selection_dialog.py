import customtkinter as ctk
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, FONT_HEADING, FONT_BODY, apply_app_icon, center_over_parent

class SpaceSelectionDialog(ctk.CTkToplevel):
    """Popup listing every space -- the active one shown at full color and
    unclickable (to switch), the others shown grey-toned and clickable to
    switch. Every row also gets a rename (pencil) and delete (X) icon,
    regardless of active/inactive status -- unlike the delete "X" in
    gui/components/transcript_list_body.py's sidebar rows, these are
    always visible rather than hover-revealed: this is a small dialog
    opened specifically to manage spaces, not a persistent, always-on-
    screen list where minimizing visual clutter matters as much.

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

        title_font = ctk.CTkFont(family=FONT_HEADING, size=15)
        ctk.CTkLabel(self, text="Spaces", text_color=COCOA_INK, font=title_font).pack(anchor="w", padx=20, pady=(20, 10))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=(20, 3), pady=(0, 20))

        self._active_font = ctk.CTkFont(family=FONT_HEADING, size=15)
        self._inactive_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self._rename_font = ctk.CTkFont(family=FONT_BODY, size=13)

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
        """Build one row: a name (a plain full-color label for the active
        space, a grey clickable button to switch for every other one --
        unchanged from before), plus a rename and delete icon that apply
        regardless of active/inactive status.

        A real method call, not a bare loop body -- this row's closures
        (start_rename()/commit_rename()/etc. below, and the lambdas on
        delete_button/edit_button/name_widget) need to close over THIS
        row's own local variables (space_state, name_widget, name_entry,
        row_pady), and a loop body directly inside __init__ doesn't get a
        fresh scope per iteration the way a method call does -- a closure
        built straight inside a plain for loop in __init__ would
        otherwise share (and by the time it's actually called, only ever
        see) whichever row's variables were bound LAST, across every row.
        Splitting row-building out into its own method sidesteps the
        whole problem the same way gui/components/transcript_list_body.py's
        add_entry() already does, one call per entry -- which is also why
        none of the lambdas below need the `lambda x=x: ...` default-arg
        capture trick the OLD version of this loop used for on_select:
        each one already closes over a fresh, per-call local."""
        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", pady=3, padx=2)

        # Mutable holder for this row's current space name -- updated in
        # place after a successful rename (see commit_rename() below), so
        # a second rename or a delete on the SAME row afterward acts on
        # the new name, not a now-stale one captured when the row was
        # first built.
        space_state = {"name": space_name}

        # delete/edit packed before the name, same reasoning as
        # transcript_list_body.py's add_entry(): packing the fixed-size
        # buttons first reserves their cavity on the right before the
        # name (packed after, with fill="x" + expand=True) can claim the
        # whole row and push them out.
        delete_button = ctk.CTkButton(
            row, text="X", width=22, height=22, corner_radius=8,
            fg_color="transparent", hover_color=WARM_TAUPE,
            text_color=WARM_LINE, cursor="hand2",
            command=lambda: self._handle_delete_requested(space_state["name"]),
        )
        delete_button.pack(side="right", padx=(4, 0))

        edit_button = ctk.CTkButton(
            row, text="✎", width=22, height=22, corner_radius=8,
            fg_color="transparent", hover_color=WARM_TAUPE,
            text_color=WARM_LINE, cursor="hand2",
            command=lambda: start_rename(),
        )
        edit_button.pack(side="right", padx=(4, 0))

        row_pady = 5 if is_current else 3
        if is_current:
            # A plain label, not a button -- full color, not clickable,
            # and can't pick up any washed-out "disabled" button styling.
            name_widget = ctk.CTkLabel(
                row, text=space_name, anchor="w",
                text_color=COCOA_INK, font=self._active_font,
            )
        else:
            name_widget = ctk.CTkButton(
                row, text=space_name, anchor="w",
                fg_color="transparent", hover_color=WARM_TAUPE,
                text_color=WARM_LINE, font=self._inactive_font,
                command=lambda: self._handle_select(space_state["name"]),
            )
        name_widget.pack(side="left", fill="x", expand=True, pady=row_pady, padx=4)

        # Rename entry -- built up front but never packed until
        # start_rename() below. Swaps into name_widget's exact pack slot
        # for the edit, then back out on commit or cancel, same pattern
        # as transcript_list_body.py's inline rename.
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
            name_entry.pack(side="left", fill="x", expand=True, pady=row_pady, padx=4)
            name_entry.focus_set()
            name_entry.select_range(0, "end")
            name_entry.icursor("end")

        def end_rename() -> None:
            rename_state["editing"] = False
            name_entry.pack_forget()
            name_widget.pack(side="left", fill="x", expand=True, pady=row_pady, padx=4)

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

    def _handle_select(self, space_name: str) -> None:
        self.on_select(space_name)
        self.destroy()

    def _handle_rename_requested(self, old_name: str, new_name: str) -> bool:
        return self.on_rename_requested(old_name, new_name)

    def _handle_delete_requested(self, space_name: str) -> None:
        self.on_delete_requested(space_name)