import customtkinter as ctk


class Footer(ctk.CTkFrame):
    """Control band: font/background colour (left), WPM (middle), highlight colour (right)."""

    def __init__(self, master):
        super().__init__(master, fg_color="#E67E22", corner_radius=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(left, text="Font colour\nBackground colour", justify="center").pack(expand=True)

        middle = ctk.CTkFrame(self, fg_color="transparent")
        middle.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(middle, text="WPM / speed").pack(expand=True)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew")
        ctk.CTkLabel(right, text="Highlighted letter colour").pack(expand=True)