import customtkinter as ctk
from tkinter import colorchooser
from gui.theme import WARM_MOCHA, COCOA_INK, EMBER_GLOW, EMBER_GLOW_HOVER, WARM_LINE, FONT_BODY
from core.settings_store import FONT_SIZE_RANGE


class Footer(ctk.CTkFrame):
    """Control band: font colour + background colour (left, stacked),
    WPM + skip controls (middle), word size + highlight colour (right,
    stacked to mirror the left column)."""

    def __init__(
        self,
        master,
        on_wpm_changed=None,
        on_font_color_changed=None,
        on_highlight_color_changed=None,
        on_background_color_changed=None,
        on_skip_back=None,
        on_skip_forward=None,
        on_font_size_changed=None,
        font_size_step: int = 1,
    ):
        super().__init__(master, fg_color=WARM_MOCHA, corner_radius=0)
        self.on_wpm_changed = on_wpm_changed
        self.on_font_color_changed = on_font_color_changed
        self.on_highlight_color_changed = on_highlight_color_changed
        self.on_background_color_changed = on_background_color_changed
        self.on_skip_back = on_skip_back
        self.on_skip_forward = on_skip_forward
        self.on_font_size_changed = on_font_size_changed
        self._font_size = 32
        self._font_size_step = font_size_step

        label_font = ctk.CTkFont(family=FONT_BODY, size=12)
        wpm_font = ctk.CTkFont(family=FONT_BODY, size=12, weight="bold")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        # ---- Left: Font (top), Background (bottom) ----
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")

        font_row = ctk.CTkFrame(left, fg_color="transparent")
        font_row.pack(pady=6)
        ctk.CTkLabel(font_row, text="Font", text_color=COCOA_INK, font=label_font).pack(side="left", padx=(0, 8))
        self.font_swatch = ctk.CTkButton(
            font_row, text="", width=28, height=28, corner_radius=8,
            border_width=2, border_color=WARM_LINE,
            command=self._pick_font_color,
        )
        self.font_swatch.pack(side="left")

        bg_row = ctk.CTkFrame(left, fg_color="transparent")
        bg_row.pack(pady=6)
        ctk.CTkLabel(bg_row, text="Background", text_color=COCOA_INK, font=label_font).pack(side="left", padx=(0, 8))
        self.background_swatch = ctk.CTkButton(
            bg_row, text="", width=28, height=28, corner_radius=8,
            border_width=2, border_color=WARM_LINE,
            command=self._pick_background_color,
        )
        self.background_swatch.pack(side="left")

        # ---- Middle: WPM (bold) + skip/slider row ----
        middle = ctk.CTkFrame(self, fg_color="transparent")
        middle.grid(row=0, column=1, sticky="nsew")
        self.wpm_label = ctk.CTkLabel(middle, text="300 WPM", text_color=COCOA_INK, font=wpm_font)
        self.wpm_label.pack(pady=(10, 0))

        slider_row = ctk.CTkFrame(middle, fg_color="transparent")
        slider_row.pack(padx=15, pady=(4, 0), fill="x")

        self.skip_back_button = ctk.CTkButton(
            slider_row, text="<<", width=36, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            command=self._handle_skip_back,
        )
        self.skip_back_button.pack(side="left", padx=(0, 8))

        self.wpm_slider = ctk.CTkSlider(
            slider_row, from_=100, to=1000, number_of_steps=90,
            progress_color=EMBER_GLOW, button_color=EMBER_GLOW, button_hover_color=EMBER_GLOW_HOVER,
            fg_color=WARM_LINE,
            command=self._handle_wpm_slide,
        )
        self.wpm_slider.set(300)
        self.wpm_slider.pack(side="left", fill="x", expand=True)

        self.skip_forward_button = ctk.CTkButton(
            slider_row, text=">>", width=36, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            command=self._handle_skip_forward,
        )
        self.skip_forward_button.pack(side="left", padx=(8, 0))

        # ---- Right: Word size (top), Highlight (bottom), mirroring the left ----
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew")

        size_row = ctk.CTkFrame(right, fg_color="transparent")
        size_row.pack(pady=6)
        self.size_decrease_button = ctk.CTkButton(
            size_row, text="-", width=24, height=24, corner_radius=8,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            command=self._handle_size_decrease,
        )
        self.size_decrease_button.pack(side="left", padx=(0, 6))
        self.size_label = ctk.CTkLabel(size_row, text="32px", text_color=COCOA_INK, font=label_font, width=40)
        self.size_label.pack(side="left")
        self.size_increase_button = ctk.CTkButton(
            size_row, text="+", width=24, height=24, corner_radius=8,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            command=self._handle_size_increase,
        )
        self.size_increase_button.pack(side="left", padx=(6, 0))

        highlight_row = ctk.CTkFrame(right, fg_color="transparent")
        highlight_row.pack(pady=6)
        ctk.CTkLabel(highlight_row, text="Highlight", text_color=COCOA_INK, font=label_font).pack(side="left", padx=(0, 8))
        self.highlight_swatch = ctk.CTkButton(
            highlight_row, text="", width=28, height=28, corner_radius=8,
            border_width=2, border_color=WARM_LINE,
            command=self._pick_highlight_color,
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
        self._font_size = transcript.font_size
        self.size_label.configure(text=f"{self._font_size}px")

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.wpm_slider.configure(state=state)
        self.font_swatch.configure(state=state)
        self.background_swatch.configure(state=state)
        self.highlight_swatch.configure(state=state)
        self.skip_back_button.configure(state=state)
        self.skip_forward_button.configure(state=state)
        self.size_decrease_button.configure(state=state)
        self.size_increase_button.configure(state=state)

    def set_font_size(self, size: int) -> None:
        """Update just the displayed size, for when the change comes
        from an external source (Settings Apply), as opposed to the
        user directly clicking +/- here."""
        self._font_size = size
        self.size_label.configure(text=f"{size}px")

    def set_font_size_step(self, step: int) -> None:
        self._font_size_step = step

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

    def _handle_size_decrease(self) -> None:
        self._change_font_size(-self._font_size_step)

    def _handle_size_increase(self) -> None:
        self._change_font_size(self._font_size_step)

    def _change_font_size(self, delta: int) -> None:
        low, high = FONT_SIZE_RANGE
        self._font_size = max(low, min(high, self._font_size + delta))
        self.size_label.configure(text=f"{self._font_size}px")
        if self.on_font_size_changed:
            self.on_font_size_changed(self._font_size)

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