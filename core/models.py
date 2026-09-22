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

    # Running totals across every finished reading session for this
    # transcript -- updated by TranscriptStore.add_session_stats(), called
    # once a session actually ends (stopped, finished, switched away from,
    # or the app closes mid-read; see gui/components/reader_display.py).
    # These never reflect a session that's still in progress -- only what's
    # already been finalized.
    #
    # times_read only increments if a flushed session had some minimum
    # real active time in it (see add_session_stats()), so opening a
    # transcript and immediately clicking away doesn't count as a read.
    #
    # total_words_read counts only words the reader actually auto-advanced
    # through at the RSVP pace -- skipping forward with the >> button does
    # NOT add to this, so it can't be inflated by skipping to the end
    # without reading. Skipping backward to reread also never subtracts.
    #
    # total_time_spent_seconds is active reading time only -- the clock
    # stops while paused, so time spent paused (or sitting on a finished
    # transcript) is never counted. Whole seconds; no need for finer
    # precision here.
    #
    # Unlike font_color_is_default/highlight_color_is_default/
    # background_color_is_default above, these three do NOT need a
    # core/storage.py backfill entry: a save file written before this
    # feature existed simply won't have these keys, and core/storage.py's
    # parse_data() already falls back to a dataclass's own default when a
    # key is missing -- which is 0 here, the correct value for a
    # pre-existing transcript that's never had a session recorded against
    # it. The color flags needed an explicit backfill only because their
    # correct "missing" value (False) differs from their dataclass default
    # (True); there's no such mismatch here.
    times_read: int = 0
    total_words_read: int = 0
    total_time_spent_seconds: int = 0