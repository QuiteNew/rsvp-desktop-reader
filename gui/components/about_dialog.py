import os
import webbrowser

import customtkinter as ctk
from PIL import Image

from core.app_info import APP_NAME, APP_VERSION, LICENSE_NAME, REPO_URL
from core.colors import blend_colors
from gui.components.dialog_keys import bind_dialog_keys
from gui.theme import (
    HEARTH_PAPER, COCOA_INK, DUSK_BLUE, EMBER_GLOW, EMBER_GLOW_HOVER,
    FONT_HEADING, FONT_BODY, apply_app_icon, center_over_parent,
)
# The same file apply_app_icon() uses for the window icon. It is a private name
# in gui/theme.py, but repeating the path logic here would mean two places to
# fix if the assets folder ever moves, so this borrows it on purpose.
from gui.theme import _ICON_PNG as APP_ICON_PNG


class AboutDialog(ctk.CTkToplevel):
    """The small "About" popup behind the info button in the Settings window:
    the app icon on the left, and on the right its name, version, licence and
    a link to the GitHub project. What it says comes from core/app_info.py, so
    there is one place to update at release time.

    Every colour here comes from the theme tokens in gui/theme.py (or is
    blended from them), so the dialog follows the light or dark theme the app
    started with, the same as the other popups. Two colours are not plain
    tokens: the quieter grey for the version and licence lines, and the link
    blue. Both are blended from the theme's own colours instead of being
    hard-coded, because a fixed grey or blue that reads well on the light
    paper looks wrong on the dark one, and the raw DUSK_BLUE is a bit too
    faint for small text on the light theme.

    on_close, if given, is called once after the dialog goes away, whether it
    was closed by the button or by the window's own close control (both go
    through the same handler, as in MessageDialog). The Settings window needs
    it: it holds the input grab, and destroying a popup opened from it does
    not hand the grab back, so it uses this to take it again."""

    ICON_SIZE = 96

    def __init__(self, master, on_close=None):
        super().__init__(master)

        # See gui/components/delete_transcript_dialog.py for the fuller
        # explanation of why this uses -alpha rather than
        # withdraw()/deiconify() to stay hidden until fully built.
        self.attributes("-alpha", 0)

        self.title("About")
        apply_app_icon(self)
        center_over_parent(self, 460, 230)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)
        self.on_close = on_close

        # The window's own close control goes through the same handler as the
        # button, so on_close fires either way.
        self.protocol("WM_DELETE_WINDOW", self._handle_dismiss)

        heading_font = ctk.CTkFont(family=FONT_HEADING, size=22)
        body_font = ctk.CTkFont(family=FONT_BODY, size=13)
        link_font = ctk.CTkFont(family=FONT_BODY, size=13, underline=True)
        button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        # Both blends clear a 4.5:1 contrast ratio against the paper colour in
        # the light and the dark theme.
        self._muted_color = blend_colors(COCOA_INK, HEARTH_PAPER, 0.30)
        self._link_color = blend_colors(DUSK_BLUE, COCOA_INK, 0.25)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=(25, 10))

        # Kept on the dialog so the image is not collected while it is shown.
        self._icon_image = self._load_icon()
        if self._icon_image is not None:
            ctk.CTkLabel(content, text="", image=self._icon_image).pack(
                side="left", anchor="n", padx=(0, 20),
            )

        details = ctk.CTkFrame(content, fg_color="transparent")
        details.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            details, text=APP_NAME, text_color=COCOA_INK, font=heading_font, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            details, text=f"Version {APP_VERSION}", text_color=self._muted_color,
            font=body_font, anchor="w",
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            details, text=f"Released under the {LICENSE_NAME} License",
            text_color=self._muted_color, font=body_font, anchor="w",
        ).pack(anchor="w", pady=(14, 0))

        # A label rather than a button so it is only as wide as the text and
        # only the text is clickable. It shows the address without the
        # "https://", which is just noise in a dialog.
        self._link = ctk.CTkLabel(
            details, text=REPO_URL.removeprefix("https://"), text_color=self._link_color,
            font=link_font, anchor="w", cursor="hand2",
        )
        self._link.pack(anchor="w", pady=(4, 0))
        self._link.bind("<Button-1>", self._open_repo)
        self._link.bind("<Enter>", lambda _event: self._link.configure(text_color=COCOA_INK))
        self._link.bind("<Leave>", lambda _event: self._link.configure(text_color=self._link_color))

        ctk.CTkButton(
            self, text="Close", width=90, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=button_font, command=self._handle_dismiss,
        ).pack(pady=(0, 20))

        # Esc does what Close does, on_close included, so Settings still gets
        # its input grab back.
        bind_dialog_keys(self, on_escape=self._handle_dismiss)

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()

        # See delete_transcript_dialog.py's matching comment: same
        # reasoning, same delay.
        self.after(80, self._reveal_now)

    def _load_icon(self):
        """The app icon as a CTkImage, or None if the file is missing or
        unreadable. Same defensive stance as apply_app_icon(): a missing
        picture should never stop the dialog from opening, so the text just
        shows without it. The source PNG is larger than the on-screen size and
        only ever scaled down, which keeps it sharp on high-DPI displays."""
        if not os.path.exists(APP_ICON_PNG):
            return None
        try:
            image = Image.open(APP_ICON_PNG).convert("RGBA")
        except OSError:
            return None
        return ctk.CTkImage(
            light_image=image, dark_image=image, size=(self.ICON_SIZE, self.ICON_SIZE),
        )

    def _open_repo(self, _event=None) -> None:
        """Opens the project page in the user's own browser. The only thing in
        the app that reaches outside it, and only when this link is clicked."""
        webbrowser.open(REPO_URL)

    def _reveal_now(self) -> None:
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def _handle_dismiss(self) -> None:
        self.destroy()
        if self.on_close:
            self.on_close()