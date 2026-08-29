import customtkinter as ctk


class Spaces(ctk.CTkFrame):
    """Folders/categories for swapping between different transcript lists."""

    def __init__(self, master):
        super().__init__(master, fg_color="#8E44AD", corner_radius=0)
        ctk.CTkLabel(self, text="Spaces").pack(expand=True)