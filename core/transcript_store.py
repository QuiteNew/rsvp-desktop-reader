from core.models import Transcript

DEFAULT_SPACE = "General"


class TranscriptStore:
    """In-memory store for spaces and transcripts.

    Backed by nothing but Python lists for now — this will be swapped for
    real persistence later, but callers (the GUI) go through this interface
    only, so nothing above it should need to change when that happens.
    """

    def __init__(self):
        self._spaces: list[str] = [DEFAULT_SPACE]
        self._transcripts: list[Transcript] = []
        self._next_id = 1

    @property
    def spaces(self) -> list[str]:
        return list(self._spaces)

    @property
    def default_space(self) -> str:
        """The space used when none is explicitly chosen — always the first one."""
        return self._spaces[0]

    @property
    def transcripts(self) -> list[Transcript]:
        return list(self._transcripts)

    def add_transcript(self, title: str, space: str) -> Transcript:
        transcript = Transcript(id=self._next_id, title=title, space=space)
        self._next_id += 1
        self._transcripts.append(transcript)
        return transcript


if __name__ == "__main__":
    store = TranscriptStore()
    print("Default space:", store.default_space)

    store.add_transcript("Lecture 3 notes", store.default_space)
    store.add_transcript("Podcast transcript", store.default_space)

    for t in store.transcripts:
        print(t)