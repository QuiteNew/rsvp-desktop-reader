import pytest

from core.models import Transcript, Bookmark


# Bookmark

def test_bookmark_defaults():
    b = Bookmark(index=5)
    assert b.index == 5
    assert b.snippet == ""
    assert b.created_at == ""
    assert b.label == ""

def test_bookmark_stores_given_values():
    b = Bookmark(index=3, snippet="the quick brown", created_at="2020-01-01T00:00:00+00:00", label="Intro")
    assert b.index == 3
    assert b.snippet == "the quick brown"
    assert b.created_at == "2020-01-01T00:00:00+00:00"
    assert b.label == "Intro"

def test_bookmark_requires_an_index():
    with pytest.raises(TypeError):
        Bookmark()


# Transcript

def test_transcript_requires_id_title_and_space():
    with pytest.raises(TypeError):
        Transcript()

def test_transcript_defaults():
    t = Transcript(id=1, title="T", space="General")
    assert t.raw_text == ""
    assert t.wpm == 300
    assert t.position == 0
    assert t.font_color == "#FFFFFF"
    assert t.highlight_color == "#E74C3C"
    assert t.background_color == "#1E1E1E"
    assert t.font_size == 32
    assert t.is_paused is False
    assert t.draft_text == ""
    assert t.is_stopped is False
    assert t.font_color_is_default is True
    assert t.highlight_color_is_default is True
    assert t.background_color_is_default is True
    assert t.times_read == 0
    assert t.total_words_read == 0
    assert t.total_time_spent_seconds == 0
    assert t.pre_normalize_text == ""
    assert t.normalized_text == ""
    assert t.bookmarks == []

def test_transcript_stores_given_values():
    t = Transcript(id=2, title="Doc", space="Work", wpm=450, position=12, font_size=40)
    assert t.id == 2
    assert t.title == "Doc"
    assert t.space == "Work"
    assert t.wpm == 450
    assert t.position == 12
    assert t.font_size == 40

def test_transcript_bookmarks_default_is_an_empty_list():
    assert Transcript(id=1, title="T", space="General").bookmarks == []

def test_transcript_bookmarks_are_not_shared_between_instances():
    # The field(default_factory=list) guard: mutating one transcript's
    # bookmarks must not leak into another's (the classic mutable-default
    # trap).
    t1 = Transcript(id=1, title="A", space="General")
    t2 = Transcript(id=2, title="B", space="General")
    t1.bookmarks.append(Bookmark(index=0))
    assert len(t1.bookmarks) == 1
    assert t2.bookmarks == []