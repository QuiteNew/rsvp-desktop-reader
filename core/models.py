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
    # Whether each color is still following the app's Light/Dark default,
    # or was picked by hand. See TranscriptStore.resync_default_reading_colors().
    # Old save files, from before this field existed, get backfilled to
    # False in core/storage.py, so existing transcripts keep their colors
    # instead of suddenly following the theme.
    font_color_is_default: bool = True
    highlight_color_is_default: bool = True
    background_color_is_default: bool = True

    # Lifetime stats for this transcript, updated by TranscriptStore.
    # add_session_stats() whenever a session ends. times_read only counts
    # sessions with some real active time, so opening and immediately
    # leaving doesn't count. total_words_read only counts words the
    # reader auto-advanced through, since skipping ahead doesn't inflate
    # it. total_time_spent_seconds is active time only; paused time
    # doesn't count. All three default to 0, which is also the right
    # value for old save files that predate this feature, so no backfill
    # is needed here the way the color flags above needed one.
    times_read: int = 0
    total_words_read: int = 0
    total_time_spent_seconds: int = 0