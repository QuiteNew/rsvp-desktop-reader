import gui.theme as theme
theme.set_dpi_awareness()

import tkinter as tk
import customtkinter as ctk

root = ctk.CTk()
root.geometry("900x600+300+150")   # windowed and offset, like your app

box = ctk.CTkTextbox(root)
box.pack(fill="both", expand=True, padx=40, pady=40)
box.insert("1.0", "Right-click in different spots to test popup positioning. " * 60)

def on_right_click(event):
    top = tk.Toplevel(root)
    top.overrideredirect(True)
    top.configure(bg="#D98A3D")
    tk.Label(top, text=" HERE ", bg="#D98A3D", fg="white").pack(padx=2, pady=2)
    top.geometry(f"+{event.x_root}+{event.y_root}")   # place by geometry, raw coords
    top.update_idletasks()
    print(f"clicked=({event.x_root},{event.y_root})  box_landed=({top.winfo_rootx()},{top.winfo_rooty()})")
    top.after(2000, top.destroy)

box._textbox.bind("<Button-3>", on_right_click)
root.mainloop()