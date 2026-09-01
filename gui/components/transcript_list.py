import customtkinter as ctk


class TranscriptList(ctk.CTkFrame):
    """List of saved transcripts, with a '+' button to add a new one."""

    def __init__(self, master, on_add=None, on_select=None):
        super().__init__(master, fg_color="#2C3E50", corner_radius=0)
        self.on_add = on_add
        self.on_select = on_select

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="List of Transcripts").pack(side="left")
        ctk.CTkButton(header, text="+", width=28, command=self._handle_add).pack(side="right")

        self.entries_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.entries_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

    def add_entry(self, transcript) -> None:
        row = ctk.CTkLabel(
            self.entries_frame,
            text=transcript.title,
            anchor="w",
            fg_color="#34495E",
            corner_radius=4,
            cursor="hand2",
        )
        row.pack(fill="x", pady=2, padx=2, ipady=6)
        row.bind("<Button-1>", lambda event, t=transcript: self._handle_select(t))

    def clear(self) -> None:
        for widget in self.entries_frame.winfo_children():
            widget.destroy()

    def render_transcripts(self, transcripts) -> None:
        self.clear()
        for t in transcripts:
            self.add_entry(t)

    def _handle_add(self) -> None:
        if self.on_add:
            self.on_add()

    def _handle_select(self, transcript) -> None:
        if self.on_select:
            self.on_select(transcript)