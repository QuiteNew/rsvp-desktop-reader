import customtkinter as ctk


class DeleteTranscriptDialog(ctk.CTkToplevel):
    """Confirmation popup before permanently deleting a transcript."""

    def __init__(self, master, on_confirm):
        super().__init__(master)
        self.title("Transcript deletion")
        self.geometry("360x160")
        self.resizable(False, False)
        self.on_confirm = on_confirm

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        ctk.CTkLabel(
            self, text="Are you sure you want to permanently delete the transcript?",
            wraplength=320, justify="left",
        ).pack(padx=20, pady=(25, 20))

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(button_row, text="Cancel", command=self.destroy).pack(side="left")
        ctk.CTkButton(
            button_row, text="Delete", fg_color="#A33636", hover_color="#7E2929",
            command=self._handle_delete,
        ).pack(side="right")

    def _handle_delete(self) -> None:
        self.on_confirm()
        self.destroy()