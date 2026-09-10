from core.models import Transcript
from core.storage import save_state, load_state, DEFAULT_DATA_DIR

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
    ) -> Transcript:
        transcript = Transcript(
            id=self._next_id, title=title, space=space,
            wpm=wpm, font_color=font_color,
            highlight_color=highlight_color, background_color=background_color,
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
        t = self._find_transcript(transcript_id)
        if t:
            t.position = position
            self._save()

    def set_transcript_paused(self, transcript_id: int, is_paused: bool) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.is_paused = is_paused
            self._save()

    def set_transcript_wpm(self, transcript_id: int, wpm: int) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.wpm = wpm
            self._save()

    def set_transcript_font_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.font_color = color
            self._save()

    def set_transcript_highlight_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.highlight_color = color
            self._save()

    def set_transcript_background_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.background_color = color
            self._save()

    def set_transcript_draft_text(self, transcript_id: int, draft_text: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.draft_text = draft_text
            self._save()

    def delete_transcript(self, transcript_id: int) -> None:
        """Permanently remove a transcript and persist the change immediately."""
        self._transcripts = [t for t in self._transcripts if t.id != transcript_id]
        self._save()