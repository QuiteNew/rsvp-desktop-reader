import customtkinter as ctk

from core.normalizer import can_revert, toggle_normalization
from gui.icons import normalize_icon, revert_icon


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
    toggle, passed in and kept current through set_split_long_paragraphs()."""

    FEEDBACK_MS = 2000

    def __init__(self, master, on_submit, initial_text: str = "", on_normalized=None, split_long_paragraphs: bool = False):
        super().__init__(master, fg_color="transparent")
        self.on_submit = on_submit
        self.on_normalized = on_normalized
        self._pre_normalize_text = ""
        self._normalized_text = ""
        self._feedback_after_id = None
        self._split_long_paragraphs = split_long_paragraphs

        self.textbox = ctk.CTkTextbox(self, width=500, height=250)
        self.textbox.pack(padx=20, pady=20, fill="both", expand=True)
        if initial_text:
            self.textbox.insert("1.0", initial_text)

        # Tk raises <<Modified>> for typing, deleting, pasting and for
        # changes made in code, so it keeps the button's icon in step
        # with the text whatever changed it.
        self.textbox.bind("<<Modified>>", self._handle_text_modified)

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