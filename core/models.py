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
    font_size: int = 32
    is_paused: bool = False
    draft_text: str = ""
    is_stopped: bool = False