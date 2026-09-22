import tkinter.font as tkfont

import customtkinter as ctk
from gui.theme import WARM_TAUPE, HEARTH_PAPER, COCOA_INK, WARM_LINE, FONT_BODY


class TranscriptListBody(ctk.CTkFrame):
    """Scrollable list of saved transcripts. Each row has a delete
    button that only becomes clearly visible when hovering that row."""

    def __init__(self, master, on_select=None, on_delete_requested=None):
        super().__init__(master, fg_color=WARM_TAUPE, corner_radius=0)
        self.on_select = on_select
        self.on_delete_requested = on_delete_requested

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

        def reveal(event=None):
            delete_button.configure(text_color=WARM_LINE)

        def unreveal(event=None):
            delete_button.configure(text_color=WARM_TAUPE)

        for widget in (row, title_label, delete_button):
            widget.bind("<Enter>", reveal)
            widget.bind("<Leave>", unreveal)

        title_label.bind("<Button-1>", lambda event, t=transcript: self._handle_select(t))

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