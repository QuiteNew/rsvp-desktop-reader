import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk
from gui.components.divider import Divider
from gui.theme import WARM_TAUPE, HEARTH_PAPER, COCOA_INK, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY


class TranscriptListBody(ctk.CTkFrame):
    """Scrollable list of saved transcripts, with a search box and sort
    menu pinned above it. Each row has a delete ("X") button that only
    becomes clearly visible when hovering that row, a double-click-to-
    rename title, and a right-click menu to move the transcript to
    another space."""

    # Every available sort mode: label -> (key function, reverse). A
    # plain dict rather than a list of tuples, since Python dicts keep
    # insertion order, so this doubles as the menu's display order in
    # _show_sort_menu() below, while also giving _rerender() a direct
    # O(1) lookup instead of a linear scan.
    #
    # "Date added" has no dedicated timestamp field to sort by (see
    # core/models.py: Transcript has no created_at/last_opened_at of
    # any kind). id stands in for it instead: TranscriptStore._next_id
    # only ever increases and ids are never reused or reassigned, and
    # add_transcript() always appends, never inserts, so id order is
    # creation order, exactly.
    #
    # "Most read" and "Most time spent reading" repurpose two of the
    # Stats tab's own running totals (times_read, total_time_spent_seconds;
    # see core/models.py and TranscriptStore.add_session_stats()) as
    # sort keys. Both are single-direction (most-first) only, not offered
    # in a "least first" variant: unlike title/date, there's no obvious
    # everyday reason to want to see your LEAST-read transcripts surfaced
    # first, so that direction was left out rather than doubling the menu
    # for a combination nothing asked for.
    SORT_MODES = {
        "Title (A–Z)": (lambda t: t.title.lower(), False),
        "Title (Z–A)": (lambda t: t.title.lower(), True),
        "Date added (newest first)": (lambda t: t.id, True),
        "Date added (oldest first)": (lambda t: t.id, False),
        "Most read": (lambda t: t.times_read, True),
        "Most time spent reading": (lambda t: t.total_time_spent_seconds, True),
    }

    # Matches the list's own pre-existing, sort-feature-free order
    # (self._transcripts in TranscriptStore is only ever appended to,
    # never reordered; see add_transcript()), so a freshly launched
    # app looks exactly as it always has until the user deliberately
    # picks a different sort.
    DEFAULT_SORT_LABEL = "Date added (oldest first)"

    def __init__(self, master, on_select=None, on_delete_requested=None, on_rename_requested=None, on_move_requested=None):
        super().__init__(master, fg_color=WARM_TAUPE, corner_radius=0)
        self.on_select = on_select
        self.on_delete_requested = on_delete_requested
        self.on_rename_requested = on_rename_requested
        self.on_move_requested = on_move_requested

        # The full, unfiltered/unsorted list handed in by the most recent
        # render_transcripts() call. Search and sort both re-derive what
        # they display from this each time (see _rerender()) rather than
        # needing app.py to re-supply it on every keystroke or menu pick,
        # since neither the search text nor the chosen sort mode is
        # something app.py or TranscriptStore has any need to know about;
        # it's purely a display-layer concern local to this widget, and
        # both are deliberately left un-persisted (in-memory only, same
        # as e.g. AddTranscriptDialog's own transient state): they reset
        # to "no search, default sort" on every launch, same as the list
        # itself always has, rather than adding a settings-store field
        # for something this low-stakes to get wrong or stale.
        self._all_transcripts: list = []
        self._sort_label = self.DEFAULT_SORT_LABEL

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 6))

        # sort_button is packed before search_entry, same reasoning as
        # delete_button before title_label in add_entry() below: reserve
        # the fixed-size icon's cavity first so search_entry, which fills
        # whatever's left, can never push it out of the toolbar, even at
        # the sidebar's minimum width (SIDEBAR_WIDTH_RANGE in
        # core/settings_store.py allows down to 120px, far too narrow for
        # a text-labeled sort dropdown to reliably fit).
        sort_font = ctk.CTkFont(family=FONT_BODY, size=13)
        sort_button = ctk.CTkButton(
            toolbar, text="⇅", width=28, height=28, corner_radius=8,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=sort_font, command=self._show_sort_menu,
        )
        sort_button.pack(side="right")
        self._sort_button = sort_button

        # trace_add fires on every change to the entry's text: typing,
        # pasting, cutting, or a programmatic .set(), unlike binding a
        # key event, which would miss paste/cut/clear. render_transcripts()
        # (called by app.py on every add/delete/rename/move/space-switch)
        # already triggers its own _rerender(); this covers the other
        # two triggers, a changed search text or a changed sort mode,
        # neither of which needs new data from app.py at all.
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_args: self._rerender())

        entry_font = ctk.CTkFont(family=FONT_BODY, size=13)
        search_entry = ctk.CTkEntry(
            toolbar, textvariable=self._search_var, placeholder_text="Search…",
            height=28, fg_color=HEARTH_PAPER, border_color=WARM_LINE, border_width=1,
            text_color=COCOA_INK, font=entry_font,
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Purely decorative: separates the search/sort toolbar above from
        # the scrollable list below so the two don't visually run
        # together. Reuses the same Divider used for the app's actual
        # resize handles (the sidebar/bottom-band splits in gui/app.py),
        # but never calls set_resizable(True) on it, so it stays in its
        # default disabled state: _enabled is False from construction,
        # and every one of Divider's press/motion handlers early-returns
        # whenever _enabled is False (see divider.py), so there's no
        # hover cursor, no drag, nothing to grab. Just the thin
        # WARM_LINE line itself.
        divider = Divider(self, orientation="horizontal")
        divider.pack(fill="x", padx=8)

        self.entries_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.entries_frame.pack(fill="both", expand=True, padx=(8, 3), pady=(6, 8))

    def _show_sort_menu(self) -> None:
        """Popup menu of every sort mode, opened from sort_button: the
        same fresh-tk.Menu-per-click pattern as add_entry()'s right-click
        move menu below, for the same reason (CustomTkinter has no themed
        popup-menu widget of its own, and building a new plain tk.Menu on
        each click is cheap and avoids keeping a persistent one around).

        Uses add_radiobutton bound to a fresh StringVar seeded with the
        currently active sort label, rather than add_command, purely for
        the free radio-dot next to whichever mode is already selected: a
        small, genuinely useful "what am I sorted by right now" cue that
        a plain command menu wouldn't give without extra work. The
        StringVar only needs to last for as long as the menu is open, so
        unlike self._search_var it doesn't need to be a persistent
        attribute; it's referenced by the menu's own radiobutton items,
        which keeps it alive until the menu (and this function's local
        scope, which is what actually holds it) is done."""
        menu = tk.Menu(self, tearoff=0)
        sort_var = tk.StringVar(value=self._sort_label)
        for label in self.SORT_MODES:
            menu.add_radiobutton(
                label=label, value=label, variable=sort_var,
                command=lambda lbl=label: self._handle_sort_selected(lbl),
            )
        x = self._sort_button.winfo_rootx()
        y = self._sort_button.winfo_rooty() + self._sort_button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _handle_sort_selected(self, label: str) -> None:
        self._sort_label = label
        self._rerender()

    def _rerender(self) -> None:
        """Re-derive the displayed rows from self._all_transcripts,
        applying the current search text and sort mode. Called after
        render_transcripts() stores a fresh list from app.py, and also
        directly whenever the search box or sort menu changes, since
        neither of those needs new data, just a different view of what's
        already here."""
        search_text = self._search_var.get().strip().lower()
        filtered = [t for t in self._all_transcripts if search_text in t.title.lower()]

        key_func, reverse = self.SORT_MODES[self._sort_label]
        ordered = sorted(filtered, key=key_func, reverse=reverse)

        self.clear()

        if search_text and not ordered:
            # Only for a search that matched nothing: a space with zero
            # transcripts and no active search still renders as a plain
            # empty list, exactly as it always has (that's pre-existing
            # behavior this feature was never asked to change). This
            # message exists specifically to distinguish "nothing here"
            # from "nothing matches what you typed," a distinction that
            # only becomes possible to confuse once search exists at all.
            ctk.CTkLabel(
                self.entries_frame, text="No transcripts match your search.",
                text_color=WARM_LINE, font=ctk.CTkFont(family=FONT_BODY, size=13),
            ).pack(pady=20)
            return

        for t in ordered:
            self.add_entry(t)

    def add_entry(self, transcript) -> None:
        row = ctk.CTkFrame(self.entries_frame, fg_color=HEARTH_PAPER, corner_radius=10)
        row.pack(fill="x", pady=3, padx=2)

        # delete_button is packed before title_label, even though it sits
        # on the right visually: Tk's pack carves cavity in packing
        # order, not visual order. title_label uses fill="x" + expand=True
        # with no wraplength, so its natural width grows to fit however
        # long transcript.title is; a file import seeds the title from
        # the file's own name (see gui/app.py's
        # _handle_add_from_file_requested()), which runs much longer than
        # a typical short typed-by-hand title. Packing title_label first
        # would let it claim the row's entire cavity before delete_button
        # got a chance to reserve its own space on the right, pushing
        # delete_button fully out of the row for any long-enough title.
        # Reserving delete_button's fixed-size cavity first guarantees
        # it's always visible; title_label then just fills, and gets
        # visually clipped inside, whatever width remains, rather than
        # the button vanishing.
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

        # Rename entry, built up front but never packed until a
        # double-click on title_label starts an edit (see start_rename()
        # below). It swaps into title_label's exact pack slot for the
        # duration of the edit, then swaps back out on commit or cancel,
        # so the row's layout never shifts around it.
        title_entry = ctk.CTkEntry(row, text_color=COCOA_INK, font=title_font)

        # A plain closure flag rather than title_entry.winfo_ismapped():
        # committing or cancelling both end with pack_forget(), which can
        # itself raise a synchronous <FocusOut> on the entry, and relying
        # on "is it currently mapped" to tell a real edit-in-progress
        # apart from that self-triggered follow-up event depends on
        # exactly when Tkinter updates the mapped state relative to
        # firing the event, which isn't something to depend on. This flag
        # is set False before pack_forget() runs, so both commit_rename()
        # and cancel_rename() are safe to call a second time and simply
        # no-op.
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
        # click event; macOS's Ctrl-click also maps to it under Tk) on
        # either the row's own background or the title opens a plain
        # context menu with the transcript's only currently-menu-only
        # action. A fresh tk.Menu is built per click rather than one
        # reused instance, which is cheap and sidesteps having to keep a
        # per-row menu object around just to close over `transcript`.
        # This is a native/undecorated tk.Menu, not a themed CTk widget:
        # CustomTkinter doesn't provide a themed popup menu, but a plain
        # OS-native context menu here is normal and expected, the same
        # way even most fully-themed desktop apps still show the
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
        its own: with no wraplength set it just requests whatever width
        the full string needs. That's what let delete_button get
        squeezed out of the row entirely for long (e.g. filename-
        derived) titles, fixed above by reserving delete_button's own
        space first; once that's fixed, a too-long title instead just
        renders with its raw end cut off wherever space runs out, which
        still isn't great, so this replaces that raw cutoff with a
        "…"-truncated version sized to actually fit.

        Tkinter has no built-in ellipsis truncation (unlike native OS
        controls), so this measures the real pixel width of the label's
        font against the label's own current on-screen width and
        rebuilds the text to fit. It's bound to <Configure> rather than
        computed once because the sidebar is user-resizable (see
        gui/app.py's sidebar drag handlers): a character-count cutoff
        chosen for today's width would be wrong, either still
        overflowing or needlessly aggressive, the moment the sidebar is
        dragged to a different width.

        Reads the font straight off the label's own internal
        tkinter.Label (label._label) rather than rebuilding it from the
        family/size passed into CTkFont: CustomTkinter applies its own
        DPI/widget-scaling on top of that font before it's actually
        drawn (see _apply_font_scaling in customtkinter's ctk_label.py),
        and this guarantees the pixel measurements below match what's
        really on screen instead of drifting at a non-default scaling
        setting. This app already has to fight DPI-scaling quirks
        elsewhere (see gui/theme.py's set_dpi_awareness()/
        apply_linux_dpi_scaling()), so this doesn't add a second,
        independent place that can disagree with Windows about scale.
        _label is private/undocumented, same caveat as
        AddTranscriptDialog._use_chevron_dropdown_arrow()'s reliance on
        CTkOptionMenu's internals; verified against
        customtkinter==6.0.0 (pinned in requirements.txt)."""
        ellipsis = "…"

        def apply_truncation(event=None) -> None:
            available_px = label.winfo_width()
            if available_px <= 1:
                return  # not laid out yet; a later <Configure> will fire once it is
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
        self._all_transcripts = list(transcripts)
        self._rerender()

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