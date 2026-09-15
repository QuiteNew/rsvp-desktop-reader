import customtkinter as ctk
from gui.app import RSVPApp
from gui.theme import register_fonts, CTK_APPEARANCE_MODE

if __name__ == "__main__":
    register_fonts()
    ctk.set_appearance_mode(CTK_APPEARANCE_MODE)
    app = RSVPApp()
    app.mainloop()