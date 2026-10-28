"""Which transcript to open when the app starts.

The app remembers the transcript that is open in the reader (see
SettingsStore.last_transcript_id). At the next launch it opens that one again,
unless the "Reopen the last transcript at launch" setting is off or the
transcript is gone. Kept out of the GUI so it can be tested without a window."""


def transcript_to_reopen(enabled: bool, last_transcript_id, transcripts):
    """The transcript to open at launch, or None to start with none open.

    None when the setting is off, when nothing was open last time, or when that
    transcript no longer exists (it was deleted, or the data was replaced by an
    import). The transcript is found wherever it is, in any space: the app kept
    it open across a switch of space, so it comes back the same way."""
    if not enabled or last_transcript_id is None:
        return None
    return next((t for t in transcripts if t.id == last_transcript_id), None)
