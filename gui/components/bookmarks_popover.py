import customtkinter as ctk

from gui.theme import (
    HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE,
    EMBER_GLOW, EMBER_GLOW_HOVER, FONT_BODY, FONT_HEADING,
    apply_app_icon, center_over_parent,
)


class BookmarksPopover(ctk.CTkToplevel):
    """A small window listing a transcript's bookmarks, with one action to
    add or remove a bookmark at the reader's current word.

    It owns no state of its own: the owner (Canvas or the detached window)
    passes the current bookmark list and reader position in, and is called
    back for the four actions (toggle-here, jump, delete, rename). After any
    mutation the owner re-renders this window with render(), rather than
    this window touching the store itself, which keeps all per-transcript
    persistence on the owner's existing canvas -> app -> store path.

    Each row shows the bookmark's label (or, when it has none, its snippet)
    followed by "word X of Y". A single click jumps there; a double click
    renames it inline, the same way the transcript list does (see
    gui/components/transcript_list_body.py). Because a single click already
    jumps and closes the window, the jump is debounced by a short beat so a
    double click can cancel it and open the edit box instead.

    Rows are a fixed height (ROW_HEIGHT) and the whole row is clickable, not
    just the text, so they're an easy target; the single/double handlers are
    bound to the row frame as well as the label (the delete button, being a
    child widget, keeps its own clicks).

    Jumping closes the window (you've gone where you wanted). Toggling,
    deleting and renaming leave it open, so several can be managed in a
    row."""

    WIDTH = 360
    HEIGHT = 440
    SNIPPET_MAX_CHARS = 44
    # How long a single click waits before it counts as a jump, giving a
    # double click time to arrive and cancel it (see _make_row). Tk's own
    # double-click window is around this long.
    CLICK_DELAY_MS = 250
    # Fixed row height (logical px), enforced with pack_propagate(False), so
    # every row is a comfortable click/touch target regardless of its one
    # line of text. The name label fills this whole height so the full row
    # is clickable, not just the text baseline.
    ROW_HEIGHT = 44

    def __init__(
        self, master, bookmarks, total_words,
        can_bookmark_here, current_index_is_bookmarked,
        on_toggle_here=None, on_jump=None, on_delete=None, on_rename=None, on_closed=None,
    ):
        super().__init__(master)
        # Hidden until built, the same flash-avoidance pattern the other
        # toplevels use (see detached_window.py / settings_window.py).
        self.attributes("-alpha", 0)

        self.on_toggle_here = on_toggle_here
        self.on_jump = on_jump
        self.on_delete = on_delete
        self.on_rename = on_rename
        self.on_closed = on_closed

        self.title("Bookmarks")
        apply_app_icon(self)
        center_over_parent(self, self.WIDTH, self.HEIGHT)
        self.minsize(300, 280)
        self.configure(fg_color=HEARTH_PAPER)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda event=None: self.close())

        self.label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self.small_font = ctk.CTkFont(family=FONT_BODY, size=11)
        self.heading_font = ctk.CTkFont(family=FONT_HEADING, size=16)

        ctk.CTkLabel(
            self, text="Bookmarks", text_color=COCOA_INK, font=self.heading_font,
        ).pack(anchor="w", padx=15, pady=(15, 8))

        self.toggle_button = ctk.CTkButton(
            self, text="", corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.label_font, command=self._handle_toggle_here,
        )
        self.toggle_button.pack(fill="x", padx=15, pady=(0, 10))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=(10, 5), pady=(0, 10))

        # Created once and kept, shown only while the list is empty, so
        # render() can reuse it instead of recreating it each time.
        self.empty_label = ctk.CTkLabel(
            self.list_frame, text="No bookmarks yet.", text_color=COCOA_INK, font=self.small_font,
        )

        self.render(bookmarks, total_words, can_bookmark_here, current_index_is_bookmarked)

        self.lift()
        self.after(60, self._reveal_now)

    def _reveal_now(self) -> None:
        if not self.winfo_exists():
            return
        self.update_idletasks()
        self.attributes("-alpha", 1)
        self.focus_force()

    def render(self, bookmarks, total_words, can_bookmark_here, current_index_is_bookmarked) -> None:
        """Rebuild the toggle button's label/state and the list of rows from
        the owner's current data. Called on open and after every mutation."""
        if not self.winfo_exists():
            return

        if not can_bookmark_here:
            # No live word right now (edit view, or a finished session).
            self.toggle_button.configure(text="Add bookmark here", state="disabled")
        elif current_index_is_bookmarked:
            self.toggle_button.configure(text="Remove bookmark here", state="normal")
        else:
            self.toggle_button.configure(text="Add bookmark here", state="normal")

        for child in self.list_frame.winfo_children():
            if child is not self.empty_label:
                child.destroy()
        self.empty_label.pack_forget()

        if not bookmarks:
            self.empty_label.pack(anchor="w", padx=8, pady=(6, 0))
            return

        for bookmark in bookmarks:
            self._make_row(bookmark, total_words)

    def _make_row(self, bookmark, total_words) -> None:
        # Fixed height, enforced by turning off geometry propagation, so the
        # row stays a comfortable target no matter its single line of text.
        row = ctk.CTkFrame(self.list_frame, fg_color=WARM_TAUPE, corner_radius=8, height=self.ROW_HEIGHT)
        row.pack(fill="x", pady=(0, 6))
        row.pack_propagate(False)

        position = (
            f"word {bookmark.index + 1:,} of {total_words:,}" if total_words
            else f"word {bookmark.index + 1:,}"
        )
        # The label wins over the snippet when it's set; otherwise the
        # snippet stands in, so unlabeled bookmarks read exactly as before.
        name = (bookmark.label or bookmark.snippet).strip()
        if len(name) > self.SNIPPET_MAX_CHARS:
            name = name[: self.SNIPPET_MAX_CHARS - 1].rstrip() + "…"
        text = f"{name}   {position}" if name else position

        # Packed before the name label so its fixed-width cavity is reserved
        # first and a long name can't push it out of the row (same reasoning
        # as the transcript list's delete button). No pady: pack centres it
        # vertically in the fixed-height row on its own.
        delete_button = ctk.CTkButton(
            row, text="✕", width=32, height=32, corner_radius=8,
            fg_color="transparent", hover_color=WARM_LINE, text_color=COCOA_INK,
            font=self.label_font, command=lambda idx=bookmark.index: self._handle_delete(idx),
        )
        delete_button.pack(side="right", padx=(0, 6))

        # fill="both" so the label occupies the row's full height, making the
        # whole left area (not just the text line) a click target. The text
        # still sits left and vertically centred (CTkLabel centres its text).
        name_label = ctk.CTkLabel(
            row, text=text, anchor="w", cursor="hand2",
            text_color=COCOA_INK, font=self.small_font,
        )
        name_label.pack(side="left", fill="both", expand=True, padx=(10, 0))

        # Built up front, swapped into name_label's slot only while renaming
        # (see start_rename), mirroring transcript_list_body.py's row rename.
        # It fills only "x" (natural height, centred) so swapping it in
        # doesn't make the row look like one giant text field.
        rename_entry = ctk.CTkEntry(row, text_color=COCOA_INK, font=self.small_font)

        # editing: a real edit is in progress (guards double commit/cancel).
        # pending: the id of a scheduled single-click jump, so a double
        # click can cancel it before it fires.
        rename_state = {"editing": False}
        click_state = {"pending": None}

        def start_rename(event=None):
            if rename_state["editing"]:
                return
            rename_state["editing"] = True
            rename_entry.delete(0, "end")
            rename_entry.insert(0, bookmark.label)  # prefill the current label (may be "")
            name_label.pack_forget()
            rename_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            rename_entry.focus_set()
            rename_entry.select_range(0, "end")
            rename_entry.icursor("end")

        def end_rename():
            rename_state["editing"] = False
            rename_entry.pack_forget()
            name_label.pack(side="left", fill="both", expand=True, padx=(10, 0))

        def commit_rename(event=None):
            if not rename_state["editing"]:
                return
            new_label = rename_entry.get().strip()
            end_rename()
            # An empty string is a real value here: it clears the label and
            # the row falls back to the snippet (see set_bookmark_label).
            if new_label != bookmark.label:
                self._handle_rename(bookmark.index, new_label)

        def cancel_rename(event=None):
            if not rename_state["editing"]:
                return
            end_rename()
            # Stop this Escape from also reaching the window's own Escape
            # binding, which would close the whole popover.
            return "break"

        rename_entry.bind("<Return>", commit_rename)
        rename_entry.bind("<FocusOut>", commit_rename)
        rename_entry.bind("<Escape>", cancel_rename)

        def fire_jump():
            click_state["pending"] = None
            self._handle_jump(bookmark.index)

        def on_single_click(event=None):
            if rename_state["editing"] or click_state["pending"] is not None:
                return
            click_state["pending"] = self.after(self.CLICK_DELAY_MS, fire_jump)

        def on_double_click(event=None):
            if click_state["pending"] is not None:
                self.after_cancel(click_state["pending"])
                click_state["pending"] = None
            start_rename()

        # Bound to both the row and the label so a click anywhere in the row
        # counts, not only on the text. Tk delivers a click to one widget's
        # bindings (no bubbling to the parent), so the row's own background
        # and the label don't double-fire, and the delete button keeps its
        # own clicks.
        for widget in (row, name_label):
            widget.bind("<Button-1>", on_single_click)
            widget.bind("<Double-Button-1>", on_double_click)

    def _handle_toggle_here(self) -> None:
        if self.on_toggle_here:
            self.on_toggle_here()

    def _handle_jump(self, index) -> None:
        if self.on_jump:
            self.on_jump(index)

    def _handle_delete(self, index) -> None:
        if self.on_delete:
            self.on_delete(index)

    def _handle_rename(self, index, label) -> None:
        if self.on_rename:
            self.on_rename(index, label)

    def close(self) -> None:
        """Close the window and let the owner drop its reference."""
        if self.on_closed:
            self.on_closed(self)
        self.destroy()