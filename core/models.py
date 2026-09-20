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
    # Whether each reading color is still tracking the app-wide Light/Dark
    # default rather than something the user picked by hand -- see
    # TranscriptStore.resync_default_reading_colors() and gui/app.py.
    # Defaults to True here (a freshly-constructed transcript is always
    # seeded from a default) -- core/storage.py explicitly backfills False
    # when loading a save file from before this field existed, so an
    # already-established transcript's colors are never silently rewritten
    # by this feature.
    font_color_is_default: bool = True
    highlight_color_is_default: bool = True
    background_color_is_default: bool = True