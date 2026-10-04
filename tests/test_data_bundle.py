import json
import pytest

from core import data_bundle
from core.models import Bookmark
from core.settings_store import SettingsStore
from core.transcript_store import TranscriptStore


@pytest.fixture
def source_stores(tmp_path):
    """A transcript store and settings store in throwaway folders, used as
    the "export" side of a round trip."""
    ts = TranscriptStore(data_directory=str(tmp_path / "src_data"))
    ss = SettingsStore(settings_directory=str(tmp_path / "src_settings"))
    return ts, ss


def _round_trip_bundle(ts, ss):
    """Build a bundle, serialize it the way gui/app.py would (json.dumps),
    and parse it back, so the test exercises the real JSON hop a bookmark
    makes between machines, not just the in-memory dict."""
    text = json.dumps(data_bundle.build_bundle(ts, ss))
    return data_bundle.parse_bundle(text)


def test_bundle_replace_preserves_bookmarks(tmp_path, source_stores):
    source_ts, source_ss = source_stores
    t = source_ts.add_transcript("Doc", "General")
    source_ts.set_transcript_text(t.id, "one two three four five")
    source_ts.add_bookmark(t.id, 1, "two")
    source_ts.add_bookmark(t.id, 3, "four")

    bundle = _round_trip_bundle(source_ts, source_ss)

    dest_ts = TranscriptStore(data_directory=str(tmp_path / "dest_data"))
    dest_ss = SettingsStore(settings_directory=str(tmp_path / "dest_settings"))
    data_bundle.apply_bundle_replace(bundle, dest_ts, dest_ss)

    imported = dest_ts.transcripts[0]
    assert [b.index for b in imported.bookmarks] == [1, 3]
    assert imported.bookmarks[0].snippet == "two"
    # Rebuilt into real Bookmark objects on the far side, not plain dicts.
    assert all(isinstance(b, Bookmark) for b in imported.bookmarks)


def test_bundle_expand_preserves_bookmarks(tmp_path, source_stores):
    source_ts, source_ss = source_stores
    t = source_ts.add_transcript("Doc", "General")
    source_ts.add_bookmark(t.id, 2, "snippet")

    bundle = _round_trip_bundle(source_ts, source_ss)

    dest_ts = TranscriptStore(data_directory=str(tmp_path / "dest_expand"))
    data_bundle.apply_bundle_expand(bundle, dest_ts)

    imported = dest_ts.transcripts[-1]
    assert [b.index for b in imported.bookmarks] == [2]
    assert isinstance(imported.bookmarks[0], Bookmark)