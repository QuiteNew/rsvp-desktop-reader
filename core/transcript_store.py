from core.models import Transcript

DEFAULT_SPACE = "General"


class TranscriptStore:
    """In-memory store for spaces and transcripts."""

    def __init__(self):
        self._spaces: list[str] = [DEFAULT_SPACE]
        self._current_space_index = 0
        self._transcripts: list[Transcript] = []
        self._next_id = 1

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
        return self.current_space

    def switch_to_space(self, name: str) -> str:
        if name in self._spaces:
            self._current_space_index = self._spaces.index(name)
        return self.current_space

    def add_transcript(self, title: str, space: str) -> Transcript:
        transcript = Transcript(id=self._next_id, title=title, space=space)
        self._next_id += 1
        self._transcripts.append(transcript)
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

    def set_transcript_position(self, transcript_id: int, position: int) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.position = position

    def set_transcript_paused(self, transcript_id: int, is_paused: bool) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.is_paused = is_paused

    def set_transcript_wpm(self, transcript_id: int, wpm: int) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.wpm = wpm

    def set_transcript_font_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.font_color = color

    def set_transcript_highlight_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.highlight_color = color

    def set_transcript_background_color(self, transcript_id: int, color: str) -> None:
        t = self._find_transcript(transcript_id)
        if t:
            t.background_color = color