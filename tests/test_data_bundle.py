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


# build_bundle

def test_build_bundle_has_format_data_and_settings(source_stores):
    source_ts, source_ss = source_stores
    bundle = data_bundle.build_bundle(source_ts, source_ss)
    assert bundle["bundle_format"] == data_bundle.BUNDLE_FORMAT_VERSION
    assert isinstance(bundle["data"], dict)
    assert isinstance(bundle["settings"], dict)

def test_build_bundle_excludes_data_directory_from_settings(source_stores):
    # data_directory is an OS-specific path and must never travel in a bundle.
    source_ts, source_ss = source_stores
    source_ss.set_data_directory("/some/machine/specific/path")
    bundle = data_bundle.build_bundle(source_ts, source_ss)
    assert "data_directory" not in bundle["settings"]

def test_build_bundle_captures_transcripts_and_spaces(source_stores):
    source_ts, source_ss = source_stores
    source_ts.add_space("Work")
    source_ts.add_transcript("A", "General")
    source_ts.add_transcript("B", "Work")

    bundle = data_bundle.build_bundle(source_ts, source_ss)
    assert "Work" in bundle["data"]["spaces"]
    titles = {t["title"] for t in bundle["data"]["transcripts"]}
    assert titles == {"A", "B"}


# parse_bundle: the happy path

def test_parse_bundle_round_trip_returns_data_and_settings(source_stores):
    source_ts, source_ss = source_stores
    source_ss.set_window_size(1234, 777)
    result = _round_trip_bundle(source_ts, source_ss)
    assert "data" in result and "settings" in result
    assert result["settings"]["window_width"] == 1234

def test_parse_bundle_returns_real_transcript_objects(source_stores):
    source_ts, source_ss = source_stores
    source_ts.add_transcript("Doc", "General")
    result = _round_trip_bundle(source_ts, source_ss)
    from core.models import Transcript
    assert isinstance(result["data"]["transcripts"][0], Transcript)


# parse_bundle: every rejection path raises BundleFormatError

def test_parse_bundle_rejects_invalid_json():
    with pytest.raises(data_bundle.BundleFormatError):
        data_bundle.parse_bundle("{ not valid json")

def test_parse_bundle_rejects_non_dict_json():
    with pytest.raises(data_bundle.BundleFormatError):
        data_bundle.parse_bundle(json.dumps([1, 2, 3]))

def test_parse_bundle_rejects_missing_bundle_format():
    with pytest.raises(data_bundle.BundleFormatError):
        data_bundle.parse_bundle(json.dumps({"data": {}, "settings": {}}))

def test_parse_bundle_rejects_unknown_version():
    with pytest.raises(data_bundle.BundleFormatError):
        data_bundle.parse_bundle(json.dumps({
            "bundle_format": data_bundle.BUNDLE_FORMAT_VERSION + 99,
            "data": {}, "settings": {},
        }))

def test_parse_bundle_rejects_missing_data_section():
    with pytest.raises(data_bundle.BundleFormatError):
        data_bundle.parse_bundle(json.dumps({
            "bundle_format": data_bundle.BUNDLE_FORMAT_VERSION,
            "settings": {},
        }))

def test_parse_bundle_rejects_missing_settings_section(source_stores):
    source_ts, source_ss = source_stores
    good_data = data_bundle.build_bundle(source_ts, source_ss)["data"]
    with pytest.raises(data_bundle.BundleFormatError):
        data_bundle.parse_bundle(json.dumps({
            "bundle_format": data_bundle.BUNDLE_FORMAT_VERSION,
            "data": good_data,
        }))

def test_parse_bundle_rejects_malformed_data():
    # bundle_format and the two sections are the right shape, but the data
    # section isn't a valid save (parse_data returns None).
    with pytest.raises(data_bundle.BundleFormatError):
        data_bundle.parse_bundle(json.dumps({
            "bundle_format": data_bundle.BUNDLE_FORMAT_VERSION,
            "data": {"not": "a valid save"},
            "settings": {},
        }))


# apply_bundle_replace

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

def test_apply_bundle_replace_overwrites_transcripts_and_spaces(tmp_path, source_stores):
    source_ts, source_ss = source_stores
    source_ts.add_space("Work")
    source_ts.add_transcript("A", "General")
    source_ts.add_transcript("B", "Work")

    bundle = _round_trip_bundle(source_ts, source_ss)

    dest_ts = TranscriptStore(data_directory=str(tmp_path / "dest_data"))
    dest_ss = SettingsStore(settings_directory=str(tmp_path / "dest_settings"))
    dest_ts.add_transcript("Old", "General")
    data_bundle.apply_bundle_replace(bundle, dest_ts, dest_ss)

    assert dest_ts.spaces == ["General", "Work"]
    titles = {t.title for t in dest_ts.transcripts}
    assert titles == {"A", "B"}  # the dest's own "Old" is gone

def test_apply_bundle_replace_replaces_settings(tmp_path, source_stores):
    source_ts, source_ss = source_stores
    source_ss.set_window_size(1280, 800)

    bundle = _round_trip_bundle(source_ts, source_ss)

    dest_ts = TranscriptStore(data_directory=str(tmp_path / "dest_data"))
    dest_ss = SettingsStore(settings_directory=str(tmp_path / "dest_settings"))
    data_bundle.apply_bundle_replace(bundle, dest_ts, dest_ss)

    assert dest_ss.window_width == 1280
    assert dest_ss.window_height == 800

def test_apply_bundle_replace_keeps_the_importing_machines_data_directory(tmp_path, source_stores):
    # The cross-machine guarantee: a bundle made on one machine must not
    # drag its data_directory onto the importing machine.
    source_ts, source_ss = source_stores
    source_ss.set_data_directory("/sender/only/path")

    bundle = _round_trip_bundle(source_ts, source_ss)

    dest_ts = TranscriptStore(data_directory=str(tmp_path / "dest_data"))
    dest_ss = SettingsStore(settings_directory=str(tmp_path / "dest_settings"))
    dest_ss.set_data_directory("/importer/own/path")
    data_bundle.apply_bundle_replace(bundle, dest_ts, dest_ss)

    assert dest_ss.data_directory == "/importer/own/path"

def test_apply_bundle_replace_persists_to_disk(tmp_path, source_stores):
    source_ts, source_ss = source_stores
    source_ts.add_transcript("Imported", "General")

    bundle = _round_trip_bundle(source_ts, source_ss)

    dest_data_dir = str(tmp_path / "dest_data")
    dest_ts = TranscriptStore(data_directory=dest_data_dir)
    dest_ss = SettingsStore(settings_directory=str(tmp_path / "dest_settings"))
    data_bundle.apply_bundle_replace(bundle, dest_ts, dest_ss)

    # A fresh store reading the same directory sees the imported data, so
    # the import actually hit disk, not just memory.
    reloaded = TranscriptStore(data_directory=dest_data_dir)
    assert [t.title for t in reloaded.transcripts] == ["Imported"]


# apply_bundle_expand

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

def test_apply_bundle_expand_adds_to_existing_transcripts(tmp_path, source_stores):
    source_ts, source_ss = source_stores
    source_ts.add_transcript("Incoming", "General")

    bundle = _round_trip_bundle(source_ts, source_ss)

    dest_ts = TranscriptStore(data_directory=str(tmp_path / "dest_expand"))
    dest_ts.add_transcript("Kept", "General")
    data_bundle.apply_bundle_expand(bundle, dest_ts)

    titles = {t.title for t in dest_ts.transcripts}
    assert titles == {"Kept", "Incoming"}  # existing kept, incoming added

def test_apply_bundle_expand_merges_new_spaces(tmp_path, source_stores):
    source_ts, source_ss = source_stores
    source_ts.add_space("Work")  # a space the destination doesn't have

    bundle = _round_trip_bundle(source_ts, source_ss)

    dest_ts = TranscriptStore(data_directory=str(tmp_path / "dest_expand"))
    data_bundle.apply_bundle_expand(bundle, dest_ts)

    assert "Work" in dest_ts.spaces