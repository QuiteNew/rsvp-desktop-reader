import customtkinter as ctk
from tkinter import colorchooser


class Footer(ctk.CTkFrame):
    """Control band: font/background colour (left), WPM + skip controls (middle), highlight colour (right)."""

    def __init__(
        self,
        master,
        on_wpm_changed=None,
        on_font_color_changed=None,
        on_highlight_color_changed=None,
        on_background_color_changed=None,
        on_skip_back=None,
        on_skip_forward=None,
    ):
        super().__init__(master, fg_color="#E67E22", corner_radius=0)
        self.on_wpm_changed = on_wpm_changed
        self.on_font_color_changed = on_font_color_changed
        self.on_highlight_color_changed = on_highlight_color_changed
        self.on_background_color_changed = on_background_color_changed
        self.on_skip_back = on_skip_back
        self.on_skip_forward = on_skip_forward

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")

        font_row = ctk.CTkFrame(left, fg_color="transparent")
        font_row.pack(pady=6)
        ctk.CTkLabel(font_row, text="Font").pack(side="left", padx=(0, 8))
        self.font_swatch = ctk.CTkButton(
            font_row, text="", width=28, height=28, corner_radius=6, command=self._pick_font_color
        )
        self.font_swatch.pack(side="left")

        bg_row = ctk.CTkFrame(left, fg_color="transparent")
        bg_row.pack(pady=6)
        ctk.CTkLabel(bg_row, text="Background").pack(side="left", padx=(0, 8))
        self.background_swatch = ctk.CTkButton(
            bg_row, text="", width=28, height=28, corner_radius=6, command=self._pick_background_color
        )
        self.background_swatch.pack(side="left")

        middle = ctk.CTkFrame(self, fg_color="transparent")
        middle.grid(row=0, column=1, sticky="nsew")
        self.wpm_label = ctk.CTkLabel(middle, text="300 WPM")
        self.wpm_label.pack(pady=(10, 0))

        slider_row = ctk.CTkFrame(middle, fg_color="transparent")
        slider_row.pack(padx=15, pady=(4, 0), fill="x")

        self.skip_back_button = ctk.CTkButton(
            slider_row, text="<<", width=36, command=self._handle_skip_back
        )
        self.skip_back_button.pack(side="left", padx=(0, 8))

        self.wpm_slider = ctk.CTkSlider(
            slider_row, from_=100, to=1000, number_of_steps=90, command=self._handle_wpm_slide
        )
        self.wpm_slider.set(300)
        self.wpm_slider.pack(side="left", fill="x", expand=True)

        self.skip_forward_button = ctk.CTkButton(
            slider_row, text=">>", width=36, command=self._handle_skip_forward
        )
        self.skip_forward_button.pack(side="left", padx=(8, 0))

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew")
        highlight_row = ctk.CTkFrame(right, fg_color="transparent")
        highlight_row.pack(expand=True)
        ctk.CTkLabel(highlight_row, text="Highlight").pack(side="left", padx=(0, 8))
        self.highlight_swatch = ctk.CTkButton(
            highlight_row, text="", width=28, height=28, corner_radius=6, command=self._pick_highlight_color
        )
        self.highlight_swatch.pack(side="left")

        self.set_enabled(False)

    def load_transcript(self, transcript) -> None:
        self.set_enabled(True)
        self.wpm_slider.set(transcript.wpm)
        self.wpm_label.configure(text=f"{transcript.wpm} WPM")
        self.font_swatch.configure(fg_color=transcript.font_color)
        self.background_swatch.configure(fg_color=transcript.background_color)
        self.highlight_swatch.configure(fg_color=transcript.highlight_color)

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.wpm_slider.configure(state=state)
        self.font_swatch.configure(state=state)
        self.background_swatch.configure(state=state)
        self.highlight_swatch.configure(state=state)
        self.skip_back_button.configure(state=state)
        self.skip_forward_button.configure(state=state)

    def _handle_wpm_slide(self, value) -> None:
        wpm = int(value)
        self.wpm_label.configure(text=f"{wpm} WPM")
        if self.on_wpm_changed:
            self.on_wpm_changed(wpm)

    def _handle_skip_back(self) -> None:
        if self.on_skip_back:
            self.on_skip_back()

    def _handle_skip_forward(self) -> None:
        if self.on_skip_forward:
            self.on_skip_forward()

    def _pick_font_color(self) -> None:
        color = colorchooser.askcolor(color=self.font_swatch.cget("fg_color"))[1]
        if color:
            self.font_swatch.configure(fg_color=color)
            if self.on_font_color_changed:
                self.on_font_color_changed(color)

    def _pick_background_color(self) -> None:
        color = colorchooser.askcolor(color=self.background_swatch.cget("fg_color"))[1]
        if color:
            self.background_swatch.configure(fg_color=color)
            if self.on_background_color_changed:
                self.on_background_color_changed(color)

    def _pick_highlight_color(self) -> None:
        color = colorchooser.askcolor(color=self.highlight_swatch.cget("fg_color"))[1]
        if color:
            self.highlight_swatch.configure(fg_color=color)
            if self.on_highlight_color_changed:
                self.on_highlight_color_changed(color)