import customtkinter as ctk

from core.reader import CHUNK_MODE_FIXED, CHUNK_MODE_ADAPTIVE
from core.settings_store import CHUNK_SIZE_RANGE, CHUNK_CHAR_TARGET_RANGE
from gui.components.dialog_keys import bind_dialog_keys
from gui.theme import (
    HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER,
    FONT_BODY, apply_app_icon, center_over_parent,
)

# The two things a change here can land on, shown on the selector at the top
# of the window and passed back to the caller as "current" / "defaults".
TARGET_CURRENT = "This transcript"
TARGET_DEFAULTS = "New transcripts"


class ChunkingSettingsWindow(ctk.CTkToplevel):
    """Every chunking setting in one place: whether words are grouped, whether
    the group size is a fixed number of words or an adaptive character width,
    and the size for each.

    The selector at the top chooses what a change lands on, the transcript
    open right now or the defaults new transcripts start from. The controls
    load from whichever is selected and Apply writes back to it, so the same
    window serves both. When nothing is open, only the defaults can be set."""

    def __init__(
        self, master,
        default_enabled, default_size, default_mode, default_char_target,
        transcript,
        on_apply,
    ):
        super().__init__(master)

        # Hidden until the whole window is built and painted, then revealed in
        # one step, so it never flashes half-drawn (the same approach the
        # other windows in this app use).
        self.attributes("-alpha", 0)

        self.on_apply = on_apply
        self._has_transcript = transcript is not None

        # The starting values behind each target, so flipping the selector can
        # reload the controls from the one chosen. The current-transcript entry
        # only exists when a transcript is open.
        self._values = {
            TARGET_DEFAULTS: {
                "enabled": default_enabled, "size": default_size,
                "mode": default_mode, "char_target": default_char_target,
            },
        }
        if transcript is not None:
            self._values[TARGET_CURRENT] = {
                "enabled": transcript.chunking_enabled, "size": transcript.chunk_size,
                "mode": transcript.chunk_mode, "char_target": transcript.chunk_char_target,
            }

        self.title("Chunking")
        apply_app_icon(self)
        center_over_parent(self, 470, 690)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)

        self.label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self.small_font = ctk.CTkFont(family=FONT_BODY, size=11)
        self.button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(16, 0))

        # ---- Apply-to selector ----
        ctk.CTkLabel(
            body, text="Apply to", text_color=COCOA_INK, font=self.label_font,
        ).pack(anchor="w")
        selector_values = [TARGET_CURRENT, TARGET_DEFAULTS] if self._has_transcript else [TARGET_DEFAULTS]
        self.target_selector = ctk.CTkSegmentedButton(
            body, values=selector_values,
            fg_color=WARM_TAUPE, selected_color=EMBER_GLOW, selected_hover_color=EMBER_GLOW_HOVER,
            unselected_color=WARM_TAUPE, unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK, font=self.label_font,
            command=self._handle_target_changed,
        )
        self.target_selector.pack(fill="x", pady=(4, 4))
        if self._has_transcript:
            note = ("\"This transcript\" changes the one open now and takes effect as you read. "
                    "\"New transcripts\" sets what transcripts created later start with.")
        else:
            note = ("No transcript is open, so these set what transcripts created later start with. "
                    "Open one to change it on its own.")
        ctk.CTkLabel(
            body, text=note, text_color=COCOA_INK, font=self.small_font,
            wraplength=430, justify="left",
        ).pack(anchor="w", pady=(0, 16))

        # ---- Group words on/off ----
        self.group_switch = self._styled_switch(body, "Group words together")
        self.group_switch.pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            body,
            text=("When on, the reader flashes several words at once instead of one at a time, "
                  "so your eyes move less across each flash."),
            text_color=COCOA_INK, font=self.small_font, wraplength=430, justify="left",
        ).pack(anchor="w", pady=(0, 16))

        # ---- Mode ----
        ctk.CTkLabel(body, text="Group size", text_color=COCOA_INK, font=self.label_font).pack(anchor="w")
        self.mode_selector = ctk.CTkSegmentedButton(
            body, values=["Fixed", "Adaptive"],
            fg_color=WARM_TAUPE, selected_color=EMBER_GLOW, selected_hover_color=EMBER_GLOW_HOVER,
            unselected_color=WARM_TAUPE, unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK, font=self.label_font,
        )
        self.mode_selector.pack(fill="x", pady=(4, 4))
        ctk.CTkLabel(
            body,
            text=("Fixed shows a set number of words per group. Adaptive instead fills each group "
                  "up to a character width, so short words pack together and long ones don't crowd "
                  "the line. Either way a group never runs past the end of a sentence."),
            text_color=COCOA_INK, font=self.small_font, wraplength=430, justify="left",
        ).pack(anchor="w", pady=(0, 16))

        # ---- Fixed word count ----
        fixed_row = ctk.CTkFrame(body, fg_color="transparent")
        fixed_row.pack(fill="x")
        ctk.CTkLabel(fixed_row, text="Words per group", width=120, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.size_label = ctk.CTkLabel(fixed_row, text="", width=70, text_color=COCOA_INK, font=self.label_font)
        self.size_label.pack(side="right")
        self.size_slider = self._styled_slider(
            body, CHUNK_SIZE_RANGE[0], CHUNK_SIZE_RANGE[1], CHUNK_SIZE_RANGE[1] - CHUNK_SIZE_RANGE[0],
            lambda v: self.size_label.configure(text=f"{int(v)} words"),
        )
        self.size_slider.pack(fill="x", pady=(2, 2))
        ctk.CTkLabel(
            body, text="Used in Fixed mode.",
            text_color=COCOA_INK, font=self.small_font, wraplength=430, justify="left",
        ).pack(anchor="w", pady=(0, 14))

        # ---- Adaptive width ----
        width_row = ctk.CTkFrame(body, fg_color="transparent")
        width_row.pack(fill="x")
        ctk.CTkLabel(width_row, text="Group width", width=120, anchor="w", text_color=COCOA_INK, font=self.label_font).pack(side="left")
        self.width_label = ctk.CTkLabel(width_row, text="", width=70, text_color=COCOA_INK, font=self.label_font)
        self.width_label.pack(side="right")
        self.width_slider = self._styled_slider(
            body, CHUNK_CHAR_TARGET_RANGE[0], CHUNK_CHAR_TARGET_RANGE[1],
            CHUNK_CHAR_TARGET_RANGE[1] - CHUNK_CHAR_TARGET_RANGE[0],
            lambda v: self.width_label.configure(text=f"{int(v)} chars"),
        )
        self.width_slider.pack(fill="x", pady=(2, 2))
        ctk.CTkLabel(
            body, text="Used in Adaptive mode, counting letters and the spaces between words.",
            text_color=COCOA_INK, font=self.small_font, wraplength=430, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # Load the controls for the target shown first: the defaults when a
        # transcript is open (the window is reached from the defaults screen),
        # or the only option otherwise.
        self._initial_target = TARGET_DEFAULTS
        self.target_selector.set(self._initial_target)
        self._load_target(self._initial_target)

        # ---- Status line + buttons ----
        self.status_label = ctk.CTkLabel(self, text="", text_color=COCOA_INK, font=self.small_font)
        self.status_label.pack(padx=18, pady=(0, 4), anchor="w")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=18, pady=(0, 16))
        self._styled_button(button_row, "Close", self.destroy, width=90).pack(side="left")
        self._styled_button(button_row, "Apply", self._handle_apply, width=90).pack(side="right")

        # Esc does what Close does. There is no Enter, so a key press can't
        # apply anything by accident.
        bind_dialog_keys(self, on_escape=self.destroy)

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()
        self.after(80, self._reveal_now)

    def _reveal_now(self) -> None:
        if not self.winfo_exists():
            return
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def _styled_slider(self, master, from_, to, steps, command) -> ctk.CTkSlider:
        return ctk.CTkSlider(
            master, from_=from_, to=to, number_of_steps=steps,
            progress_color=EMBER_GLOW, button_color=EMBER_GLOW, button_hover_color=EMBER_GLOW_HOVER,
            fg_color=WARM_LINE, command=command,
        )

    def _styled_switch(self, master, text) -> ctk.CTkSwitch:
        return ctk.CTkSwitch(
            master, text=text, font=self.label_font, text_color=COCOA_INK,
            progress_color=EMBER_GLOW, fg_color=WARM_LINE,
            button_color=COCOA_INK, button_hover_color=COCOA_INK,
        )

    def _styled_button(self, master, text, command, width=140) -> ctk.CTkButton:
        return ctk.CTkButton(
            master, text=text, width=width, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=command,
        )

    def _load_target(self, target: str) -> None:
        """Fill the controls from the stored values for the chosen target."""
        v = self._values[target]
        (self.group_switch.select() if v["enabled"] else self.group_switch.deselect())
        self.mode_selector.set("Adaptive" if v["mode"] == CHUNK_MODE_ADAPTIVE else "Fixed")
        self.size_slider.set(v["size"])
        self.size_label.configure(text=f"{v['size']} words")
        self.width_slider.set(v["char_target"])
        self.width_label.configure(text=f"{v['char_target']} chars")

    def _handle_target_changed(self, target: str) -> None:
        self._load_target(target)
        self.status_label.configure(text="")

    def _handle_apply(self) -> None:
        target = self.target_selector.get()
        enabled = bool(self.group_switch.get())
        mode = CHUNK_MODE_ADAPTIVE if self.mode_selector.get() == "Adaptive" else CHUNK_MODE_FIXED
        size = int(self.size_slider.get())
        char_target = int(self.width_slider.get())

        # Remember what was just applied, so switching the selector away and
        # back shows the applied values rather than the originals.
        self._values[target] = {
            "enabled": enabled, "size": size, "mode": mode, "char_target": char_target,
        }
        target_key = "current" if target == TARGET_CURRENT else "defaults"
        self.on_apply(target_key, enabled, size, mode, char_target)
        self.status_label.configure(
            text="Applied to this transcript." if target == TARGET_CURRENT else "Applied to new transcripts."
        )