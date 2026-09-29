from core.parser import clean_transcript
from core.tokenizer import tokenize
from core.orp import split_at_orp, get_orp_index_for_length, ORPWord
from core.timing import (
    wpm_to_delay_ms, apply_pacing_multiplier, apply_length_multiplier,
    effective_pacing_length, apply_warm_up, pacing_multiplier, length_multiplier,
)
from core.punctuation import split_punctuation, classify_pacing


class ReaderSession:
    """Holds a tokenized, ORP-split transcript and tracks playback position."""

    def __init__(
        self, raw_text: str, wpm: int = 300, start_index: int = 0,
        length_pacing_enabled: bool = False,
        warm_up_enabled: bool = False,
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

        # Per-word delay multipliers (relative to the flat base delay),
        # summed from each position to the end, so remaining_ms() is O(1)
        # and independent of WPM (which only scales the base delay). Two
        # tables: punctuation pacing alone, and punctuation combined with
        # length pacing (the larger of the two per word, matching
        # current_delay_ms). Toggling length pacing just switches which
        # table remaining_ms() reads, with no rebuild. Warm-up is
        # deliberately excluded: it's a brief start-of-session ramp, so
        # leaving it out keeps the estimate stable and close. Each table has
        # total_words + 1 entries; the last is 0.0, so a finished session
        # reads 0.
        n = len(self.frames)
        self._suffix_punct_mult = [0.0] * (n + 1)
        self._suffix_paced_mult = [0.0] * (n + 1)
        for i in range(n - 1, -1, -1):
            punct = pacing_multiplier(self._paces[i])
            paced = max(punct, length_multiplier(self._length_bands[i]))
            self._suffix_punct_mult[i] = self._suffix_punct_mult[i + 1] + punct
            self._suffix_paced_mult[i] = self._suffix_paced_mult[i + 1] + paced

        self.wpm = wpm
        self.index = max(0, min(start_index, len(self.frames)))
        self.length_pacing_enabled = length_pacing_enabled
        self.warm_up_enabled = warm_up_enabled
        # How many words have been shown since this session began, used to
        # position the warm-up ramp (see core/timing.py's
        # warm_up_multiplier). Counts words actually advanced past, not the
        # transcript index, so starting mid-transcript still eases in and
        # skipping doesn't restart the ramp. Reset by reset().
        self._words_shown = 0

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
            return self._with_warm_up(punctuation_delay)
        # Only the larger of the two pauses applies; they don't stack.
        # A word that's both long and ends a sentence doesn't get an
        # unusually long compounded pause, just whichever single reason
        # to slow down is bigger. Comparing the two already-applied
        # delays, rather than the two multipliers directly, works out
        # the same here, since both start from the same base and
        # round() is monotonic, so the larger resulting delay always
        # comes from the larger multiplier.
        length_delay = apply_length_multiplier(base, self._length_bands[self.index])
        return self._with_warm_up(max(punctuation_delay, length_delay))

    def remaining_ms(self) -> int:
        """Estimated time, in milliseconds, to read from the current word to
        the end at the current WPM. Sums the paced per-word delays (the
        sentence, clause and long-word pauses that would apply), so it
        reflects what playback will actually do, but excludes the warm-up
        ramp, which is a short start-of-session effect. Includes the word
        currently on screen, and returns 0 once finished. O(1): the
        multipliers are pre-summed at construction (see __init__) and only
        the base delay depends on WPM."""
        base = wpm_to_delay_ms(self.wpm)
        suffix = self._suffix_paced_mult if self.length_pacing_enabled else self._suffix_punct_mult
        return round(base * suffix[self.index])

    def _with_warm_up(self, delay_ms: int) -> int:
        """Apply the warm-up ramp to an already-paced delay, if warm-up is
        on. Kept as the single exit point for current_delay_ms's two return
        paths so the ramp is never accidentally skipped on one of them."""
        if not self.warm_up_enabled:
            return delay_ms
        return apply_warm_up(delay_ms, self._words_shown)

    def advance(self) -> None:
        if not self.is_finished:
            self.index += 1
            self._words_shown += 1

    def seek(self, delta: int) -> None:
        """Jump the current position by delta words: negative moves
        backward, positive moves forward. Clamped so it can never land
        before the first word or past the last."""
        self.index = max(0, min(self.total_words, self.index + delta))

    def seek_to(self, index: int) -> None:
        """Jump straight to an absolute word index, rather than by a
        relative delta like seek(). Defined in terms of seek() so it
        inherits exactly the same clamping (never before the first word
        or past the last) and finished-state handling, including that
        seeking back from a finished session un-finishes it. Used by the
        progress scrubber, which knows the target position outright. Like
        seek(), it deliberately leaves _words_shown untouched, so scrubbing
        never restarts the warm-up ramp."""
        self.seek(index - self.index)

    def reset(self) -> None:
        self.index = 0
        # Restart the warm-up ramp too: restart() is a deliberate "read this
        # from the top again", so it should ease back in just like a fresh
        # session start.
        self._words_shown = 0

    def set_wpm(self, new_wpm: int) -> None:
        self.wpm = new_wpm

    def set_length_pacing_enabled(self, enabled: bool) -> None:
        self.length_pacing_enabled = enabled

    def set_warm_up_enabled(self, enabled: bool) -> None:
        self.warm_up_enabled = enabled