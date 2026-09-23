import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk
from gui.theme import WARM_TAUPE, HEARTH_PAPER, COCOA_INK, WARM_LINE, FONT_BODY


class TranscriptListBody(ctk.CTkFrame):
    """Scrollable list of saved transcripts. Each row has a delete ("X")
    button that only becomes clearly visible when hovering that row, a
    double-click-to-rename title, and a right-click menu to move the
    transcript to another space.

    Move deliberately has no icon of its own -- an earlier version added
    a dedicated always-there-on-hover "→" button next to delete, but that
    cost ~24px of the row's width on top of what delete already reserves
    (see the packing comment in add_entry() below), squeezing an already
    narrow sidebar's title text for a feature expected to be used far
    less often than delete or rename. Rename solves the same problem for
    itself with a gesture instead of an icon (double-click); move reuses
    that idea via a right-click context menu, which costs the row
    nothing until it's actually opened."""

    def __init__(self, master, on_select=None, on_delete_requested=None, on_rename_requested=None, on_move_requested=None):
        super().__init__(master, fg_color=WARM_TAUPE, corner_radius=0)
        self.on_select = on_select
        self.on_delete_requested = on_delete_requested
        self.on_rename_requested = on_rename_requested
        self.on_move_requested = on_move_requested

        self.entries_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.entries_frame.pack(fill="both", expand=True, padx=(8, 3), pady=8)

    def add_entry(self, transcript) -> None:
        row = ctk.CTkFrame(self.entries_frame, fg_color=HEARTH_PAPER, corner_radius=10)
        row.pack(fill="x", pady=3, padx=2)

        # delete_button is packed BEFORE title_label, even though it sits
        # on the right visually -- Tk's pack carves cavity in PACKING
        # order, not visual order. title_label uses fill="x" + expand=True
        # with no wraplength, so its natural width grows to fit however
        # long transcript.title is; a file import seeds the title from
        # the file's own name (see gui/app.py's
        # _handle_add_from_file_requested()), which runs much longer than
        # a typical short typed-by-hand title. Packing title_label FIRST
        # (the original order) let it claim the row's entire cavity
        # before delete_button got a chance to reserve its own space on
        # the right, which pushed delete_button fully out of the row for
        # any long-enough title -- confirmed by rendering both a short
        # and a long title side by side and watching the "X" disappear
        # only on the long one, exactly matching what was reported for
        # file-imported transcripts (whose titles are the ones usually
        # long enough to trigger it). Reserving delete_button's fixed-
        # size cavity first guarantees it's always visible; title_label
        # then just fills -- and gets visually clipped inside -- whatever
        # width remains, rather than the button vanishing.
        delete_button = ctk.CTkButton(
            row, text="X", width=20, height=20, corner_radius=8,
            fg_color="transparent", hover_color=WARM_LINE,
            text_color=WARM_TAUPE, cursor="hand2",
            command=lambda t=transcript: self._handle_delete_requested(t),
        )
        delete_button.pack(side="right", padx=(0, 10))

        title_font = ctk.CTkFont(family=FONT_BODY, size=13)
        title_label = ctk.CTkLabel(
            row, text=transcript.title, anchor="w",
            text_color=COCOA_INK, font=title_font, cursor="hand2",
        )
        title_label.pack(side="left", fill="x", expand=True, padx=(12, 4), pady=8)
        self._bind_truncating_label(title_label, transcript.title)

        # Rename entry -- built up front but never packed until a
        # double-click on title_label starts an edit (see start_rename()
        # below). It swaps into title_label's exact pack slot for the
        # duration of the edit, then swaps back out on commit or cancel,
        # so the row's layout never shifts around it.
        title_entry = ctk.CTkEntry(row, text_color=COCOA_INK, font=title_font)

        # A plain closure flag rather than title_entry.winfo_ismapped():
        # committing or cancelling both end with pack_forget(), which can
        # itself raise a synchronous <FocusOut> on the entry -- relying on
        # "is it currently mapped" to tell a real edit-in-progress apart
        # from that self-triggered follow-up event depends on exactly
        # when Tkinter updates the mapped state relative to firing the
        # event, which isn't something to depend on. This flag is set
        # False before pack_forget() runs, so both commit_rename() and
        # cancel_rename() are safe to call a second time and simply no-op.
        rename_state = {"editing": False}

        def start_rename(event=None):
            if rename_state["editing"]:
                return
            rename_state["editing"] = True
            title_entry.delete(0, "end")
            title_entry.insert(0, transcript.title)
            title_label.pack_forget()
            title_entry.pack(side="left", fill="x", expand=True, padx=(12, 4), pady=8)
            title_entry.focus_set()
            title_entry.select_range(0, "end")
            title_entry.icursor("end")

        def end_rename():
            rename_state["editing"] = False
            title_entry.pack_forget()
            title_label.pack(side="left", fill="x", expand=True, padx=(12, 4), pady=8)

        def commit_rename(event=None):
            if not rename_state["editing"]:
                return
            new_title = title_entry.get().strip()
            end_rename()
            if new_title and new_title != transcript.title:
                self._handle_rename_requested(transcript, new_title)

        def cancel_rename(event=None):
            if not rename_state["editing"]:
                return
            end_rename()

        title_entry.bind("<Return>", commit_rename)
        title_entry.bind("<FocusOut>", commit_rename)
        title_entry.bind("<Escape>", cancel_rename)

        def reveal(event=None):
            delete_button.configure(text_color=WARM_LINE)

        def unreveal(event=None):
            delete_button.configure(text_color=WARM_TAUPE)

        for widget in (row, title_label, delete_button):
            widget.bind("<Enter>", reveal)
            widget.bind("<Leave>", unreveal)

        title_label.bind("<Button-1>", lambda event, t=transcript: self._handle_select(t))
        title_label.bind("<Double-Button-1>", start_rename)

        # Right-click ("<Button-3>", the standard Windows/Linux secondary-
        # click event -- macOS's Ctrl-click also maps to it under Tk) on
        # either the row's own background or the title opens a plain
        # context menu with the transcript's only currently-menu-only
        # action. A fresh tk.Menu is built per click rather than one
        # reused instance -- cheap, and sidesteps having to keep a
        # per-row menu object around just to close over `transcript`.
        # This is a native/undecorated tk.Menu, not a themed CTk widget
        # -- CustomTkinter doesn't provide a themed popup menu, but a
        # plain OS-native context menu here is normal and expected, the
        # same way even most fully-themed desktop apps still show the
        # system's native right-click menu.
        def show_context_menu(event):
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Move to Space...", command=lambda: self._handle_move_requested(transcript))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        row.bind("<Button-3>", show_context_menu)
        title_label.bind("<Button-3>", show_context_menu)

    @staticmethod
    def _bind_truncating_label(label: ctk.CTkLabel, full_text: str) -> None:
        """CTkLabel, like a plain Tk label, never truncates long text on
        its own -- with no wraplength set it just requests whatever
        width the full string needs. That's what let delete_button get
        squeezed out of the row entirely for long (e.g. filename-
        derived) titles, fixed above by reserving delete_button's own
        space first; once that's fixed, a too-long title instead just
        renders with its raw end cut off wherever space runs out, which
        still isn't great -- this replaces that raw cutoff with a
        "…"-truncated version sized to actually fit.

        Tkinter has no built-in ellipsis truncation (unlike native OS
        controls), so this measures the real pixel width of the label's
        font against the label's own CURRENT on-screen width and
        rebuilds the text to fit -- bound to <Configure> rather than
        computed once, because the sidebar is user-resizable (see
        gui/app.py's sidebar drag handlers): a character-count cutoff
        chosen for today's width would be wrong -- still overflowing, or
        needlessly aggressive -- the moment the sidebar is dragged to a
        different width.

        Reads the font straight off the label's own internal
        tkinter.Label (label._label) rather than rebuilding it from the
        family/size passed into CTkFont: CustomTkinter applies its own
        DPI/widget-scaling on top of that font before it's actually
        drawn (see _apply_font_scaling in customtkinter's ctk_label.py),
        and this guarantees the pixel measurements below match what's
        really on screen instead of drifting at a non-default scaling
        setting -- this app already has to fight DPI-scaling quirks
        elsewhere (see gui/theme.py's set_dpi_awareness()/
        apply_linux_dpi_scaling()), so this doesn't add a second,
        independent place that can disagree with Windows about scale.
        _label is private/undocumented, same caveat as
        AddTranscriptDialog._use_chevron_dropdown_arrow()'s reliance on
        CTkOptionMenu's internals -- verified against
        customtkinter==6.0.0 (pinned in requirements.txt)."""
        ellipsis = "…"

        def apply_truncation(event=None) -> None:
            available_px = label.winfo_width()
            if available_px <= 1:
                return  # not laid out yet -- a later <Configure> will fire once it is
            tk_font = tkfont.Font(font=label._label.cget("font"))
            if tk_font.measure(full_text) <= available_px:
                truncated = full_text
            else:
                truncated = full_text
                while truncated and tk_font.measure(truncated + ellipsis) > available_px:
                    truncated = truncated[:-1]
                truncated = (truncated + ellipsis) if truncated else ellipsis
            if label.cget("text") != truncated:
                label.configure(text=truncated)

        label.bind("<Configure>", apply_truncation)
        label.after(10, apply_truncation)

    def clear(self) -> None:
        for widget in self.entries_frame.winfo_children():
            widget.destroy()

    def render_transcripts(self, transcripts) -> None:
        self.clear()
        for t in transcripts:
            self.add_entry(t)

    def _handle_select(self, transcript) -> None:
        if self.on_select:
            self.on_select(transcript)

    def _handle_delete_requested(self, transcript) -> None:
        if self.on_delete_requested:
            self.on_delete_requested(transcript)

    def _handle_rename_requested(self, transcript, new_title: str) -> None:
        if self.on_rename_requested:
            self.on_rename_requested(transcript, new_title)

    def _handle_move_requested(self, transcript) -> None:
        if self.on_move_requested:
            self.on_move_requested(transcript)