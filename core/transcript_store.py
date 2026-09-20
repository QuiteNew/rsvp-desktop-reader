import time

from core.models import Transcript
from core.storage import save_state, load_state, DEFAULT_DATA_DIR, LIVE_SAVE_INTERVAL_SECONDS

DEFAULT_SPACE = "General"


class TranscriptStore:
    """In-memory store for spaces and transcripts, backed by a JSON file
    in a configurable directory."""

    def __init__(self, data_directory: str | None = None):
        self._data_directory = data_directory or str(DEFAULT_DATA_DIR)

        loaded = load_state(self._data_directory)
        if loaded:
            self._spaces = loaded["spaces"]
            self._current_space_index = min(loaded["current_space_index"], len(self._spaces) - 1)
            self._transcripts = loaded["transcripts"]
            self._next_id = loaded["next_id"]
        else:
            self._spaces: list[str] = [DEFAULT_SPACE]
            self._current_space_index = 0
            self._transcripts: list[Transcript] = []
            self._next_id = 1

        # 0.0 rather than time.monotonic() at startup -- guarantees the very
        # first throttled write after launch always goes straight through
        # instead of waiting out a throttle window against a startup time
        # it has no real relationship to.
        self._last_live_save = 0.0

    def _save(self) -> None:
        save_state(self._data_directory, self._spaces, self._current_space_index, self._transcripts, self._next_id)

    def set_data_directory(self, directory: str) -> None:
        self._data_directory = directory
        self._save()

    @property
    def spaces(self) -> list[str]:
        return list(self._spaces)

    @property
    def default_space(self) -> str:
        return self._spaces[0]

    @property
    def current_space(self) -> str:
        return self._spaces[self._current_space_index]

    @property
    def transcripts(self) -> list[Transcript]:
        return list(self._transcripts)

    @property
    def transcripts_in_current_space(self) -> list[Transcript]:
        return [t for t in self._transcripts if t.space == self.current_space]

    def add_space(self, name: str) -> str:
        name = name.strip()
        if name and name not in self._spaces:
            self._spaces.append(name)
            self._current_space_index = len(self._spaces) - 1
            self._save()
        return self.current_space

    def switch_to_space(self, name: str) -> str:
        if name in self._spaces:
            self._current_space_index = self._spaces.index(name)
            self._save()
        return self.current_space

    def add_transcript(
        self,
        title: str,
        space: str,
        wpm: int = 300,
        font_color: str = "#FFFFFF",
        highlight_color: str = "#E74C3C",
        background_color: str = "#1E1E1E",
        font_size: int = 32,
    ) -> Transcript:
        transcript = Transcript(
            id=self._next_id, title=title, space=space,
            wpm=wpm, font_color=font_color,
            highlight_color=highlight_color, background_color=background_color,
            font_size=font_size,
        )
        self._next_id += 1
        self._transcripts.append(transcript)
        self._save()
        return transcript

    def _find_transcript(self, transcript_id: int) -> Transcript | None:
        for t in self._transcripts:
            if t.id == transcript_id:
                return t
        return None

    def set_transcript_text(self, transcript_id: int, raw_text: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.raw_text = raw_text
            self._save()

    def set_transcript_position(self, transcript_id: int, position: int) -> None:
        """Update the transcript's position and persist it -- but the disk
        write itself is throttled (see LIVE_SAVE_INTERVAL_SECONDS in
        core/storage.py), since this is called on every word during
        playback. The in-memory value is always current regardless; call
        flush() to force an immediate write of whatever's still pending."""
        t = self._find_transcript(transcript_id)
        if t:
            t.position = position
            self._save_throttled()

    def _save_throttled(self) -> None:
        now = time.monotonic()
        if now - self._last_live_save >= LIVE_SAVE_INTERVAL_SECONDS:
            self._last_live_save = now
            self._save()

    def flush(self) -> None:
        """Force an immediate save, bypassing the live-update throttle.
        Every OTHER setter in this class already calls _save() directly
        and unconditionally (pause, stop, skip's pause-toggle, colors,
        etc.), so those already double as safe checkpoints for whatever
        position/WPM was last recorded in memory -- this is only needed to
        guarantee a throttled-but-not-yet-written update actually reaches
        disk when nothing else is going to save afterward. Called from
        gui/app.py on app close."""
        self._last_live_save = time.monotonic()
        self._save()

    def set_transcript_paused(self, transcript_id: int, is_paused: bool) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.is_paused = is_paused
            self._save()

    def set_transcript_wpm(self, transcript_id: int, wpm: int) -> None:
        """Update the transcript's WPM and persist it -- throttled the same
        way set_transcript_position() is, since this is the footer WPM
        slider's live drag callback and can fire dozens of times across a
        single drag. This is currently WPM's only caller, so no separate
        discrete/unthrottled variant is needed the way skip_word_count
        needed one in SettingsStore (see set_skip_word_count_live() there)."""
        t = self._find_transcript(transcript_id)
        if t:
            t.wpm = wpm
            self._save_throttled()

    def set_transcript_font_color(self, transcript_id: int, color: str) -> None:
        # Called only from the footer's own color picker -- a genuine
        # manual change, so it retires this transcript's font color from
        # theme-tracking. Only clears the flag if the color actually
        # changed, so re-picking the same color twice doesn't accidentally
        # freeze it (see resync_default_reading_colors()).
        t = self._find_transcript(transcript_id)
        if t:
            if color != t.font_color:
                t.font_color_is_default = False
            t.font_color = color
            self._save()

    def set_transcript_highlight_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            if color != t.highlight_color:
                t.highlight_color_is_default = False
            t.highlight_color = color
            self._save()

    def set_transcript_background_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            if color != t.background_color:
                t.background_color_is_default = False
            t.background_color = color
            self._save()

    def resync_default_reading_colors(self, font_color: str, highlight_color: str, background_color: str) -> None:
        """Update every transcript whose reading colors are still tracking
        the app-wide default (font_color_is_default etc. -- see
        core/models.py) to the given values, leaving any transcript with
        its own deliberately-picked color untouched. Called once at app
        startup (see gui/app.py) with whichever color set matches the
        CURRENT theme -- the same "takes effect on next launch" timing the
        rest of the theme system already uses, not a live update."""
        changed = False
        for t in self._transcripts:
            if t.font_color_is_default and t.font_color != font_color:
                t.font_color = font_color
                changed = True
            if t.highlight_color_is_default and t.highlight_color != highlight_color:
                t.highlight_color = highlight_color
                changed = True
            if t.background_color_is_default and t.background_color != background_color:
                t.background_color = background_color
                changed = True
        if changed:
            self._save()

    def set_transcript_font_size(self, transcript_id: int, font_size: int) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.font_size = font_size
            self._save()

    def set_transcript_draft_text(self, transcript_id: int, draft_text: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.draft_text = draft_text
            self._save()

    def set_transcript_stopped(self, transcript_id: int, is_stopped: bool) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.is_stopped = is_stopped
            self._save()

    def delete_transcript(self, transcript_id: int) -> None:
        self._transcripts = [t for t in self._transcripts if t.id != transcript_id]
        self._save()