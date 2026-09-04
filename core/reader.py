from core.parser import clean_transcript
from core.tokenizer import tokenize
from core.orp import split_at_orp, ORPWord
from core.timing import wpm_to_delay_ms


class ReaderSession:
    """Holds a tokenized, ORP-split transcript and tracks playback position."""

    def __init__(self, raw_text: str, wpm: int = 300, start_index: int = 0):
        clean = clean_transcript(raw_text)
        words = tokenize(clean)
        self.frames: list[ORPWord] = [split_at_orp(w) for w in words]
        self.wpm = wpm
        # Clamped defensively — guards against a stale saved position ever
        # exceeding the word count (not currently reachable, but cheap to guard)
        self.index = min(start_index, len(self.frames))

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
        return wpm_to_delay_ms(self.wpm)

    def advance(self) -> None:
        if not self.is_finished:
            self.index += 1

    def reset(self) -> None:
        self.index = 0

    def set_wpm(self, new_wpm: int) -> None:
        self.wpm = new_wpm