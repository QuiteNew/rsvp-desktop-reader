import sys

import customtkinter as ctk
from core.self_check import parse_self_check_args
from gui.app import RSVPApp
from gui.self_check import run_self_check
from gui.theme import register_fonts, set_dpi_awareness, apply_linux_dpi_scaling, CTK_APPEARANCE_MODE

if __name__ == "__main__":
    # Must run before anything else, including register_fonts() and the
    # first window's creation; see set_dpi_awareness()'s and
    # apply_linux_dpi_scaling()'s docstrings.
    set_dpi_awareness()
    apply_linux_dpi_scaling()
    register_fonts()
    ctk.set_appearance_mode(CTK_APPEARANCE_MODE)
    # The release build starts the packaged app with --self-check to see that
    # it really works, then quits. It follows the same start-up as above, so
    # that is part of what gets checked. See core/self_check.py.
    self_check = parse_self_check_args(sys.argv[1:])
    if self_check is not None:
        sys.exit(run_self_check(self_check.report_path))
    app = RSVPApp()
    app.mainloop()