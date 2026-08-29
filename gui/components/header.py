import customtkinter as ctk


class Header(ctk.CTkFrame):
    """Slim top row: active transcript name (left) and a settings icon placeholder (right)."""

    def __init__(self, master):
        super().__init__(master, fg_color="#16A085", corner_radius=0)
        ctk.CTkLabel(self, text="Transcript name").pack(side="left", padx=15)
        ctk.CTkLabel(self, text="[settings]").pack(side="right", padx=15)