from core.parser import clean_transcript
from core.tokenizer import tokenize
from core.orp import split_at_orp, get_orp_index_for_length, ORPWord
from core.timing import wpm_to_delay_ms, apply_pacing_multiplier, apply_length_multiplier, effective_pacing_length
from core.punctuation import split_punctuation, classify_pacing


class ReaderSession:
    """Holds a tokenized, ORP-split transcript and tracks playback position."""

    def __init__(
        self, raw_text: str, wpm: int = 300, start_index: int = 0,
        length_pacing_enabled: bool = False,
    ):
        clean = clean_transcript(raw_text)
        words = tokenize(clean)

        # Built together, once, in this same loop, so self._paces and
        # self._length_bands stay in step with self.frames by
        # construction. All three are fixed-length and never reordered
        # afterward, only self.index ever moves, so there's no risk of
        # them drifting out of sync later.
        self.frames: list[ORPWord] = []
        self._paces: list[str] = []
        self._length_bands: list[int] = []
        for word in words:
            leading, core, trailing = split_punctuation(word)
            # A token that's entirely punctuation, such as a standalone
            # "--", has no core to split an ORP letter or measure a
            # length band around. Falling back to the whole raw token
            # for both, rather than crashing on split_at_orp(""),
            # mirrors the same "core or the whole word" choice
            # split_at_orp() itself needs. Rare in a real transcript,
            # but not impossible, so this has to degrade gracefully
            # instead of raising.
            orp_subject = core if core else word
            frame = split_at_orp(orp_subject)
            if core:
                frame = ORPWord(before=leading + frame.before, focus=frame.focus, after=frame.after + trailing)
            self.frames.append(frame)
            self._paces.append(classify_pacing(leading + trailing))
            self._length_bands.append(get_orp_index_for_length(effective_pacing_length(orp_subject)))

        self.wpm = wpm
        self.index = max(0, min(start_index, len(self.frames)))
        self.length_pacing_enabled = length_pacing_enabled

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
        punctuation_delay = apply_pacing_multiplier(base, self._paces[self.index])
        if not self.length_pacing_enabled:
            return punctuation_delay
        # Only the larger of the two pauses applies; they don't stack.
        # A word that's both long and ends a sentence doesn't get an
        # unusually long compounded pause, just whichever single reason
        # to slow down is bigger. Comparing the two already-applied
        # delays, rather than the two multipliers directly, works out
        # the same here, since both start from the same base and
        # round() is monotonic, so the larger resulting delay always
        # comes from the larger multiplier.
        length_delay = apply_length_multiplier(base, self._length_bands[self.index])
        return max(punctuation_delay, length_delay)

    def advance(self) -> None:
        if not self.is_finished:
            self.index += 1

    def seek(self, delta: int) -> None:
        """Jump the current position by delta words: negative moves
        backward, positive moves forward. Clamped so it can never land
        before the first word or past the last."""
        self.index = max(0, min(self.total_words, self.index + delta))

    def reset(self) -> None:
        self.index = 0

    def set_wpm(self, new_wpm: int) -> None:
        self.wpm = new_wpm

    def set_length_pacing_enabled(self, enabled: bool) -> None:
        self.length_pacing_enabled = enabled