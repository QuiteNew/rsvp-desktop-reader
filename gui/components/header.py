import customtkinter as ctk


class Header(ctk.CTkFrame):
    """Slim top row: active transcript name (left) and a settings icon placeholder (right)."""

    def __init__(self, master):
        super().__init__(master, fg_color="#16A085", corner_radius=0)
        self.title_label = ctk.CTkLabel(self, text="No transcript selected")
        self.title_label.pack(side="left", padx=15)
        ctk.CTkLabel(self, text="[settings]").pack(side="right", padx=15)

    def set_title(self, title: str) -> None:
        self.title_label.configure(text=title)