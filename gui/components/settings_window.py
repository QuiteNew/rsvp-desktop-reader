import customtkinter as ctk


class SettingsWindow(ctk.CTkToplevel):
    """Popup for app-level settings — currently just window size."""

    MIN_WIDTH, MAX_WIDTH = 500, 2000
    MIN_HEIGHT, MAX_HEIGHT = 400, 1400

    def __init__(self, master, current_width: int, current_height: int, on_apply):
        super().__init__(master)
        self.title("Settings")
        self.geometry("320x230")
        self.resizable(False, False)
        self.on_apply = on_apply

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        ctk.CTkLabel(self, text="Window size", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))

        width_row = ctk.CTkFrame(self, fg_color="transparent")
        width_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(width_row, text="Width", width=60, anchor="w").pack(side="left")
        self.width_entry = ctk.CTkEntry(width_row)
        self.width_entry.insert(0, str(current_width))
        self.width_entry.pack(side="left", fill="x", expand=True)

        height_row = ctk.CTkFrame(self, fg_color="transparent")
        height_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(height_row, text="Height", width=60, anchor="w").pack(side="left")
        self.height_entry = ctk.CTkEntry(height_row)
        self.height_entry.insert(0, str(current_height))
        self.height_entry.pack(side="left", fill="x", expand=True)

        self.error_label = ctk.CTkLabel(self, text="", text_color="#E74C3C")
        self.error_label.pack(padx=20, pady=(8, 0), anchor="w")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(button_row, text="Close", command=self.destroy).pack(side="left")
        ctk.CTkButton(button_row, text="Apply", command=self._handle_apply).pack(side="right")

    def _handle_apply(self) -> None:
        width_text = self.width_entry.get().strip()
        height_text = self.height_entry.get().strip()

        if not width_text.isdigit() or not height_text.isdigit():
            self.error_label.configure(text="Width and height must be whole numbers.")
            return

        width, height = int(width_text), int(height_text)

        if not (self.MIN_WIDTH <= width <= self.MAX_WIDTH):
            self.error_label.configure(text=f"Width must be between {self.MIN_WIDTH} and {self.MAX_WIDTH}.")
            return
        if not (self.MIN_HEIGHT <= height <= self.MAX_HEIGHT):
            self.error_label.configure(text=f"Height must be between {self.MIN_HEIGHT} and {self.MAX_HEIGHT}.")
            return

        self.error_label.configure(text="")
        self.on_apply(width, height)