from core.parser import clean_transcript
from core.tokenizer import tokenize
from core.orp import split_at_orp, ORPWord
from core.timing import wpm_to_delay_ms, apply_pacing_multiplier
from core.punctuation import split_punctuation, classify_pacing


class ReaderSession:
    """Holds a tokenized, ORP-split transcript and tracks playback position."""

    def __init__(self, raw_text: str, wpm: int = 300, start_index: int = 0):
        clean = clean_transcript(raw_text)
        words = tokenize(clean)

        # Built together, once, in this same loop -- self._paces stays in
        # step with self.frames by construction (both are fixed-length
        # and never reordered afterward; only self.index ever moves), so
        # there's no risk of the two drifting out of sync later.
        self.frames: list[ORPWord] = []
        self._paces: list[str] = []
        for word in words:
            leading, core, trailing = split_punctuation(word)
            # A token that's entirely punctuation (e.g. a standalone
            # "--") has no core to split an ORP letter out of -- fall
            # back to treating the whole token as the ORP subject
            # rather than crashing on split_at_orp(""). Rare in a real
            # transcript, but not impossible, so this has to degrade
            # gracefully, not raise.
            if core:
                frame = split_at_orp(core)
                frame = ORPWord(before=leading + frame.before, focus=frame.focus, after=frame.after + trailing)
            else:
                frame = split_at_orp(word)
            self.frames.append(frame)
            self._paces.append(classify_pacing(leading + trailing))

        self.wpm = wpm
        self.index = max(0, min(start_index, len(self.frames)))

    @property
    def total_words(self) -> int:
        return len(self.frames)

    @property
    def is_finished(self) -> bool:
        return self.index >= self.total_words

    def current_frame(self) -> ORPWord | None:
        if self.is_finished:
            return None
        return self.frames[self.index]

    def current_delay_ms(self) -> int:
        base = wpm_to_delay_ms(self.wpm)
        if self.is_finished:
            return base
        return apply_pacing_multiplier(base, self._paces[self.index])

    def advance(self) -> None:
        if not self.is_finished:
            self.index += 1

    def seek(self, delta: int) -> None:
        """Jump the current position by delta words — negative moves
        backward, positive moves forward — clamped so it can never land
        before the first word or past the last."""
        self.index = max(0, min(self.total_words, self.index + delta))

    def reset(self) -> None:
        self.index = 0

    def set_wpm(self, new_wpm: int) -> None:
        self.wpm = new_wpm