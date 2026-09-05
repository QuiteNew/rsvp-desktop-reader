from dataclasses import dataclass


@dataclass
class Transcript:
    """A single saved transcript entry."""
    id: int
    title: str
    space: str
    raw_text: str = ""
    wpm: int = 300
    position: int = 0
    font_color: str = "#FFFFFF"
    highlight_color: str = "#E74C3C"
    background_color: str = "#1E1E1E"