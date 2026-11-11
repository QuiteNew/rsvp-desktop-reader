from dataclasses import replace

import customtkinter as ctk

from core.chime import CHANGE_PATTERN, CHIME_STYLES, MIN_CHIME_GAP_MS, SPEAKER_PATTERNS, chime_length_ms
from core.speakers import speaker_rows, speakers_to_save
from gui.components.dialog_keys import bind_dialog_keys
from gui.theme import (
    HEARTH_PAPER, COCOA_INK, WARM_TAUPE, WARM_LINE, EMBER_GLOW, EMBER_GLOW_HOVER,
    FONT_BODY, apply_app_icon, center_over_parent,
)

# What the sound and style choices are called on screen, by the value saved
# in the settings.
SOUND_LABELS = {"off": "Off", "change": "One chime", "per_speaker": "Per speaker"}
STYLE_LABELS = {style: style.capitalize() for style in CHIME_STYLES}

# The speaker list's Automatic/Custom label.
LIST_AUTOMATIC = "Automatic"
LIST_CUSTOM = "Custom"

# The Listen button plays this many speakers' chimes when Sound is Per
# speaker, with a short pause between them on top of the reader's own gap,
# so each one can be heard on its own.
PREVIEW_SPEAKERS = 3
PREVIEW_PAUSE_MS = 250

# How tall the speaker list can grow before it scrolls (four rows), and the
# height of one row, both before display scaling.
SPEAKER_LIST_MAX_PX = 136
SPEAKER_ROW_PX = 34

# The window's size. It's shorter when there's no speaker list to show, and
# never taller than the Chunking window's 690 by much, so it still fits a
# small laptop screen.
WINDOW_WIDTH = 470
WINDOW_HEIGHT_WITH_LIST = 700
WINDOW_HEIGHT_WITHOUT_LIST = 540


def preview_plan(sound: str, style: str) -> list[tuple[int, tuple[float, ...]]]:
    """What the Listen button plays for these choices: (when, notes) pairs,
    with when in milliseconds after the click. Per speaker plays the first
    PREVIEW_SPEAKERS speakers' patterns one after another. One chime, and Off
    too (so a style can still be heard before a sound is picked), plays the
    one change chime.

    Each chime starts once the one before has finished, the same way the
    reader spaces them (see ChimeGap in core/chime.py), plus PREVIEW_PAUSE_MS,
    since Windows cuts off a sound still playing when the next one starts."""
    patterns = SPEAKER_PATTERNS[:PREVIEW_SPEAKERS] if sound == "per_speaker" else (CHANGE_PATTERN,)
    plan = []
    when = 0
    for notes in patterns:
        plan.append((when, notes))
        when += max(MIN_CHIME_GAP_MS, chime_length_ms(notes, style)) + PREVIEW_PAUSE_MS
    return plan


def appearances_text(appearances: int) -> str:
    return "seen 1 time" if appearances == 1 else f"seen {appearances} times"


class SpeakerCuesWindow(ctk.CTkToplevel):
    """Every Speaker cues setting in one place.

    The top part is for the whole app: the on/off switch, which visual cues
    show (the name tag and the flash), the sound (off, one chime for any
    change, or a chime per speaker) and its style, with a Listen button that
    plays the choice before it's applied. Where chimes can't be played (only
    Windows has them for now) the sound part is greyed out and says so, and
    whatever was saved there is kept as it is.

    The bottom part is the speaker list of the transcript open right now: a
    row for every label found in its text, with a tick box, the name it's
    shown with, and how often it starts a line. Changing a tick or a name
    makes the list Custom; typing the same name on two rows makes them one
    speaker. "Back to automatic" puts every row back the way Auto has it.
    With no transcript open the part only says so.

    Apply hands the top part to on_apply(enabled, name_tag, flash, sound,
    style) and, when a transcript is shown, its list to
    on_apply_speakers(transcript_id, speakers), where speakers is None for
    Automatic (see speakers_to_save() in core/speakers.py). The window stays
    open after Apply, the same as the Chunking window, and Close (or Esc)
    leaves without applying anything more."""

    def __init__(
        self, master,
        enabled, name_tag, flash, sound, style,
        transcript,
        on_apply,
        on_apply_speakers,
        chime_player=None,
    ):
        super().__init__(master)

        # Hidden until the whole window is built and painted, then revealed in
        # one step, so it never flashes half-drawn (the same approach the
        # other windows in this app use).
        self.attributes("-alpha", 0)

        self.on_apply = on_apply
        self.on_apply_speakers = on_apply_speakers
        self._chime_player = chime_player
        self._sound_available = chime_player is not None and chime_player.available
        self._transcript = transcript
        self._preview_after_ids: list[str] = []
        # The rows as the transcript's list has them, and as Auto would have
        # them (for "Back to automatic"). Both empty with no transcript.
        if transcript is not None:
            self._loaded_rows = speaker_rows(transcript.raw_text, transcript.speaker_custom)
            self._auto_rows = speaker_rows(transcript.raw_text, None)
        else:
            self._loaded_rows, self._auto_rows = [], []
        # One entry per speaker row: (the row as it was loaded, its tick box,
        # its name's text variable). Empty with no transcript or no labels.
        self._row_widgets = []

        self.title("Speaker cues")
        apply_app_icon(self)
        height = WINDOW_HEIGHT_WITH_LIST if self._loaded_rows else WINDOW_HEIGHT_WITHOUT_LIST
        center_over_parent(self, WINDOW_WIDTH, height)
        self.resizable(False, False)
        self.configure(fg_color=HEARTH_PAPER)

        self.label_font = ctk.CTkFont(family=FONT_BODY, size=13)
        self.small_font = ctk.CTkFont(family=FONT_BODY, size=11)
        self.button_font = ctk.CTkFont(family=FONT_BODY, size=13)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(16, 0))

        # ---- On/off ----
        self.enabled_switch = self._styled_switch(body, "Speaker cues")
        self.enabled_switch.pack(anchor="w", pady=(0, 4))
        self._note(body, (
            "When on, the reader shows who is speaking in transcripts that have names at the "
            "start of their lines, like \"Interviewer:\", and gives a cue when the speaker changes. "
            "Applies to every transcript."
        ), pady=(0, 14))

        # ---- Visual cues ----
        ctk.CTkLabel(body, text="Show", text_color=COCOA_INK, font=self.label_font).pack(anchor="w")
        self.name_tag_check = self._styled_check(body, "The speaker's name above the word")
        self.name_tag_check.pack(anchor="w", pady=(6, 4))
        self.flash_check = self._styled_check(body, "A brief flash when the speaker changes")
        self.flash_check.pack(anchor="w", pady=(0, 14))

        # ---- Sound ----
        ctk.CTkLabel(body, text="Sound", text_color=COCOA_INK, font=self.label_font).pack(anchor="w")
        self.sound_selector = self._styled_segments(body, list(SOUND_LABELS.values()))
        self.sound_selector.pack(fill="x", pady=(4, 8))
        style_row = ctk.CTkFrame(body, fg_color="transparent")
        style_row.pack(fill="x")
        self.style_selector = self._styled_segments(style_row, list(STYLE_LABELS.values()))
        self.style_selector.pack(side="left", fill="x", expand=True)
        self.listen_button = self._styled_button(style_row, "\u25b6 Listen", self._handle_listen, width=96)
        self.listen_button.pack(side="right", padx=(8, 0))
        if self._sound_available:
            sound_note = ("One chime sounds at every change. Per speaker gives each speaker a chime "
                          "of their own. Listen plays your choice before you apply it.")
        else:
            sound_note = "Sound is Windows only for now, so it can't be changed here."
            for widget in (self.sound_selector, self.style_selector, self.listen_button):
                widget.configure(state="disabled")
        self.sound_note = self._note(body, sound_note, pady=(4, 14))

        # ---- Speaker list ----
        self._build_speaker_list(body)

        # ---- Load the saved values ----
        (self.enabled_switch.select() if enabled else self.enabled_switch.deselect())
        (self.name_tag_check.select() if name_tag else self.name_tag_check.deselect())
        (self.flash_check.select() if flash else self.flash_check.deselect())
        self.sound_selector.set(SOUND_LABELS[sound])
        self.style_selector.set(STYLE_LABELS[style])

        # ---- Status line + buttons ----
        self.status_label = ctk.CTkLabel(self, text="", text_color=COCOA_INK, font=self.small_font)
        self.status_label.pack(padx=18, pady=(0, 4), anchor="w")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=18, pady=(0, 16))
        self.close_button = self._styled_button(button_row, "Close", self.destroy, width=90)
        self.close_button.pack(side="left")
        self.apply_button = self._styled_button(button_row, "Apply", self._handle_apply, width=90)
        self.apply_button.pack(side="right")

        # Esc does what Close does. There is no Enter, so a key press in a
        # name box can't apply anything by accident.
        bind_dialog_keys(self, on_escape=self.destroy)

        self.lift()
        self.transient(master)
        self.after(10, self.grab_set)
        self.focus_force()
        self.after(80, self._reveal_now)

    def _build_speaker_list(self, body) -> None:
        header = ctk.CTkFrame(body, fg_color="transparent")
        header.pack(fill="x")
        if self._transcript is None:
            ctk.CTkLabel(header, text="Speakers", text_color=COCOA_INK, font=self.label_font).pack(side="left")
            self.list_mode_label = None
            self._note(body, "Open a transcript to see its speakers and change them.", pady=(4, 0))
            return

        ctk.CTkLabel(
            header, text="Speakers in this transcript", text_color=COCOA_INK, font=self.label_font,
        ).pack(side="left")
        self.list_mode_label = ctk.CTkLabel(header, text="", text_color=COCOA_INK, font=self.small_font)
        self.list_mode_label.pack(side="right")
        self._note(body, self._transcript.title, pady=(0, 6))

        rows = self._loaded_rows
        if not rows:
            self._note(body, (
                "No speaker names were found. A name counts when it starts a line and is "
                "followed by a colon, like \"Interviewer:\"."
            ), pady=(4, 0))
            self.list_mode_label.configure(text=LIST_AUTOMATIC)
            return

        list_height = min(SPEAKER_LIST_MAX_PX, len(rows) * SPEAKER_ROW_PX)
        self.speaker_list = ctk.CTkScrollableFrame(
            body, height=list_height,
            fg_color=WARM_TAUPE, corner_radius=10,
            scrollbar_button_color=WARM_LINE, scrollbar_button_hover_color=EMBER_GLOW,
        )
        self.speaker_list.pack(fill="x", pady=(0, 6))
        # A CTkScrollableFrame's scrollbar asks for 200px of height whatever
        # height the frame is given, which would make the list that tall and
        # push Close and Apply off the bottom of the window. Ask for the list's
        # own height instead (the same fix as the Profiles tab's list). Reaches
        # into the private _scrollbar; if that name ever changes the only effect
        # is a taller list.
        try:
            self.speaker_list._scrollbar.configure(height=list_height)
        except AttributeError:
            pass
        for row in rows:
            line = ctk.CTkFrame(self.speaker_list, fg_color="transparent")
            line.pack(fill="x", pady=2)
            check = self._styled_check(line, "", command=self._update_list_mode)
            check.configure(width=24)
            check.pack(side="left", padx=(4, 6))
            (check.select() if row.ticked else check.deselect())
            name = ctk.StringVar(value=row.name)
            name.trace_add("write", lambda *_args: self._update_list_mode())
            ctk.CTkEntry(
                line, textvariable=name, width=210,
                fg_color=HEARTH_PAPER, border_color=WARM_LINE, border_width=1,
                text_color=COCOA_INK, font=self.label_font,
            ).pack(side="left")
            ctk.CTkLabel(
                line, text=appearances_text(row.appearances), text_color=COCOA_INK, font=self.small_font,
            ).pack(side="right", padx=(6, 4))
            self._row_widgets.append((row, check, name))

        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.pack(fill="x")
        self.back_to_automatic_button = self._styled_button(
            footer, "Back to automatic", self._handle_back_to_automatic, width=150,
        )
        self.back_to_automatic_button.pack(side="right")
        ctk.CTkLabel(
            footer, text="The same name on two rows makes them one speaker.",
            text_color=COCOA_INK, font=self.small_font, wraplength=260, justify="left",
        ).pack(side="left", anchor="w")
        self._update_list_mode()

    def _reveal_now(self) -> None:
        if not self.winfo_exists():
            return
        self.update_idletasks()
        self.attributes("-alpha", 1)

    def destroy(self) -> None:
        self._cancel_preview()
        super().destroy()

    # ---- Small builders ----

    def _note(self, master, text, pady) -> ctk.CTkLabel:
        label = ctk.CTkLabel(
            master, text=text, text_color=COCOA_INK, font=self.small_font, wraplength=430, justify="left",
        )
        label.pack(anchor="w", pady=pady)
        return label

    def _styled_switch(self, master, text) -> ctk.CTkSwitch:
        return ctk.CTkSwitch(
            master, text=text, font=self.label_font, text_color=COCOA_INK,
            progress_color=EMBER_GLOW, fg_color=WARM_LINE,
            button_color=COCOA_INK, button_hover_color=COCOA_INK,
        )

    def _styled_check(self, master, text, command=None) -> ctk.CTkCheckBox:
        return ctk.CTkCheckBox(
            master, text=text, font=self.label_font, text_color=COCOA_INK,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, border_color=WARM_LINE,
            checkmark_color=COCOA_INK, command=command,
        )

    def _styled_segments(self, master, values) -> ctk.CTkSegmentedButton:
        return ctk.CTkSegmentedButton(
            master, values=values,
            fg_color=WARM_TAUPE, selected_color=EMBER_GLOW, selected_hover_color=EMBER_GLOW_HOVER,
            unselected_color=WARM_TAUPE, unselected_hover_color=WARM_LINE,
            text_color=COCOA_INK, font=self.label_font,
        )

    def _styled_button(self, master, text, command, width=140) -> ctk.CTkButton:
        return ctk.CTkButton(
            master, text=text, width=width, corner_radius=10,
            fg_color=EMBER_GLOW, hover_color=EMBER_GLOW_HOVER, text_color=COCOA_INK,
            font=self.button_font, command=command,
        )

    # ---- Reading the controls ----

    def chosen_sound(self) -> str:
        return {label: value for value, label in SOUND_LABELS.items()}[self.sound_selector.get()]

    def chosen_style(self) -> str:
        return {label: value for value, label in STYLE_LABELS.items()}[self.style_selector.get()]

    def current_rows(self):
        """The speaker rows as they are on screen now."""
        return [
            replace(row, ticked=bool(check.get()), name=name.get())
            for row, check, name in self._row_widgets
        ]

    # ---- The speaker list ----

    def _update_list_mode(self) -> None:
        if self.list_mode_label is None:
            return
        mode = LIST_AUTOMATIC if speakers_to_save(self.current_rows()) is None else LIST_CUSTOM
        self.list_mode_label.configure(text=mode)

    def _handle_back_to_automatic(self) -> None:
        for auto_row, (_row, check, name) in zip(self._auto_rows, self._row_widgets):
            (check.select() if auto_row.ticked else check.deselect())
            name.set(auto_row.name)
        self._update_list_mode()

    # ---- Listen ----

    def _handle_listen(self) -> None:
        """Play the sound and style chosen right now, applied or not. A
        second click starts again from the beginning. Never called without
        sound, since the button is greyed out then."""
        self._cancel_preview()
        style = self.chosen_style()
        for when, notes in preview_plan(self.chosen_sound(), style):
            if when == 0:
                self._chime_player.play(notes, style, wait=True)
            else:
                self._preview_after_ids.append(
                    self.after(when, lambda notes=notes: self._chime_player.play(notes, style, wait=True))
                )

    def _cancel_preview(self) -> None:
        for after_id in self._preview_after_ids:
            self.after_cancel(after_id)
        self._preview_after_ids = []

    # ---- Apply ----

    def _handle_apply(self) -> None:
        self.on_apply(
            bool(self.enabled_switch.get()),
            bool(self.name_tag_check.get()),
            bool(self.flash_check.get()),
            self.chosen_sound(),
            self.chosen_style(),
        )
        if self._transcript is not None and self._row_widgets:
            self.on_apply_speakers(self._transcript.id, speakers_to_save(self.current_rows()))
        self.status_label.configure(text="Applied.")
