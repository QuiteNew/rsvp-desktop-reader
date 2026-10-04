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
    back for the three actions (toggle-here, jump, delete). After any
    mutation the owner re-renders this window with render(), rather than
    this window touching the store itself, which keeps all per-transcript
    persistence on the owner's existing canvas -> app -> store path.

    Jumping closes the window (you've gone where you wanted). Toggling and
    deleting leave it open, so several can be managed in a row."""

    WIDTH = 360
    HEIGHT = 440
    SNIPPET_MAX_CHARS = 44

    def __init__(
        self, master, bookmarks, total_words,
        can_bookmark_here, current_index_is_bookmarked,
        on_toggle_here=None, on_jump=None, on_delete=None, on_closed=None,
    ):
        super().__init__(master)
        # Hidden until built, the same flash-avoidance pattern the other
        # toplevels use (see detached_window.py / settings_window.py).
        self.attributes("-alpha", 0)

        self.on_toggle_here = on_toggle_here
        self.on_jump = on_jump
        self.on_delete = on_delete
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
        row = ctk.CTkFrame(self.list_frame, fg_color=WARM_TAUPE, corner_radius=8)
        row.pack(fill="x", pady=(0, 6))

        position = (
            f"word {bookmark.index + 1:,} of {total_words:,}" if total_words
            else f"word {bookmark.index + 1:,}"
        )
        snippet = bookmark.snippet.strip()
        if len(snippet) > self.SNIPPET_MAX_CHARS:
            snippet = snippet[: self.SNIPPET_MAX_CHARS - 1].rstrip() + "…"
        label = f"{position}   {snippet}" if snippet else position

        jump_button = ctk.CTkButton(
            row, text=label, anchor="w", corner_radius=8,
            fg_color="transparent", hover_color=WARM_LINE, text_color=COCOA_INK,
            font=self.small_font, command=lambda idx=bookmark.index: self._handle_jump(idx),
        )
        jump_button.pack(side="left", fill="x", expand=True, padx=(4, 0), pady=4)

        delete_button = ctk.CTkButton(
            row, text="✕", width=28, corner_radius=8,
            fg_color="transparent", hover_color=WARM_LINE, text_color=COCOA_INK,
            font=self.label_font, command=lambda idx=bookmark.index: self._handle_delete(idx),
        )
        delete_button.pack(side="right", padx=(0, 4), pady=4)

    def _handle_toggle_here(self) -> None:
        if self.on_toggle_here:
            self.on_toggle_here()

    def _handle_jump(self, index) -> None:
        if self.on_jump:
            self.on_jump(index)

    def _handle_delete(self, index) -> None:
        if self.on_delete:
            self.on_delete(index)

    def close(self) -> None:
        """Close the window and let the owner drop its reference."""
        if self.on_closed:
            self.on_closed(self)
        self.destroy()