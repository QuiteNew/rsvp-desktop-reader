import json
from pathlib import Path
from dataclasses import asdict

from core.models import Transcript

DATA_DIR = Path.home() / ".rsvp_reader"
DATA_FILE = DATA_DIR / "data.json"


def save_state(spaces: list[str], current_space_index: int, transcripts: list[Transcript], next_id: int) -> None:
    """Write the store's full state to disk as JSON."""
    DATA_DIR.mkdir(exist_ok=True)
    data = {
        "next_id": next_id,
        "current_space_index": current_space_index,
        "spaces": spaces,
        "transcripts": [asdict(t) for t in transcripts],
    }
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_state():
    """Read saved state from disk. Returns None if no valid save exists yet,
    so the caller can fall back to sensible defaults."""
    if not DATA_FILE.exists():
        return None
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        transcripts = [Transcript(**t) for t in data["transcripts"]]
        return {
            "next_id": data["next_id"],
            "current_space_index": data["current_space_index"],
            "spaces": data["spaces"],
            "transcripts": transcripts,
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        # Corrupted, or saved by an older version with different Transcript
        # fields — safer to start fresh than crash on launch
        return None