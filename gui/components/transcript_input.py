import textwrap

import customtkinter as ctk


class TranscriptInput(ctk.CTkFrame):
    """Paste-in prompt shown when the selected transcript has no text yet."""

    # CTkTextbox's own word-wrap layout becomes extremely slow -- to the
    # point of a full, multi-minute freeze, not just gradual lag -- once
    # a single logical line (the text between real newlines) runs into
    # the hundreds of thousands of characters. Confirmed this is specific
    # to CTkTextbox, not Tkinter's underlying Text widget, which doesn't
    # have the problem with identical content:
    # https://github.com/TomSchimansky/CustomTkinter/issues/1020
    #
    # A normal typed or pasted transcript never comes near this --
    # paragraph breaks keep every line short. What DOES reliably trigger
    # it: a file import. core/importers.py runs every imported file
    # through clean_transcript() (core/parser.py), which deliberately
    # collapses ALL whitespace -- including the original newlines -- into
    # single spaces. That's exactly right for reading (RSVP flashes one
    # word at a time regardless of original line breaks), but it also
    # means an imported file's draft text arrives here as ONE unbroken
    # line, which can easily run past 400,000 characters for a large
    # document -- confirmed as the actual cause of a real crash on a
    # 73,677-word PDF import.
    #
    # See _wrap_for_display() below for how this is guarded against.
    _MAX_DISPLAY_LINE_CHARS = 2000

    def __init__(self, master, on_submit, initial_text: str = ""):
        super().__init__(master, fg_color="transparent")
        self.on_submit = on_submit

        self.textbox = ctk.CTkTextbox(self, width=500, height=250)
        self.textbox.pack(padx=20, pady=20, fill="both", expand=True)
        if initial_text:
            self.textbox.insert("1.0", self._wrap_for_display(initial_text))

        self.start_button = ctk.CTkButton(self, text="Start reading", command=self._handle_submit)
        self.start_button.pack(pady=(0, 20))

    def get_text(self) -> str:
        """Return whatever's currently typed, submitted or not."""
        return self.textbox.get("1.0", "end")

    def set_text(self, text: str) -> None:
        """Replace the textbox's contents."""
        self.textbox.delete("1.0", "end")
        if text:
            self.textbox.insert("1.0", self._wrap_for_display(text))

    @classmethod
    def _wrap_for_display(cls, text: str) -> str:
        """Break up any pathologically long line before it reaches
        CTkTextbox -- see the class comment above for why. Text that's
        already broken into reasonably-sized lines (which covers every
        normal paste or typed entry) is returned completely unchanged --
        this can never alter how a normal transcript looks when it's
        redisplayed for editing. It only steps in for the one
        pathological case this class comment describes.

        Wrapped per EXISTING line, not across the whole text at once --
        so if a future caller ever legitimately mixes short paragraph
        lines with one huge one, only the huge one gets reflowed and
        every other line keeps its original break exactly where it was.

        These inserted breaks are purely cosmetic, for CTkTextbox's
        sake. Whatever eventually gets submitted (get_text(), on "Start
        reading") still passes through clean_transcript() before being
        read, which collapses all whitespace -- including these
        display-only breaks -- straight back into single spaces, so
        nothing about how the transcript actually reads is affected."""
        lines = text.split("\n")
        if all(len(line) <= cls._MAX_DISPLAY_LINE_CHARS for line in lines):
            return text
        return "\n".join(
            textwrap.fill(line, width=100) if len(line) > cls._MAX_DISPLAY_LINE_CHARS else line
            for line in lines
        )

    def _handle_submit(self) -> None:
        self.on_submit(self.get_text())
