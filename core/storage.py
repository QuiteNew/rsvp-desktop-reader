import json
from pathlib import Path
from dataclasses import asdict

from core.models import Transcript

DEFAULT_DATA_DIR = Path.home() / ".rsvp_reader"

# Transcript fields added after this project already had saved data on
# disk. A save file written before a field existed simply won't have the
# key -- for these specific three, missing must resolve to False (already
# has its own colors), not the dataclass's own True default, so this
# migration never silently rewrites a color on a transcript that already
# existed. See core/models.py's Transcript and TranscriptStore.
_COLOR_DEFAULT_FLAG_FIELDS = ("font_color_is_default", "highlight_color_is_default", "background_color_is_default")

# Shared by TranscriptStore and SettingsStore for any setter that gets
# called from a live, high-frequency UI event -- continuous playback
# position, and dragging the WPM or skip-amount sliders -- rather than a
# discrete one-shot action (a click, a switch, Settings' Apply button).
# Those setters throttle their disk write to at most once per this
# interval instead of writing the full state on every single call; see
# each store's _save_throttled()/flush() for how.
LIVE_SAVE_INTERVAL_SECONDS = 1.0


def save_state(directory: str, spaces: list[str], current_space_index: int, transcripts: list[Transcript], next_id: int) -> None:
    """Write the store's full state to disk as JSON, inside the given directory."""
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    data_file = dir_path / "data.json"
    data = {
        "next_id": next_id,
        "current_space_index": current_space_index,
        "spaces": spaces,
        "transcripts": [asdict(t) for t in transcripts],
    }
    data_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_state(directory: str):
    """Read saved state from the given directory. Returns None if no valid
    save exists there yet, so the caller can fall back to sensible defaults."""
    data_file = Path(directory) / "data.json"
    if not data_file.exists():
        return None
    try:
        data = json.loads(data_file.read_text(encoding="utf-8"))
        for t in data["transcripts"]:
            for field_name in _COLOR_DEFAULT_FLAG_FIELDS:
                t.setdefault(field_name, False)
        transcripts = [Transcript(**t) for t in data["transcripts"]]
        return {
            "next_id": data["next_id"],
            "current_space_index": data["current_space_index"],
            "spaces": data["spaces"],
            "transcripts": transcripts,
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        return None