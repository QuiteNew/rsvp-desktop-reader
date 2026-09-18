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

        title_font = ctk.CTkFont(family=FONT_BODY, size=13)
        title_label = ctk.CTkLabel(
            row, text=transcript.title, anchor="w",
            text_color=COCOA_INK, font=title_font, cursor="hand2",
        )
        title_label.pack(side="left", fill="x", expand=True, padx=(12, 4), pady=8)

        # WARM_TAUPE (muted, near-blended into the row at rest) and WARM_LINE
        # (clearly visible on hover) — both real theme tokens now, so this
        # correctly adapts to dark mode instead of the old fixed hex values.
        delete_button = ctk.CTkButton(
            row, text="X", width=20, height=20, corner_radius=8,
            fg_color="transparent", hover_color=WARM_LINE,
            text_color=WARM_TAUPE, cursor="hand2",
            command=lambda t=transcript: self._handle_delete_requested(t),
        )
        delete_button.pack(side="right", padx=(0, 10))

        def reveal(event=None):
            delete_button.configure(text_color=WARM_LINE)

        def unreveal(event=None):
            delete_button.configure(text_color=WARM_TAUPE)

        for widget in (row, title_label, delete_button):
            widget.bind("<Enter>", reveal)
            widget.bind("<Leave>", unreveal)

        title_label.bind("<Button-1>", lambda event, t=transcript: self._handle_select(t))

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