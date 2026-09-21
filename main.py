import customtkinter as ctk
from gui.app import RSVPApp
from gui.theme import register_fonts, set_dpi_awareness, apply_linux_dpi_scaling, CTK_APPEARANCE_MODE

if __name__ == "__main__":
    # Must run before anything else -- including register_fonts() and the
    # first window's creation -- see set_dpi_awareness()'s and
    # apply_linux_dpi_scaling()'s docstrings.
    set_dpi_awareness()
    apply_linux_dpi_scaling()
    register_fonts()
    ctk.set_appearance_mode(CTK_APPEARANCE_MODE)
    app = RSVPApp()
    app.mainloop()