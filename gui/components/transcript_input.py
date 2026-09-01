import customtkinter as ctk


class TranscriptInput(ctk.CTkFrame):
    """Paste-in prompt shown when the selected transcript has no text yet."""

    def __init__(self, master, on_submit):
        super().__init__(master, fg_color="transparent")
        self.on_submit = on_submit

        self.textbox = ctk.CTkTextbox(self, width=500, height=250)
        self.textbox.pack(padx=20, pady=20, fill="both", expand=True)

        self.start_button = ctk.CTkButton(self, text="Start reading", command=self._handle_submit)
        self.start_button.pack(pady=(0, 20))

    def _handle_submit(self) -> None:
        raw_text = self.textbox.get("1.0", "end")
        self.on_submit(raw_text)