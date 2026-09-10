import customtkinter as ctk


class TranscriptListBody(ctk.CTkFrame):
    """Scrollable list of saved transcripts. Each row has a delete
    button that only becomes clearly visible when hovering that row."""

    DELETE_MUTED = "#47566B"     # close to the row's own background — present but subtle at rest
    DELETE_REVEALED = "#AEB6BF"  # a plain, clearly visible gray on hover — never blue

    def __init__(self, master, on_select=None, on_delete_requested=None):
        super().__init__(master, fg_color="#2C3E50", corner_radius=0)
        self.on_select = on_select
        self.on_delete_requested = on_delete_requested

        self.entries_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.entries_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def add_entry(self, transcript) -> None:
        row = ctk.CTkFrame(self.entries_frame, fg_color="#34495E", corner_radius=4)
        row.pack(fill="x", pady=2, padx=2)

        title_label = ctk.CTkLabel(row, text=transcript.title, anchor="w", cursor="hand2")
        title_label.pack(side="left", fill="x", expand=True, padx=(10, 4), pady=6)

        delete_button = ctk.CTkButton(
            row, text="X", width=20, height=20, corner_radius=6,
            fg_color="transparent", hover_color="#34495E",
            text_color=self.DELETE_MUTED, cursor="hand2",
            command=lambda t=transcript: self._handle_delete_requested(t),
        )
        delete_button.pack(side="right", padx=(0, 8))

        def reveal(event=None):
            delete_button.configure(text_color=self.DELETE_REVEALED)

        def unreveal(event=None):
            delete_button.configure(text_color=self.DELETE_MUTED)

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