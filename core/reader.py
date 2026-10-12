from typing import NamedTuple

from core.parser import clean_transcript
from core.tokenizer import tokenize
from core.orp import split_at_orp, get_orp_index_for_length, ORPWord
from core.timing import (
    wpm_to_delay_ms, apply_pacing_multiplier, apply_length_multiplier,
    effective_pacing_length, apply_warm_up, pacing_multiplier, length_multiplier,
)
from core.punctuation import split_punctuation, classify_pacing, PACE_SENTENCE


# Soft upper bound on the characters (words plus the single spaces between
# them) a chunk may hold in FIXED chunking mode. A chunk stops before a word
# that would push it past this, so a run of long words does not overflow the
# reading area. It never yields an empty chunk: a lone word longer than the cap
# still forms a one-word chunk. This is a tuning value. In ADAPTIVE mode the per-transcript
# chunk_char_target plays this role instead (see _chunk_limits()).
CHUNK_CHAR_CAP = 30

# Chunk sizing modes (Transcript.chunk_mode). "fixed" groups up to chunk_size
# words (v1 behaviour); "adaptive" fills each chunk up to chunk_char_target
# characters instead, capped at ADAPTIVE_MAX_WORDS words.
CHUNK_MODE_FIXED = "fixed"
CHUNK_MODE_ADAPTIVE = "adaptive"

# Hard ceiling on how many words one adaptive chunk may hold, regardless of
# the character target, so a run of very short words ("a is of to it") can't
# pile an absurd number into a single flash. See the adaptive design doc.
ADAPTIVE_MAX_WORDS = 6


class PeripheralContext(NamedTuple):
    """The words around the current one, for the peripheral context ribbon:
    `before` in reading order (left to right), the `current` word (None when
    the session is finished or empty), and `after` in reading order."""
    before: list[str]
    current: str | None
    after: list[str]


def assemble_chunk_text(frames: list[ORPWord]) -> tuple[str, str, str]:
    """Assemble a chunk's on-screen text as a (before, focus, after) triple,
    the exact split the reader draws: only the chunk's first word keeps its own
    before/focus/after, and every later word trails inside the after part after
    a single separating space. With a single frame this is just that frame's own
    split. Returns three empty strings for an empty list, which a real chunk
    never is. Kept next to how chunks are built so the reader's drawing and the
    font-fit measurement share one definition of a chunk's text instead of each
    assembling it their own way."""
    if not frames:
        return "", "", ""
    first = frames[0]
    after_text = first.after
    if len(frames) > 1:
        trailing = " ".join(f.before + f.focus + f.after for f in frames[1:])
        after_text = f"{first.after} {trailing}"
    return first.before, first.focus, after_text


class ReaderSession:
    """Holds a tokenized, ORP-split transcript and tracks playback position.

    When chunking is on (chunk_enabled), the words are grouped into chunks and
    the reader advances a whole chunk at a time rather than a single word. How
    a chunk's size is decided depends on chunk_mode: "fixed" groups up to
    chunk_size words (the v1 behaviour), while "adaptive" fills each chunk up
    to chunk_char_target characters instead, capped at ADAPTIVE_MAX_WORDS
    words. Either way the word index stays the canonical position: advancing,
    skipping and seeking all land on a chunk's first word, so a saved position
    or bookmark (a word index) stays valid and flipping chunking off just
    reads the same words one at a time. When chunking is off, every chunk is a
    single word and the behaviour is identical to single-word reading."""

    def __init__(
        self, raw_text: str, wpm: int = 300, start_index: int = 0,
        length_pacing_enabled: bool = False,
        warm_up_enabled: bool = False,
        chunk_enabled: bool = False,
        chunk_size: int = 2,
        chunk_mode: str = CHUNK_MODE_FIXED,
        chunk_char_target: int = 30,
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
        # reads 0. Chunking does not change these: a chunk's dwell is the sum
        # of its words' delays, so the total time to the end is the same
        # however the words are grouped.
        n = len(self.frames)
        self._suffix_punct_mult = [0.0] * (n + 1)
        self._suffix_paced_mult = [0.0] * (n + 1)
        for i in range(n - 1, -1, -1):
            punct = pacing_multiplier(self._paces[i])
            paced = max(punct, length_multiplier(self._length_bands[i]))
            self._suffix_punct_mult[i] = self._suffix_punct_mult[i + 1] + punct
            self._suffix_paced_mult[i] = self._suffix_paced_mult[i + 1] + paced

        self.wpm = wpm
        self.length_pacing_enabled = length_pacing_enabled
        self.warm_up_enabled = warm_up_enabled
        self.chunking_enabled = chunk_enabled
        self.chunk_size = chunk_size
        self.chunk_mode = chunk_mode
        self.chunk_char_target = chunk_char_target

        # Group the words into chunks, using whatever limits the current mode
        # implies (see _chunk_limits()). With chunking off those collapse to
        # one word per chunk, leaving single-word reading unchanged. _chunks is
        # the ordered list of (start, end) word-index ranges (end exclusive);
        # _chunk_bounds_of_word maps each word index to the (start, end) of its
        # chunk, for O(1) lookup when advancing and snapping.
        max_words, char_limit = self._chunk_limits()
        self._chunks: list[tuple[int, int]] = self._build_chunks(max_words, char_limit)
        self._chunk_bounds_of_word: list[tuple[int, int]] = [(0, 0)] * n
        for start, end in self._chunks:
            for j in range(start, end):
                self._chunk_bounds_of_word[j] = (start, end)

        # Clamp the start position, then snap it to the start of the chunk that
        # contains it, so a session always begins on a chunk boundary.
        idx = max(0, min(start_index, n))
        if idx < n:
            idx = self._chunk_bounds_of_word[idx][0]
        self.index = idx

        # How many words have been shown since this session began, used to
        # position the warm-up ramp (see core/timing.py's
        # warm_up_multiplier). Counts words actually advanced past, not the
        # transcript index, so starting mid-transcript still eases in and
        # skipping doesn't restart the ramp. Advancing a chunk bumps it by the
        # chunk's word count, so the ramp stays word-based. Reset by reset().
        self._words_shown = 0

    def _chunk_limits(self) -> tuple[int, int]:
        """The (max_words, char_limit) a single chunk may reach, derived from
        the current chunking state. Both __init__ and _rebuild_chunks() go
        through here, so the fixed and adaptive rules live in one place and
        can't drift.

        - Chunking off: one word per chunk (max_words 1), reproducing
          single-word reading. The char limit is irrelevant at one word.
        - Fixed mode: up to chunk_size words, with CHUNK_CHAR_CAP as the same
          safety cap v1 used, so fixed grouping stays byte-for-byte unchanged.
        - Adaptive mode: fill up to chunk_char_target characters instead, with
          ADAPTIVE_MAX_WORDS as a word ceiling. """
        if not self.chunking_enabled:
            return 1, CHUNK_CHAR_CAP
        if self.chunk_mode == CHUNK_MODE_ADAPTIVE:
            return ADAPTIVE_MAX_WORDS, self.chunk_char_target
        return self.chunk_size, CHUNK_CHAR_CAP

    def _build_chunks(self, max_words: int, char_limit: int) -> list[tuple[int, int]]:
        """Group the word indices into chunks, scanning left to right and
        closing the current chunk when any of three things holds: it has
        reached `max_words` words; the word just added ends a sentence (so a
        chunk never crosses a sentence boundary); or adding the next word would
        push the chunk past `char_limit` characters (words plus the single
        spaces between them). The first word of a chunk is always included, so
        a single word longer than the limit still forms a one-word chunk rather
        than an empty one, and the final chunk may be short. With max_words 1
        every chunk is a single word, whatever the char limit."""
        n = len(self.frames)
        chunks: list[tuple[int, int]] = []
        start = 0
        while start < n:
            i = start
            char_count = 0
            while i < n:
                frame = self.frames[i]
                word_len = len(frame.before) + len(frame.focus) + len(frame.after)
                projected = char_count + (0 if i == start else 1) + word_len
                if i > start and projected > char_limit:
                    break
                char_count = projected
                i += 1
                if i - start >= max_words:
                    break
                if self._paces[i - 1] == PACE_SENTENCE:
                    break
            chunks.append((start, i))
            start = i
        return chunks

    def _rebuild_chunks(self) -> None:
        """Recompute the chunk ranges and the word-to-chunk map from the
        current chunking state, reusing the already-built frames and pacing
        tables. Shared by __init__ (indirectly, via the inline build it
        mirrors) and set_chunking(). The per-mode limits come from
        _chunk_limits()."""
        max_words, char_limit = self._chunk_limits()
        n = len(self.frames)
        self._chunks = self._build_chunks(max_words, char_limit)
        self._chunk_bounds_of_word = [(0, 0)] * n
        for start, end in self._chunks:
            for j in range(start, end):
                self._chunk_bounds_of_word[j] = (start, end)

    @property
    def total_words(self) -> int:
        return len(self.frames)

    @property
    def is_finished(self) -> bool:
        return self.index >= self.total_words

    def chunk_ranges(self) -> list[tuple[int, int]]:
        """The word-index ranges of every chunk, (start, end) with end
        exclusive, in order. With chunking off there is one range per word."""
        return list(self._chunks)

    def chunk_texts(self) -> list[tuple[str, str, str]]:
        """The assembled (before, focus, after) text of every chunk, in order,
        the same split the reader draws (see assemble_chunk_text). Read-only and
        position-independent: it spans the whole transcript, not just the chunk
        on screen, so the display can measure the widest chunk once and fit the
        font to the reading row. With chunking off there is one entry per word."""
        return [assemble_chunk_text(self.frames[start:end]) for start, end in self._chunks]

    def current_frame(self) -> ORPWord | None:
        if self.is_finished:
            return None
        return self.frames[self.index]

    def current_chunk(self) -> list[ORPWord] | None:
        """The ORP frames of the chunk currently on screen, in reading order,
        or None when the session is finished. The first frame is the one whose
        ORP letter the reader anchors and highlights; the rest trail to its
        right. With chunking off this is a single-frame list, matching
        current_frame()."""
        if self.is_finished:
            return None
        start, end = self._chunk_bounds_of_word[self.index]
        return self.frames[start:end]

    def current_chunk_bounds(self) -> tuple[int, int] | None:
        """The (start, end) word-index range of the chunk currently on screen,
        end exclusive, or None when finished. Lets the display find the words
        just before and after the whole chunk for the peripheral ribbon."""
        if self.is_finished:
            return None
        return self._chunk_bounds_of_word[self.index]

    def _word_at(self, i: int) -> str:
        """The plain text of the word at index i, punctuation included,
        reconstructed from its ORP frame the same way the reader shows it."""
        frame = self.frames[i]
        return frame.before + frame.focus + frame.after

    def peripheral_context(self, before: int, after: int) -> PeripheralContext:
        """The words immediately around the current one, for the peripheral
        context ribbon: up to `before` words preceding it (in reading order,
        left to right), the current word, and up to `after` words following
        it. Near the start or end there are simply fewer, and a finished or
        empty session has no current word, so it returns all-empty with
        current None. Pure and read-only: it never moves the position, so
        the ribbon can be recomputed freely after advancing, skipping or
        seeking. Punctuation stays attached to its word (the reconstructed
        word is the frame's before+focus+after), so a trailing comma or
        period shows in the ribbon just as it plays."""
        before = max(0, before)
        after = max(0, after)
        if self.is_finished or self.total_words == 0:
            return PeripheralContext([], None, [])
        start = max(0, self.index - before)
        before_words = [self._word_at(j) for j in range(start, self.index)]
        end = min(self.total_words, self.index + 1 + after)
        after_words = [self._word_at(j) for j in range(self.index + 1, end)]
        return PeripheralContext(before_words, self._word_at(self.index), after_words)

    def chunk_peripheral_context(self, before: int, after: int) -> PeripheralContext:
        """Peripheral context for the ribbon when chunking is on: `before`
        words precede the chunk's FIRST word and `after` words follow its
        LAST word, so the ribbon shows what is around the whole chunk rather
        than repeating words already on screen in it. `current` is the chunk's
        first word, the one under the anchor. With chunking off a chunk is a
        single word, so this is identical to peripheral_context()."""
        before = max(0, before)
        after = max(0, after)
        if self.is_finished or self.total_words == 0:
            return PeripheralContext([], None, [])
        start, end = self._chunk_bounds_of_word[self.index]
        before_start = max(0, start - before)
        before_words = [self._word_at(j) for j in range(before_start, start)]
        after_end = min(self.total_words, end + after)
        after_words = [self._word_at(j) for j in range(end, after_end)]
        return PeripheralContext(before_words, self._word_at(start), after_words)

    def _paced_delay_at(self, i: int) -> int:
        """The per-word delay for word i from WPM and pacing, before the
        warm-up ramp. With length pacing off it is the base delay with
        punctuation pacing; with it on, the larger of the punctuation and
        long-word delays, since the two do not stack. Pulled out so the
        single-word delay and a chunk's summed delay compute each word the same
        way."""
        base = wpm_to_delay_ms(self.wpm)
        punctuation_delay = apply_pacing_multiplier(base, self._paces[i])
        if not self.length_pacing_enabled:
            return punctuation_delay
        # Comparing the two already-applied delays matches comparing the
        # multipliers directly: both start from the same base and round() is
        # monotonic, so the larger delay always comes from the larger pause.
        length_delay = apply_length_multiplier(base, self._length_bands[i])
        return max(punctuation_delay, length_delay)

    def _delay_at(self, i: int, words_shown: int) -> int:
        """The on-screen delay for word i: pacing plus the warm-up ramp at the
        given words-shown position. words_shown is a parameter rather than
        self._words_shown so a chunk can age each of its member words in turn
        (the k-th word of a chunk uses self._words_shown + k), which keeps the
        chunk's total time equal to what the same words would take read one at
        a time."""
        paced = self._paced_delay_at(i)
        if not self.warm_up_enabled:
            return paced
        return apply_warm_up(paced, words_shown)

    def current_delay_ms(self) -> int:
        base = wpm_to_delay_ms(self.wpm)
        if self.is_finished:
            return base
        return self._delay_at(self.index, self._words_shown)

    def current_chunk_delay_ms(self) -> int:
        """How long the current chunk stays on screen: the sum of its member
        words' delays, so WPM stays exactly true (N words take the time those N
        words would) and any punctuation pause inside the chunk is already
        counted and lands at its end. Each member word ages the warm-up ramp by
        one, as it would read singly. With chunking off this is a single word,
        so it equals current_delay_ms()."""
        base = wpm_to_delay_ms(self.wpm)
        if self.is_finished:
            return base
        start, end = self._chunk_bounds_of_word[self.index]
        total = 0
        for k, j in enumerate(range(start, end)):
            total += self._delay_at(j, self._words_shown + k)
        return total

    def remaining_ms(self) -> int:
        """Estimated time, in milliseconds, to read from the current word to
        the end at the current WPM. Sums the paced per-word delays (the
        sentence, clause and long-word pauses that would apply), so it
        reflects what playback will actually do, but excludes the warm-up
        ramp, which is a short start-of-session effect. Includes the word
        currently on screen, and returns 0 once finished. O(1): the
        multipliers are pre-summed at construction (see __init__) and only
        the base delay depends on WPM. Unaffected by chunking, since a chunk's
        dwell is the sum of its words' delays."""
        base = wpm_to_delay_ms(self.wpm)
        suffix = self._suffix_paced_mult if self.length_pacing_enabled else self._suffix_punct_mult
        return round(base * suffix[self.index])

    def advance(self) -> None:
        """Advance to the next chunk: move the word index to the first word of
        the chunk after the current one, and age the warm-up ramp by the number
        of words just passed. With chunking off each chunk is a single word, so
        this steps the index by one, exactly as single-word reading does."""
        if self.is_finished:
            return
        _, end = self._chunk_bounds_of_word[self.index]
        self._words_shown += end - self.index
        self.index = end

    def seek(self, delta: int) -> None:
        """Jump the current position by delta words: negative moves backward,
        positive moves forward. Clamped so it can never land before the first
        word or past the last, then snapped to the start of the chunk that
        contains the landed word, so playback resumes from a chunk boundary.
        With chunking off the snap is a no-op (every word is its own chunk), so
        this is a plain word jump. Leaves the warm-up position untouched, so
        skipping never restarts the ramp."""
        landed = max(0, min(self.total_words, self.index + delta))
        if landed < self.total_words:
            landed = self._chunk_bounds_of_word[landed][0]
        self.index = landed

    def seek_to(self, index: int) -> None:
        """Jump straight to an absolute word index, rather than by a
        relative delta like seek(). Defined in terms of seek(), so it
        inherits exactly the same clamping (never before the first word
        or past the last), the chunk-boundary snap, and leaving _words_shown
        untouched (scrubbing never restarts the warm-up ramp). Seeking back
        from a finished session un-finishes it. Used by the progress scrubber,
        which knows the target position outright."""
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

    def set_chunking(self, enabled: bool, size: int, mode: str | None = None, char_target: int | None = None) -> None:
        """Re-group this already-built session with new chunking settings, in
        place, without rebuilding the frames, pacing tables or warm-up ramp.
        Recomputes the chunk ranges and the word-to-chunk map, then snaps the
        current word index to the start of the chunk that now contains it, so
        the reading position is preserved as a word and only its grouping
        changes. Leaves _words_shown untouched, the same way seek() does:
        re-grouping is not a fresh start.

        enabled and size always apply. mode and char_target are optional: when
        left None they keep whatever this session already has, so a caller that
        only flips the toggle or the fixed size (the v1 footer path) doesn't
        have to know the mode. Pass them to switch between fixed and adaptive
        or change the adaptive width. A finished session (index at the end)
        keeps its position; there is no chunk to snap to."""
        self.chunking_enabled = enabled
        self.chunk_size = size
        if mode is not None:
            self.chunk_mode = mode
        if char_target is not None:
            self.chunk_char_target = char_target
        self._rebuild_chunks()
        if self.index < self.total_words:
            self.index = self._chunk_bounds_of_word[self.index][0]