import customtkinter as ctk


class Header(ctk.CTkFrame):
    """Slim top row: active transcript name (left) and a settings button (right)."""

    def __init__(self, master, on_settings=None):
        super().__init__(master, fg_color="#16A085", corner_radius=0)
        self.on_settings = on_settings

        self.title_label = ctk.CTkLabel(self, text="No transcript selected")
        self.title_label.pack(side="left", padx=15)

        ctk.CTkButton(self, text="Settings", width=80, command=self._handle_settings).pack(side="right", padx=15)

    def set_title(self, title: str) -> None:
        self.title_label.configure(text=title)

    def _handle_settings(self) -> None:
        if self.on_settings:
            self.on_settings()