import customtkinter as ctk
from gui.app import RSVPApp
from gui.theme import register_fonts

if __name__ == "__main__":
    register_fonts()
    ctk.set_appearance_mode("Light")
    app = RSVPApp()
    app.mainloop()