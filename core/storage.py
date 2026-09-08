import json
from pathlib import Path
from dataclasses import asdict

from core.models import Transcript

DEFAULT_DATA_DIR = Path.home() / ".rsvp_reader"


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
        transcripts = [Transcript(**t) for t in data["transcripts"]]
        return {
            "next_id": data["next_id"],
            "current_space_index": data["current_space_index"],
            "spaces": data["spaces"],
            "transcripts": transcripts,
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        return None