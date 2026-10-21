import re
import tkinter as tk

import customtkinter as ctk

from core.bold_spans import MAX_BOLD_LINE, has_long_line, tk_spans
from core.font_choice import bold_family
from core.normalizer import can_revert, toggle_normalization
from core.rich_copy import cf_html, segments_text
from gui.icons import bold_starts_icon, normalize_icon, revert_icon
from gui.rich_clipboard import copy_rich
from gui.theme import HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, FONT_BODY

# The Tk text tag that draws the start of every word in bold.
BOLD_TAG = "bold_starts"

# What the feedback label says when a line was too long to be bolded, see
# core/bold_spans.py for why there is a limit. Short, since it has to fit beside
# Start reading in the narrow detached window.
LONG_LINES_NOTE = "Long lines stay plain"

# What the feedback label says after Copy with bold in the right-click menu. When
# the bold could not go along, the words are still copied, and the label says so.
COPIED_WITH_BOLD = "Copied with bold"
COPIED_PLAIN = "Copied without bold"

# How many bold stretches go into one tag_add call. A book has a great many of
# them, and a few hundred small calls are quicker than one enormous one.
_TAG_BATCH = 500

# The body of the Tcl procedure that stands in front of the edit box's Text
# command, see _EditBox._watch_edits for why it is Tcl and not Python. The @...@
# words are filled in with the real command names. An insert, a delete or a
# replace first asks @BEFORE@ which lines it will touch, runs the real command,
# and only if that worked tells @AFTER@. Whatever the real command answers, a
# result or an error, is handed back exactly as it came. (The level is raised by
# one first because catch reports 0, which would make return carry on to the
# last line instead of leaving.) Every other call is passed straight on.
_FORWARDER_BODY = """
switch -exact -- [lindex $args 0] {
    insert - delete - replace {
        set span [@BEFORE@ {*}$args]
        set code [catch {@ORIG@ {*}$args} result options]
        if {$code == 0 && $span ne {}} {
            @AFTER@ {*}$span
        }
        dict incr options -level
        return -options $options $result
    }
}
tailcall @ORIG@ {*}$args
"""

# How many columns this Tk gives a character outside the Basic Multilingual
# Plane (an emoji). Found out the first time it is needed, see _tk_astral_width.
_astral_width = None


def _tcl_word(text: str) -> str:
    """text as a single word of a Tcl script. The names it is used for here, a
    widget's path and the commands tkinter registers, are made of letters, digits
    and . ! _ only, which Tcl takes exactly as they are. Anything else would need
    quoting, and is refused rather than guessed at."""
    if not re.fullmatch(r"[\w.!]+", text):
        raise ValueError(f"not safe to use as a Tcl command name: {text!r}")
    return text


def _tk_astral_width(widget) -> int:
    """How many columns Tk counts an emoji as: 2 in Tk 8.6, which is what
    Python 3.13 on Windows ships, and 1 in Tk 9. Asked of a throwaway Text widget
    once and remembered, since it is the same for every widget in the process.
    Guessing from the version number would be shakier than just looking."""
    global _astral_width
    if _astral_width is None:
        probe = tk.Text(widget)
        try:
            probe.insert("1.0", chr(0x1F600))
            _astral_width = max(1, int(probe.index("1.end").split(".")[1]))
        finally:
            probe.destroy()
    return _astral_width


class _EditBox(ctk.CTkTextbox):
    """The edit box, with two extras: it says so when its font changes, and it
    says which lines were edited.

    The font. CustomTkinter hands the inner Text widget a new font whenever the
    display scaling changes (the window moved to another monitor, say) or the
    font is reconfigured, and it does that in exactly two methods. The bold word
    starts are a tag with a font of its own, which would be left at the old size
    without being told, so the owner passes on_font_changed to hear about it.
    Tk sends no event for this: the inner Text is not resized when only its font
    is, so a <Configure> binding would never fire.

    The edits. Typing, pasting and cutting do not go through any Python method:
    Tk's own key bindings call the Text widget's command directly. So the
    command is put behind a small forwarder (the idea Python's IDLE editor
    uses): every call passes through it, unchanged, and when it is an insert, a
    delete or a replace, on_edited(first, last) is called afterwards with the
    first and last line the edit touched, counted from 1. When the lines cannot
    be worked out it is called with (None, None), which means anything may have
    changed. Comparing the text before and after instead is not enough: Tk keeps
    a tag with the characters it was put on, so when new text pushes old text
    down a line, the old line has not changed and yet its tag has moved away."""

    def __init__(self, *args, on_font_changed=None, on_edited=None, **kwargs):
        # Set before anything else, since CustomTkinter can already call the
        # methods below while the widget is being built.
        self._on_font_changed = on_font_changed
        self._on_edited = on_edited
        self._tk_original = None
        super().__init__(*args, **kwargs)
        self._watch_edits()

    def _set_scaling(self, *args, **kwargs):
        super()._set_scaling(*args, **kwargs)
        self._tell_font_changed()

    def _update_font(self):
        super()._update_font()
        self._tell_font_changed()

    def _tell_font_changed(self):
        if self._on_font_changed is not None:
            self._on_font_changed()

    def _watch_edits(self) -> None:
        """Put the forwarder in front of the Text widget's own command. The real
        command is renamed out of the way, and a small Tcl procedure (see
        _FORWARDER_BODY) takes over its name.

        The forwarder is Tcl and not a Python function on purpose. Tk's own
        bindings call the widget command inside a Tcl catch where an error is
        part of the plan: copy and cut with nothing selected, and paste on
        Windows, which first tries to delete the selection. A Python command that
        raised there would be caught by Tcl, but tkinter still remembers the
        exception and raises it again out of mainloop(), which closed the whole
        app. As a Tcl procedure every error goes back to the caller untouched, as
        it does on a plain Text widget. Only the two small Python hooks below are
        called, and register() wraps them so that they cannot raise into Tcl."""
        inner = self._textbox
        name = str(inner)
        original = name + "_original"
        words = {
            "@ORIG@": original,
            "@BEFORE@": self.register(self._before_edit),
            "@AFTER@": self.register(self._after_edit),
        }
        body = _FORWARDER_BODY
        for placeholder, word in words.items():
            body = body.replace(placeholder, _tcl_word(word))
        self._tk_original = original
        inner.tk.call("rename", name, original)
        inner.tk.call("proc", name, "args", body)

    def _unwatch_edits(self) -> None:
        """Take the forwarder out again and give the real command its name back."""
        original, self._tk_original = self._tk_original, None
        if original is None:
            return
        name = str(self._textbox)
        try:
            self.tk.call("rename", name, "")
            self.tk.call("rename", original, name)
        except tk.TclError:
            pass

    def destroy(self):
        self._unwatch_edits()
        super().destroy()

    def _before_edit(self, *args):
        """Called by the forwarder before an insert, a delete or a replace. The
        lines it will touch as Tcl text, "first last" with "none" for a line that
        cannot be told, or an empty string when there is nothing to report."""
        if self._on_edited is None:
            return ""
        edited = self._edit_lines(args)
        if not edited:
            return ""
        return " ".join("none" if line is None else str(line) for line in edited)

    def _after_edit(self, first, last):
        """Called by the forwarder once the edit has gone through."""
        if self._on_edited is None:
            return
        self._on_edited(*(None if line == "none" else int(line) for line in (first, last)))

    def _edit_lines(self, args):
        """For a call that changes the text: the (first, last) line it touches,
        as they will be numbered once it is done. (None, None) when that cannot
        be told, and False for a call that does not change the text. Worked out
        before the call, while indexes like "insert" still mean what they meant.
        Undo and redo need no case of their own: Tk carries them out by running
        ordinary inserts and deletes through the widget command."""
        command = args[0] if args else ""
        if command == "insert":
            index, new_text = args[1], args[2::2]
        elif command == "replace":
            index, new_text = args[1], args[3::2]
        elif command == "delete":
            if len(args) > 3:
                # Several ranges in one call: Tk's own bindings never do this.
                return (None, None)
            index, new_text = args[1], ()
        else:
            return False
        try:
            line = self._line_of(index)
        except tk.TclError:
            # A bad index: the call itself will fail with the proper message.
            return False
        return line, line + sum(str(piece).count("\n") for piece in new_text)

    def _line_of(self, index) -> int:
        """The line an index points at. An index past the end, as "end" is,
        means the last line, which is where Tk puts text sent there."""
        original = self._tk_original
        line = int(str(self.tk.call(original, "index", index)).split(".")[0])
        return min(line, int(str(self.tk.call(original, "index", "end-1c")).split(".")[0]))


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

    A click that finds nothing to change shows "Nothing to change" at the
    right-hand end of the button row for a moment, so it doesn't look like the
    click was lost.

    The button next to Normalize draws the start of every word in the edit box
    in bold, or stops again. It only changes how the text looks: the text is
    never touched, so saving, Start reading and Normalize's revert check all
    see the same words as before. The bold is a Tk tag laid over the text (see
    core/bold_spans.py and core/bold_starts.py for where it goes). Typing,
    pasting or deleting bolds again just the lines that were touched (see
    _EditBox for how they are found), so the look keeps up with the text
    without redoing all of it. Whoever owns this
    widget passes the starting state in and is told about each click
    through on_bold_starts_toggled; set_bold_starts() is how it changes the
    state from outside, for instance to keep several edit boxes in step.

    Whether a click also splits long paragraphs is a global Settings
    toggle, passed in and kept current through set_split_long_paragraphs().

    Right-clicking a selection in the edit box opens a small context menu (see
    _show_selection_menu). Play and Detach run just the highlighted part of the
    transcript, and the owner decides what those do by passing
    on_play_selection and on_detach_selection. Copy with bold is there while the
    bold look is on. When none of them is on offer, no menu appears.

    With the bold look on, copying a selection (Ctrl+C or that menu entry) puts
    the bold on the Windows clipboard next to the plain text, so that Word shows
    it. Notepad and everything else that only reads plain text gets the same
    words without it. See _copy_with_bold."""

    FEEDBACK_MS = 2000

    def __init__(self, master, on_submit, initial_text: str = "", on_normalized=None, split_long_paragraphs: bool = False, on_play_selection=None, on_detach_selection=None, bold_starts: bool = False, on_bold_starts_toggled=None):
        super().__init__(master, fg_color="transparent")
        self.on_submit = on_submit
        self.on_normalized = on_normalized
        self.on_play_selection = on_play_selection
        self.on_detach_selection = on_detach_selection
        self.on_bold_starts_toggled = on_bold_starts_toggled
        self._bold_starts = bold_starts
        # True while the text is being replaced in one go (see set_text and the
        # start of __init__), so those edits are not bolded line by line just
        # before the whole text is bolded at once.
        self._edits_paused = True
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

        self.textbox = _EditBox(
            self, width=500, height=250,
            on_font_changed=self._handle_font_changed, on_edited=self._handle_edited_lines,
        )
        self.textbox.pack(padx=20, pady=20, fill="both", expand=True)
        if initial_text:
            self.textbox.insert("1.0", initial_text)
        # Clear Tk's modified flag that the insert above just set. Tk only
        # raises <<Modified>> on a False->True transition, so if the flag is
        # left True from construction, the binding below never fires again
        # and the Normalize/Revert icon stops tracking live edits (see
        # _handle_text_modified, the only thing that resets it). A no-op when
        # initial_text is empty.
        self.textbox.edit_modified(False)

        # Tk raises <<Modified>> for typing, deleting, pasting and for
        # changes made in code, so it keeps the button's icon in step
        # with the text whatever changed it.
        self.textbox.bind("<<Modified>>", self._handle_text_modified)

        # Right-click on a selection offers to Play or Detach just that
        # part of the transcript, or to copy it with its bold. Bound on the
        # underlying tkinter Text, since that's where the selection and the
        # mouse event live.
        inner_textbox = getattr(self.textbox, "_textbox", None)
        if inner_textbox is not None:
            inner_textbox.bind("<Button-3>", self._show_selection_menu)
            # Ctrl+C. Tk's own copy puts plain text on the clipboard, so with the
            # bold look on this one goes first and carries the bold along too.
            inner_textbox.bind("<<Copy>>", self._handle_copy_event)

        # Three columns: Normalize and the bold word starts button at the far
        # left, lined up with the text box's left edge, and Start reading in
        # the middle. uniform keeps the two outer columns the same width, so
        # Start reading stays truly centered however wide the window is.
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

        # The bold word starts button: the same size and colour as Normalize,
        # with the same treatment of the image label, and 8px to its right. Its
        # icon is what says whether the look is on, see _refresh_bold_starts.
        self._bold_off_image = bold_starts_icon(False)
        self._bold_on_image = bold_starts_icon(True)
        self.bold_starts_button = ctk.CTkButton(
            button_row, text="", image=self._bold_off_image, width=36, height=28,
            command=self._handle_bold_starts_click,
        )
        self.bold_starts_button._image_label.configure(borderwidth=0, padx=0, pady=0, highlightthickness=0)
        self.bold_starts_button.grid(row=0, column=0, sticky="w", padx=(44, 0))

        # At the right-hand end of the row, in the column that mirrors the two
        # buttons. Beside the buttons there is no room for it any more: in the
        # 500px detached window it would run into Start reading.
        self.feedback_label = ctk.CTkLabel(
            button_row, text="", text_color="gray50", font=ctk.CTkFont(size=12),
        )
        self.feedback_label.grid(row=0, column=2, sticky="e")

        self._edits_paused = False
        self._refresh_bold_starts()

    def get_text(self) -> str:
        """Return whatever's currently typed, submitted or not."""
        return self.textbox.get("1.0", "end")

    def set_text(self, text: str) -> None:
        """Replace the textbox's contents."""
        self._edits_paused = True
        try:
            self.textbox.delete("1.0", "end")
            if text:
                self.textbox.insert("1.0", text)
        finally:
            self._edits_paused = False
        # Reset the modified flag after a programmatic replace, for the same
        # reason as in __init__: keep the <<Modified>> handler live for the
        # next real edit. The icon itself is refreshed directly just below.
        self.textbox.edit_modified(False)
        self._refresh_normalize_button()
        # The replace above wiped the tag along with the old text.
        if self._bold_starts:
            self._apply_bold_starts()

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

    def set_bold_starts(self, enabled: bool) -> None:
        """Show or stop showing the start of every word in bold. Does nothing
        when it is already so. This is how an owner keeps edit boxes in step;
        it does not call on_bold_starts_toggled, which is only for a click."""
        enabled = bool(enabled)
        if enabled == self._bold_starts:
            return
        self._bold_starts = enabled
        self._refresh_bold_starts()

    def _handle_bold_starts_click(self) -> None:
        self.set_bold_starts(not self._bold_starts)
        if self.on_bold_starts_toggled:
            self.on_bold_starts_toggled(self._bold_starts)

    def _refresh_bold_starts(self) -> None:
        """Match the button's icon and the text to the current state."""
        image = self._bold_on_image if self._bold_starts else self._bold_off_image
        self.bold_starts_button.configure(image=image)
        self._apply_bold_starts()

    def _inner_text(self):
        """The tkinter Text inside the edit box, or None while it is not built
        yet. The bold tag lives there because CustomTkinter's own tag_config
        refuses a font (it could not keep it in step with the scaling)."""
        return getattr(getattr(self, "textbox", None), "_textbox", None)

    def _apply_bold_starts(self) -> None:
        """Bold the start of every word in the whole text, or clear the bold when
        the look is off. Replaces whatever the tag covered before."""
        inner = self._inner_text()
        if inner is None:
            return
        inner.tag_remove(BOLD_TAG, "1.0", "end")
        if not self._bold_starts:
            return
        self._sync_bold_font()
        self._bold_text(inner, inner.get("1.0", "end-1c"), 1)

    def _handle_edited_lines(self, first, last) -> None:
        """The edit box says lines first to last (from 1) were just edited, or
        None when it cannot say which. Bold those lines again. The bold of a
        line depends on nothing but that line, so every other line keeps the tag
        it has, whether the edit was a typed letter, a paste of several lines or
        a join of two lines."""
        if not self._bold_starts or self._edits_paused:
            return
        if first is None:
            self._apply_bold_starts()
            return
        inner = self._inner_text()
        if inner is None:
            return
        end = f"{last}.end"
        inner.tag_remove(BOLD_TAG, f"{first}.0", end)
        self._bold_text(inner, inner.get(f"{first}.0", end), first)

    def _bold_text(self, inner, text: str, first_line: int) -> None:
        """Bold the word starts of `text`, which is the lines of the edit box
        from first_line on. Lines over the limit are left plain, and the label
        says so, so it does not look like the button did nothing."""
        spans = tk_spans(text, _tk_astral_width(self), first_line, MAX_BOLD_LINE)
        self._add_bold_tags(inner, spans)
        if has_long_line(text, MAX_BOLD_LINE):
            self._show_feedback(LONG_LINES_NOTE)

    @staticmethod
    def _add_bold_tags(inner, spans) -> None:
        """Lay the bold tag over (line, start, end) stretches, a batch at a time."""
        for first in range(0, len(spans), _TAG_BATCH):
            places = []
            for line, start, end in spans[first:first + _TAG_BATCH]:
                places += (f"{line}.{start}", f"{line}.{end}")
            inner.tag_add(BOLD_TAG, *places)

    def _sync_bold_font(self) -> None:
        """Give the bold tag the edit box's current font, in bold. The family and
        the pixel size are read off the font the Text is using right now, so
        this is also what keeps the tag in step when the scaling changes. A tuple
        keeps the exact pixel size, where a Tk Font object would round it to
        points. See bold_family() for the OpenDyslexic case."""
        inner = self._inner_text()
        if inner is None or not inner.winfo_exists():
            return
        family, size = inner.tk.splitlist(inner.cget("font"))[:2]
        inner.tag_configure(BOLD_TAG, font=(bold_family(family), int(size), "bold"))

    def _handle_font_changed(self) -> None:
        if self._bold_starts:
            self._sync_bold_font()

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
        # Nothing to revert until something has been normalized. Checking that
        # first spares reading the whole text on every edit, which is slow in a
        # long text once the bold word starts are on (Tk puts the text together
        # from a great many pieces then).
        if self._pre_normalize_text and can_revert(self.get_text(), self._pre_normalize_text, self._normalized_text):
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
        # one action is on offer (Play, Detach, or Copy with bold while the
        # bold look is on); otherwise a right-click does nothing.
        text = self._selected_text()
        if not text or not (self.on_play_selection or self.on_detach_selection or self._bold_starts):
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
        if self._bold_starts:
            rows.append(("Copy with bold", self._dispatch_copy_with_bold))
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

    def _selection_pieces(self):
        """The selected text as (text, is_bold) pieces in reading order, as it is
        shown right now, or None when nothing is selected. Read off the screen
        with Tk's dump, which reports where the bold tag starts and stops, so what
        is copied is exactly what is seen (lines left plain stay plain) and no
        column has to be turned into a position by hand, which is where an emoji
        would go wrong. The selection may begin in the middle of a bold stretch,
        which dump does not report, so that is asked first. Called with the raw
        Tcl command: tkinter's own dump() groups the answer in Python and takes
        about twice as long on a long selection."""
        inner = self._inner_text()
        if inner is None or not inner.tag_ranges("sel"):
            return None
        start, end = str(inner.index("sel.first")), str(inner.index("sel.last"))
        bold = BOLD_TAG in inner.tag_names(start)
        pieces = []
        events = inner.tk.call(str(inner), "dump", "-tag", "-text", start, end)
        for kind, value in zip(events[0::3], events[1::3]):
            if kind == "tagon" and value == BOLD_TAG:
                bold = True
            elif kind == "tagoff" and value == BOLD_TAG:
                bold = False
            elif kind == "text" and value:
                pieces.append((value, bold))
        return pieces

    def _copy_with_bold(self) -> bool:
        """Put the selection on the clipboard as text with its bold, for Word. True
        when that worked. False when it did not (not on Windows, the clipboard was
        busy, nothing is selected), and then nothing is promised about the
        clipboard and the caller copies the plain text the ordinary way."""
        inner = self._inner_text()
        try:
            pieces = self._selection_pieces()
            if pieces is None:
                return False
            plain = inner.get("sel.first", "sel.last")
        except tk.TclError:
            return False
        # The pieces must add up to exactly the text Tk itself would copy. If they
        # ever did not, a plain copy is safer than a wrong rich one.
        if segments_text(pieces) != plain:
            return False
        return copy_rich(inner.winfo_id(), plain, cf_html(pieces))

    def _handle_copy_event(self, event):
        # Ctrl+C. With the bold look off, or when the rich copy did not work, this
        # does nothing and Tk's own plain copy carries on. Cut is left to Tk too:
        # the text is gone from the box afterwards, so there is nothing to look at.
        if self._bold_starts and self._copy_with_bold():
            return "break"
        return None

    def _dispatch_copy_with_bold(self, text: str) -> None:
        if self._copy_with_bold():
            self._show_feedback(COPIED_WITH_BOLD)
            return
        # The bold could not go along, so copy the words the ordinary way and say
        # so. The selection may have changed since the menu opened, so it is read
        # again, and the text the menu was opened with is the fallback.
        inner = self._inner_text()
        if inner is not None and inner.tag_ranges("sel"):
            text = inner.get("sel.first", "sel.last")
        self.clipboard_clear()
        self.clipboard_append(text)
        self._show_feedback(COPIED_PLAIN)