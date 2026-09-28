import tkinter as tk

import customtkinter as ctk

from core.normalizer import can_revert, toggle_normalization
from gui.icons import normalize_icon, revert_icon
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, FONT_BODY


class TranscriptInput(ctk.CTkFrame):
    """Paste-in prompt shown when the selected transcript has no text yet,
    with Normalize and Start reading buttons underneath.

    The Normalize button toggles between a page-with-checkmark icon
    (normalize) and a plain page icon (revert); see gui/icons.py, and
    core/normalizer.py's toggle_normalization() for what each click
    does. This widget only keeps a copy of the transcript's undo
    information to decide which icon to show. Whoever owns it passes
    that in with set_normalization() and saves the result of each click
    through on_normalized.

    A click that finds nothing to change shows "Nothing to change" beside
    the button for a moment, so it doesn't look like the click was lost.

    Whether a click also splits long paragraphs is a global Settings
    toggle, passed in and kept current through set_split_long_paragraphs().

    Right-clicking a selection in the edit box opens a small Play / Detach
    context menu (see _show_selection_menu), for running just the
    highlighted part of the transcript. The owner decides what those do
    by passing on_play_selection and on_detach_selection; when neither is
    given, no menu appears."""

    FEEDBACK_MS = 2000

    def __init__(self, master, on_submit, initial_text: str = "", on_normalized=None, split_long_paragraphs: bool = False, on_play_selection=None, on_detach_selection=None):
        super().__init__(master, fg_color="transparent")
        self.on_submit = on_submit
        self.on_normalized = on_normalized
        self.on_play_selection = on_play_selection
        self.on_detach_selection = on_detach_selection
        self._pre_normalize_text = ""
        self._normalized_text = ""
        self._feedback_after_id = None
        self._split_long_paragraphs = split_long_paragraphs
        # The right-click popup is created once, on first use, then reused:
        # shown by deiconify() and hidden by withdraw(), never destroyed
        # until this widget is (see _open_selection_menu for why it must
        # outlive its own close). _selection_menu holds that reused popup,
        # _selection_menu_visible tracks whether it's currently shown.
        self._selection_menu = None
        self._selection_menu_visible = False
        self._outside_click_bound = False
        self._escape_bound = False

        self.textbox = ctk.CTkTextbox(self, width=500, height=250)
        self.textbox.pack(padx=20, pady=20, fill="both", expand=True)
        if initial_text:
            self.textbox.insert("1.0", initial_text)

        # Tk raises <<Modified>> for typing, deleting, pasting and for
        # changes made in code, so it keeps the button's icon in step
        # with the text whatever changed it.
        self.textbox.bind("<<Modified>>", self._handle_text_modified)

        # Right-click on a selection offers to Play or Detach just that
        # part of the transcript. Bound on the underlying tkinter Text,
        # since that's where the selection and the mouse event live.
        inner_textbox = getattr(self.textbox, "_textbox", None)
        if inner_textbox is not None:
            inner_textbox.bind("<Button-3>", self._show_selection_menu)

        # Three columns: Normalize at the far left, lined up with the text
        # box's left edge, and Start reading in the middle. uniform keeps
        # the two outer columns the same width, so Start reading stays
        # truly centered however wide the window is.
        #
        # The Normalize button is 36x28 with Start reading's rounded
        # corners. CTkButton pads its content by the corner radius (6px)
        # at each side and its border spacing (2px) at top and bottom,
        # so the 24px icon fills it exactly: 24 + 2*6 wide, 24 + 2*2 tall.
        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=(0, 20))
        button_row.grid_columnconfigure(0, weight=1, uniform="side")
        button_row.grid_columnconfigure(1, weight=0)
        button_row.grid_columnconfigure(2, weight=1, uniform="side")

        self.start_button = ctk.CTkButton(button_row, text="Start reading", command=self._handle_submit)
        self.start_button.grid(row=0, column=1)

        self._normalize_image = normalize_icon()
        self._revert_image = revert_icon()
        self.normalize_button = ctk.CTkButton(
            button_row, text="", image=self._normalize_image, width=36, height=28,
            command=self._handle_normalize,
        )
        # The plain Tk label CTkButton shows the image in adds a small
        # border of its own, and how big it is varies by platform. Removing
        # it keeps the button exactly 36x28 everywhere. CTkButton has no
        # public option for this, hence the private _image_label.
        self.normalize_button._image_label.configure(borderwidth=0, padx=0, pady=0, highlightthickness=0)
        self.normalize_button.grid(row=0, column=0, sticky="w")

        # Shares the button's column, so Start reading stays centered.
        self.feedback_label = ctk.CTkLabel(
            button_row, text="", text_color="gray50", font=ctk.CTkFont(size=12),
        )
        self.feedback_label.grid(row=0, column=0, sticky="w", padx=(44, 0))

    def get_text(self) -> str:
        """Return whatever's currently typed, submitted or not."""
        return self.textbox.get("1.0", "end")

    def set_text(self, text: str) -> None:
        """Replace the textbox's contents."""
        self.textbox.delete("1.0", "end")
        if text:
            self.textbox.insert("1.0", text)
        self._refresh_normalize_button()

    def set_normalization(self, pre_normalize_text: str, normalized_text: str) -> None:
        """Take the current transcript's undo information (see
        core/models.py). Must be called whenever a different transcript's
        text is shown, so the icon never reflects the previous one."""
        self._pre_normalize_text = pre_normalize_text
        self._normalized_text = normalized_text
        self._refresh_normalize_button()

    def set_split_long_paragraphs(self, enabled: bool) -> None:
        """Whether the Normalize button also splits a long wall of prose
        into paragraphs. Read at click time by _handle_normalize(); see
        core/normalizer.py. Kept in step by whoever owns this widget when
        the Settings toggle changes."""
        self._split_long_paragraphs = enabled

    def _handle_normalize(self) -> None:
        text_before = self.get_text().strip()
        result = toggle_normalization(
            self.get_text(), self._pre_normalize_text, self._normalized_text,
            split_long_paragraphs=self._split_long_paragraphs,
        )
        self._pre_normalize_text = result.pre_normalize_text
        self._normalized_text = result.normalized_text
        self.set_text(result.text)
        if result.text == text_before:
            self._show_feedback("Nothing to change")
        if self.on_normalized:
            self.on_normalized(result)

    def _show_feedback(self, message: str) -> None:
        if self._feedback_after_id is not None:
            self.after_cancel(self._feedback_after_id)
        self.feedback_label.configure(text=message)
        self._feedback_after_id = self.after(self.FEEDBACK_MS, self._clear_feedback)

    def _clear_feedback(self) -> None:
        self._feedback_after_id = None
        # The window may have closed in the meantime (a detached window
        # closed within the two seconds), with this label gone with it.
        if self.feedback_label.winfo_exists():
            self.feedback_label.configure(text="")

    def _handle_text_modified(self, event=None) -> None:
        # Tk only raises <<Modified>> when its modified flag changes, so
        # the flag has to be reset each time to hear about the next edit.
        # Resetting it raises the event once more, with the flag already
        # False, which is skipped here.
        if not self.textbox.edit_modified():
            return
        self.textbox.edit_modified(False)
        self._refresh_normalize_button()

    def _refresh_normalize_button(self) -> None:
        if can_revert(self.get_text(), self._pre_normalize_text, self._normalized_text):
            self.normalize_button.configure(image=self._revert_image)
        else:
            self.normalize_button.configure(image=self._normalize_image)

    def _handle_submit(self) -> None:
        self.on_submit(self.get_text())

    def _selected_text(self) -> str:
        """The transcript text currently highlighted in the edit box, or an
        empty string if nothing (or only whitespace) is selected."""
        inner = getattr(self.textbox, "_textbox", None)
        if inner is None or not inner.tag_ranges("sel"):
            return ""
        try:
            return inner.get("sel.first", "sel.last").strip()
        except tk.TclError:
            return ""

    def _show_selection_menu(self, event):
        # Only open the menu when text is actually selected and at least
        # one action is wired up; otherwise a right-click does nothing.
        text = self._selected_text()
        if not text or not (self.on_play_selection or self.on_detach_selection):
            return None
        self._close_selection_menu()
        self._open_selection_menu(text, event.x_root, event.y_root)
        return "break"

    def _open_selection_menu(self, text: str, x_root: int, y_root: int) -> None:
        """A small right-click popup offering to run the selected text.
        Built as a borderless Toplevel positioned with geometry() rather
        than a native tk.Menu: under CustomTkinter's high-DPI window
        scaling tk_popup places a native menu far from the cursor, while a
        plain Toplevel positioned with geometry() lands exactly at the
        cursor at any scale. Colours follow the app theme (see
        gui/theme.py): a soft light surface with dark text in Light mode, a
        soft near-black surface with light text in Dark mode, and a warm
        neutral highlight for the hovered row rather than the system's
        default blue. Clicking a row runs it and closes the popup; clicking
        away or pressing Escape closes it with no action.

        The popup is created once and then reused: shown here with
        deiconify() and hidden by _close_selection_menu() with withdraw(),
        never destroyed between uses. This is deliberate, and the reason is
        CustomTkinter. When choosing Detach opens a CTkToplevel, that
        window's Windows-only titlebar setup snapshots whatever has focus
        (this popup) and re-applies it a moment later via
        after(10, widget.focus). If the popup had been destroyed on click
        (the obvious approach), that delayed focus would land on a
        destroyed window and Tk would raise "bad window path name". Keeping
        the single popup alive means that delayed focus always finds a real
        window; it just focuses a hidden one, which is harmless. The popup
        is a child of this widget, so it's torn down with it.

        Dismissal is driven from the main window (a one-time click binding
        and an Escape binding), so it works without the popup needing its
        own keyboard focus (see _ensure_outside_click_binding and
        _ensure_escape_binding)."""
        popup = self._selection_menu
        if popup is None or not popup.winfo_exists():
            popup = tk.Toplevel(self)
            popup.withdraw()  # placed before it's shown, so it never flashes at 0,0
            popup.overrideredirect(True)
            popup.configure(bg=WARM_LINE)  # a 1px border around the inner surface
            self._selection_menu = popup
        else:
            # Reused popup: clear the previous rows before rebuilding them,
            # since the selected text (and so each row's action) has changed.
            for child in popup.winfo_children():
                child.destroy()

        inner = tk.Frame(popup, bg=HEARTH_PAPER, bd=0)
        inner.pack(padx=1, pady=1)

        rows = []
        if self.on_play_selection:
            rows.append(("Play", self._dispatch_play))
        if self.on_detach_selection:
            rows.append(("Detach", self._dispatch_detach))
        for label, dispatch in rows:
            row = tk.Label(
                inner, text=label, bg=HEARTH_PAPER, fg=COCOA_INK,
                font=(FONT_BODY, 11), anchor="w", padx=18, pady=6, cursor="hand2",
            )
            row.pack(fill="x")
            row.bind("<Enter>", lambda e, r=row: r.configure(bg=WARM_TAUPE))
            row.bind("<Leave>", lambda e, r=row: r.configure(bg=HEARTH_PAPER))
            row.bind("<Button-1>", lambda e, d=dispatch: self._choose_selection(d, text))

        self._place_selection_menu(popup, x_root, y_root)
        popup.deiconify()
        self._selection_menu_visible = True
        # Close on a click elsewhere in the main window, or on Escape. Both
        # are bound on the main window, not the popup, so they work without
        # the popup taking focus (see the docstring). No Tk grab is used: a
        # grab on a borderless popup can leave the whole app unresponsive,
        # its own close button included, if a dismissal path ever fails to
        # run. The popup is its own toplevel, so clicks on its rows don't
        # reach the outside-click binding.
        self._ensure_outside_click_binding()
        self._ensure_escape_binding()

    def _place_selection_menu(self, popup, x_root: int, y_root: int) -> None:
        """Put the popup at the cursor, nudged back onto the screen if it
        would spill past the right or bottom edge. The coordinates are real
        screen pixels, which geometry() places correctly at any display
        scaling (see _open_selection_menu)."""
        popup.update_idletasks()
        width = popup.winfo_reqwidth()
        height = popup.winfo_reqheight()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(0, min(x_root, screen_w - width))
        y = max(0, min(y_root, screen_h - height))
        popup.geometry(f"+{x}+{y}")

    def _ensure_outside_click_binding(self) -> None:
        # Bound once on the main window and left in place for the widget's
        # life: it's a cheap no-op whenever no popup is open, which avoids
        # bind/unbind churn and the funcid pitfalls that come with it.
        if self._outside_click_bound:
            return
        try:
            self.winfo_toplevel().bind("<Button-1>", self._handle_outside_click, add="+")
            self._outside_click_bound = True
        except tk.TclError:
            pass

    def _handle_outside_click(self, event):
        # A left-click landed somewhere in the main window while a selection
        # popup is open. The popup is its own toplevel, so clicks on its own
        # rows never reach here; anything that does means the click was away
        # from the popup, so close it. A no-op when no popup is open.
        if self._selection_menu_visible:
            self._close_selection_menu()
        return None

    def _ensure_escape_binding(self) -> None:
        # Bound once on the main window and left in place for the widget's
        # life, like the outside-click binding: a cheap no-op whenever no
        # popup is open. Escape is handled here rather than on the popup so
        # it works without the popup taking focus (see _open_selection_menu).
        if self._escape_bound:
            return
        try:
            self.winfo_toplevel().bind("<Escape>", self._handle_escape_key, add="+")
            self._escape_bound = True
        except tk.TclError:
            pass

    def _handle_escape_key(self, event):
        # Close an open selection popup on Escape, and swallow the keypress
        # so it doesn't also trigger anything else. When no popup is open,
        # do nothing and let Escape fall through to any other handler (the
        # app's reading-stop shortcut, for one).
        if self._selection_menu_visible:
            self._close_selection_menu()
            return "break"
        return None

    def _choose_selection(self, dispatch, text: str) -> str:
        self._close_selection_menu()
        dispatch(text)
        return "break"

    def _close_selection_menu(self) -> None:
        # Hide the reused popup rather than destroying it, so a focus call
        # CustomTkinter may have scheduled on it can't hit a dead window
        # (see _open_selection_menu). It's recreated only if it was somehow
        # already gone.
        if not self._selection_menu_visible:
            return
        self._selection_menu_visible = False
        popup = self._selection_menu
        if popup is None:
            return
        try:
            popup.withdraw()
        except tk.TclError:
            pass

    def _dispatch_play(self, text: str) -> None:
        if self.on_play_selection:
            self.on_play_selection(text)

    def _dispatch_detach(self, text: str) -> None:
        if self.on_detach_selection:
            self.on_detach_selection(text)