import customtkinter as ctk
from gui.app import RSVPApp
from gui.theme import register_fonts, set_dpi_awareness, CTK_APPEARANCE_MODE

if __name__ == "__main__":
    # Must run before anything else -- including register_fonts() and the
    # first window's creation -- see set_dpi_awareness()'s docstring.
    set_dpi_awareness()
    register_fonts()
    ctk.set_appearance_mode(CTK_APPEARANCE_MODE)
    app = RSVPApp()
    app.mainloop()