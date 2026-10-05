from dataclasses import dataclass, field


@dataclass
class Bookmark:
    """A deliberately saved reading position within a transcript, created
    from the reader (the Bookmark button or the B shortcut). Unlike
    Transcript.position, which just tracks where you last were and moves
    with every word, a bookmark is a fixed return point, and a transcript
    can hold several.

    index is the word index it points at. snippet is a short piece of the
    surrounding text, captured when the bookmark is created, so it's
    recognizable in a list without re-reading the transcript. created_at is
    an ISO-8601 timestamp, kept for later display/sorting. label is an
    optional name the user gives the bookmark (see
    TranscriptStore.set_bookmark_label); when it's empty the list falls
    back to showing the snippet, so old bookmarks and never-renamed ones
    keep working unchanged. Bookmarks are identified by their index: a
    transcript holds at most one per word position (see
    TranscriptStore.add_bookmark / remove_bookmark)."""
    index: int
    snippet: str = ""
    created_at: str = ""
    label: str = ""


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

    # Undo information for the edit view's Normalize button (see
    # core/normalizer.py's toggle_normalization()). pre_normalize_text is
    # the text as it was before normalizing, and normalized_text is what
    # normalizing produced. Both are empty when there's nothing to
    # revert, which is also the right value for old save files, so no
    # backfill is needed.
    pre_normalize_text: str = ""
    normalized_text: str = ""

    # Deliberately saved reading positions within this transcript (see the
    # Bookmark dataclass above and TranscriptStore.add_bookmark). Kept
    # sorted by index. Written to disk as plain dicts by asdict() and
    # rebuilt into Bookmark objects on load by core/storage.py's
    # parse_data(). Old save files from before bookmarks existed have no
    # key for this, which default_factory handles as an empty list, so no
    # explicit backfill is needed (unlike the color flags above).
    bookmarks: list[Bookmark] = field(default_factory=list)