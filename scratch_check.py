import tkinter as tk
import tkinter.font as tkfont
from gui.theme import register_fonts

register_fonts()
root = tk.Tk()
matches = [f for f in tkfont.families() if "fredoka" in f.lower() or "quicksand" in f.lower()]
print("Matching font families found:", matches)
root.destroy()