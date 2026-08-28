import customtkinter as ctk


class InputView(ctk.CTkFrame):
    """View for pasting a transcript and starting a reading session."""

    def __init__(self, master, on_start):
        super().__init__(master)
        self.on_start = on_start

        self.textbox = ctk.CTkTextbox(self, width=500, height=300)
        self.textbox.pack(padx=20, pady=20, fill="both", expand=True)

        self.start_button = ctk.CTkButton(self, text="Start reading", command=self._handle_start)
        self.start_button.pack(pady=(0, 20))

    def _handle_start(self):
        raw_text = self.textbox.get("1.0", "end")
        self.on_start(raw_text)