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
        """The very first space that ever existed — a fixed anchor."""
        return self._spaces[0]

    @property
    def current_space(self) -> str:
        """Whichever space is currently active."""
        return self._spaces[self._current_space_index]

    @property
    def transcripts(self) -> list[Transcript]:
        return list(self._transcripts)

    @property
    def transcripts_in_current_space(self) -> list[Transcript]:
        return [t for t in self._transcripts if t.space == self.current_space]

    def add_space(self, name: str) -> str:
        """Add a new space and switch to it. Ignored if blank or a duplicate."""
        name = name.strip()
        if name and name not in self._spaces:
            self._spaces.append(name)
            self._current_space_index = len(self._spaces) - 1
        return self.current_space

    def next_space(self) -> str:
        """Cycle to the next space, wrapping around to the first."""
        self._current_space_index = (self._current_space_index + 1) % len(self._spaces)
        return self.current_space

    def previous_space(self) -> str:
        """Cycle to the previous space, wrapping around to the last."""
        self._current_space_index = (self._current_space_index - 1) % len(self._spaces)
        return self.current_space

    def add_transcript(self, title: str, space: str) -> Transcript:
        transcript = Transcript(id=self._next_id, title=title, space=space)
        self._next_id += 1
        self._transcripts.append(transcript)
        return transcript