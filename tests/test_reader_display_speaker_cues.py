"""Speaker cues in the reader widget (gui/components/reader_display.py): the
name tag above the word, the flash at a new speaker, and the chime.

Like test_reader_letter_spacing.py, these build a reader of their own on a small
window rather than the whole app, since the reader is all they need; the app's
wiring has its own tests. Reading is moved on by calling _advance(), the very
method the reader's own timer calls, on a paused reader, so nothing here
depends on how fast the machine is. The chime player is a stand-in that records
what it was asked to play; the real player is tested in test_chime_player.py.

Turns in TEXT, by word number: Ann 0-2, Bob 3-5, Ann 6-8, Bob 9-11."""

import pytest

from core.chime import CHANGE_PATTERN, SPEAKER_PATTERNS
from core.colors import blend_colors
from core.reader import ReaderSession
from tk_helpers import cancel_pending_afters, settle

TEXT = "Ann: hi there\nBob: hello you\nAnn: and so\nBob: we go"
FONT = "#3B2E27"
HIGHLIGHT = "#C0392B"  # not the app's default highlight, so a test can tell them apart
BACKGROUND = "#F6EFE3"


class FakePlayer:
    def __init__(self, available=True):
        self.available = available
        self.played = []
        self.prepared = []

    def play(self, notes, style, wait=False):
        self.played.append((tuple(notes), style))
        return True

    def prepare(self, style):
        self.prepared.append(style)


@pytest.fixture
def root(shown_root):
    shown_root.geometry("700x420+0+0")
    shown_root.callback_errors = []
    shown_root.report_callback_exception = lambda *details: shown_root.callback_errors.append(details)
    yield shown_root
    assert shown_root.callback_errors == []


@pytest.fixture
def reader(root):
    from gui.components.reader_display import ReaderDisplay

    display = ReaderDisplay(root)
    display.pack(fill="both", expand=True)
    display.set_colors(FONT, HIGHLIGHT, BACKGROUND)
    settle(root, 100)
    yield display
    cancel_pending_afters(display)
    display.destroy()
    settle(root, 50)


def _load(reader, text=TEXT, cues=True, custom=None, **kwargs):
    """Open a paused session, so the reader's own timer never runs."""
    session = ReaderSession(text, wpm=300, speaker_cues_enabled=cues, speaker_custom=custom, **kwargs)
    reader.load_session(session, start_paused=True)
    settle(reader, 100)
    return session


def _step(reader, times=1):
    """Read on, the way the reader's timer does."""
    for _ in range(times):
        reader._advance()
    settle(reader, 20)


def _tag(reader):
    """The name tag's text, or None when it isn't on screen."""
    return reader.speaker_tag.cget("text") if reader.speaker_tag.winfo_ismapped() else None


def _background(reader):
    return reader.word_row.cget("fg_color")


def _dim():
    return blend_colors(FONT, BACKGROUND, 0.55)


def _warm():
    return blend_colors(BACKGROUND, HIGHLIGHT, 0.18)


# ---- The name tag ----

def test_the_tag_shows_the_first_speaker(reader):
    _load(reader)
    assert _tag(reader) == "Ann"

def test_the_tag_follows_the_reading(reader):
    _load(reader)
    seen = []
    for _ in range(12):
        seen.append(_tag(reader))
        _step(reader)
    assert seen == ["Ann"] * 3 + ["Bob"] * 3 + ["Ann"] * 3 + ["Bob"] * 3

def test_the_tag_is_dimmed_like_the_ribbon(reader):
    _load(reader)
    assert reader.speaker_tag.cget("text_color") == _dim() == blend_colors(FONT, BACKGROUND, reader.PERIPHERAL_CONTEXT_DIM)

def test_the_tag_sits_centred_above_the_word_clear_of_the_guide_marks(reader, root):
    _load(reader)
    reader.toggle_pause()  # running, so the guide marks are on screen
    settle(root, 50)
    try:
        tag, focus, mark = reader.speaker_tag, reader.focus_label, reader.guide_mark_above
        assert mark.winfo_ismapped()
        tag_middle = tag.winfo_rootx() + tag.winfo_width() / 2
        focus_middle = focus.winfo_rootx() + focus.winfo_width() / 2
        assert abs(tag_middle - focus_middle) <= 1
        # At least 8 px clear of the top of the guide mark (a pixel of
        # rounding allowed), pinned as a plain number.
        assert reader.SPEAKER_TAG_BOTTOM_MARGIN_PX == 8
        tag_bottom = tag.winfo_rooty() + tag.winfo_height()
        assert tag_bottom <= mark.winfo_rooty() - 8 + 1
        assert tag.winfo_rooty() >= reader.word_row.winfo_rooty()
    finally:
        reader.toggle_pause()

def test_in_a_short_window_the_tag_stays_inside_the_top_edge(reader, root):
    root.geometry("700x110+0+0")
    reader.set_font_size(40)
    _load(reader)
    settle(root, 100)
    assert reader.SPEAKER_TAG_MIN_TOP_PX == 4
    # It would go above the top edge if it kept its distance from the marks.
    assert reader._tag_y == 4 + reader.speaker_tag.winfo_reqheight() / 2
    assert reader.speaker_tag.winfo_rooty() >= reader.word_row.winfo_rooty() + 4 - 1

def test_the_tag_stays_while_paused_and_while_reading(reader, root):
    _load(reader)
    assert _tag(reader) == "Ann"
    reader.toggle_pause()
    settle(root, 30)
    try:
        assert _tag(reader) == "Ann"
    finally:
        reader.toggle_pause()

def test_the_tag_is_half_the_word_size(reader):
    _load(reader)
    reader.set_font_size(48)
    settle(reader, 30)
    assert reader.speaker_tag_font.cget("size") == max(8, round(reader.word_font.cget("size") * 0.5))

def test_no_tag_before_the_first_speaker(reader):
    _load(reader, "Welcome back\nAnn: hi\nBob: hey\nAnn: bye\nBob: ok")
    assert _tag(reader) is None
    _step(reader, 2)
    assert _tag(reader) == "Ann"

def test_no_tag_for_a_change_with_no_name(reader):
    _load(reader, "Ann: hi there\n>> who is that\nAnn: me")
    _step(reader, 3)
    assert reader.session.current_speaker == ">>"
    assert _tag(reader) is None
    _step(reader, 4)  # ">> who is that" is four words
    assert _tag(reader) == "Ann"

def test_no_tag_with_speaker_cues_off(reader):
    _load(reader, cues=False)
    assert _tag(reader) is None

def test_no_tag_when_the_tag_is_switched_off_and_back_on(reader):
    _load(reader)
    reader.set_speaker_cue_options(False, True, "off", "bell")
    settle(reader, 20)
    assert _tag(reader) is None
    reader.set_speaker_cue_options(True, True, "off", "bell")
    settle(reader, 20)
    assert _tag(reader) == "Ann"

def test_no_tag_once_finished_or_stopped(reader):
    _load(reader)
    _step(reader, 12)
    assert reader.session.is_finished
    assert _tag(reader) is None
    _load(reader)
    assert _tag(reader) == "Ann"
    reader.stop()
    settle(reader, 20)
    assert _tag(reader) is None

def test_a_custom_list_names_the_speakers(reader):
    _load(reader, custom={"ann": "Interviewer", "bob": "Guest"})
    assert _tag(reader) == "Interviewer"
    _step(reader, 3)
    assert _tag(reader) == "Guest"

def test_skipping_and_jumping_move_the_tag(reader):
    _load(reader)
    reader.skip(4)
    settle(reader, 20)
    assert _tag(reader) == "Bob"
    reader.jump_to(7)
    settle(reader, 20)
    assert _tag(reader) == "Ann"

def test_the_tag_follows_new_colours(reader):
    _load(reader)
    reader.set_colors("#FFFFFF", "#E74C3C", "#1E1E1E")
    settle(reader, 20)
    assert reader.speaker_tag.cget("text_color") == blend_colors("#FFFFFF", "#1E1E1E", 0.55)

def test_the_tag_slides_with_a_pan(reader, root):
    long_word = "Pneumonoultramicroscopicsilicovolcanoconiosis" * 3
    _load(reader, f"Ann: {long_word}\nBob: b\nAnn: c\nBob: d")
    _step(reader)
    assert reader._scrollbar_visible
    # Scroll right, the way the scrollbar's arrow does: the long word's right
    # end spills off the reader, its left end doesn't.
    reader._handle_scroll("scroll", 5, "units")
    settle(root, 30)
    assert reader._pan_offset_px != 0
    tag, focus = reader.speaker_tag, reader.focus_label
    tag_middle = tag.winfo_rootx() + tag.winfo_width() / 2
    focus_middle = focus.winfo_rootx() + focus.winfo_width() / 2
    assert abs(tag_middle - focus_middle) <= 1


# ---- The flash ----

def test_reading_on_into_a_new_speaker_flashes(reader):
    _load(reader)
    _step(reader, 3)
    assert _background(reader) == _warm()
    assert reader.cget("fg_color") == _warm()
    assert reader.speaker_tag.cget("text_color") == HIGHLIGHT
    settle(reader, reader.SPEAKER_FLASH_MS + 150)
    assert _background(reader) == BACKGROUND
    assert reader.cget("fg_color") == BACKGROUND
    assert reader.speaker_tag.cget("text_color") == _dim()

def test_the_flash_lasts_about_a_third_of_a_second(reader):
    assert reader.SPEAKER_FLASH_MS == 330
    assert reader.SPEAKER_FLASH_WARMTH == 0.18
    _load(reader)
    _step(reader, 3)
    settle(reader, 200)
    assert _background(reader) == _warm()

def test_reading_on_within_a_turn_does_not_flash(reader):
    _load(reader)
    _step(reader)
    assert _background(reader) == BACKGROUND

def test_skipping_jumping_and_restarting_do_not_flash(reader):
    _load(reader)
    reader.skip(3)
    settle(reader, 20)
    assert _background(reader) == BACKGROUND
    reader.jump_to(6)
    settle(reader, 20)
    assert _background(reader) == BACKGROUND
    reader.restart()
    reader.toggle_pause()
    settle(reader, 20)
    assert _background(reader) == BACKGROUND

def test_no_flash_when_it_is_switched_off(reader):
    _load(reader)
    reader.set_speaker_cue_options(True, False, "off", "bell")
    _step(reader, 3)
    assert _background(reader) == BACKGROUND
    assert reader.speaker_tag.cget("text_color") == _dim()

def test_switching_the_flash_off_ends_one_under_way(reader):
    _load(reader)
    _step(reader, 3)
    reader.set_speaker_cue_options(True, False, "off", "bell")
    settle(reader, 20)
    assert _background(reader) == BACKGROUND

def test_no_flash_with_speaker_cues_off(reader):
    _load(reader, cues=False)
    _step(reader, 3)
    assert _background(reader) == BACKGROUND

def test_a_flash_still_shows_for_a_change_with_no_name(reader):
    _load(reader, "Ann: hi there\n>> who is that\nAnn: me")
    _step(reader, 3)
    assert _background(reader) == _warm()

def test_new_colours_during_a_flash_end_it_and_stay(reader):
    _load(reader)
    _step(reader, 3)
    reader.set_colors("#FFFFFF", "#E74C3C", "#1E1E1E")
    settle(reader, 20)
    # Over at once: the name is dimmed again in the new colours.
    assert reader.speaker_tag.cget("text_color") == blend_colors("#FFFFFF", "#1E1E1E", 0.55)
    settle(reader, reader.SPEAKER_FLASH_MS + 150)
    assert _background(reader) == "#1E1E1E"
    assert reader.cget("fg_color") == "#1E1E1E"

def test_stopping_during_a_flash_puts_the_background_back(reader):
    _load(reader)
    _step(reader, 3)
    reader.stop()
    settle(reader, 20)
    assert _background(reader) == BACKGROUND

def test_a_new_session_during_a_flash_puts_the_background_back(reader):
    _load(reader)
    _step(reader, 3)
    _load(reader)
    assert _background(reader) == BACKGROUND

def test_closing_during_a_flash_leaves_no_timer_behind(root):
    from gui.components.reader_display import ReaderDisplay

    display = ReaderDisplay(root)
    display.pack(fill="both", expand=True)
    display.set_colors(FONT, HIGHLIGHT, BACKGROUND)
    settle(root, 50)
    _load(display)
    _step(display, 3)
    flash = display._flash_after_id
    assert flash is not None
    display.destroy()
    # Tk's own list of waiting timers no longer has it. Left there, it would
    # fire into a widget that's gone and print an "invalid command name" error.
    assert flash not in root.tk.splitlist(root.tk.call("after", "info"))


# ---- The chime ----

def _with_player(reader, sound="per_speaker", style="bell", available=True):
    player = FakePlayer(available)
    reader.set_chime_player(player)
    reader.set_speaker_cue_options(True, True, sound, style)
    return player

def test_reading_on_into_a_new_speaker_plays_their_pattern(reader):
    player = _with_player(reader)
    _load(reader)
    _step(reader, 3)
    assert player.played == [(SPEAKER_PATTERNS[1], "bell")]

def test_each_speaker_keeps_their_pattern(reader):
    player = _with_player(reader, style="glass")
    clock = iter(range(0, 100_000, 5000))
    reader._now_ms = lambda: next(clock)
    _load(reader)
    _step(reader, 9)
    assert player.played == [
        (SPEAKER_PATTERNS[1], "glass"), (SPEAKER_PATTERNS[0], "glass"), (SPEAKER_PATTERNS[1], "glass"),
    ]

def test_one_chime_for_any_change(reader):
    player = _with_player(reader, sound="change")
    _load(reader)
    _step(reader, 3)
    assert player.played == [(CHANGE_PATTERN, "bell")]

def test_a_change_with_no_name_plays_the_change_chime(reader):
    player = _with_player(reader)
    _load(reader, "Ann: hi there\n>> who is that\nAnn: me")
    _step(reader, 3)
    assert player.played == [(CHANGE_PATTERN, "bell")]

def test_no_chime_with_the_sound_off(reader):
    player = _with_player(reader, sound="off")
    _load(reader)
    _step(reader, 3)
    assert player.played == []

def test_no_chime_where_sound_is_not_available(reader):
    player = _with_player(reader, available=False)
    _load(reader)
    _step(reader, 3)
    assert player.played == []

def test_no_player_at_all_is_fine(reader):
    reader.set_speaker_cue_options(True, True, "per_speaker", "bell")
    _load(reader)
    _step(reader, 3)
    assert _tag(reader) == "Bob"

def test_no_chime_within_a_turn_or_on_skipping(reader):
    player = _with_player(reader)
    _load(reader)
    _step(reader)
    reader.skip(2)
    reader.jump_to(6)
    reader.restart()
    reader.toggle_pause()
    settle(reader, 20)
    assert player.played == []

def test_a_chime_too_soon_after_the_last_is_skipped(reader):
    player = _with_player(reader)
    times = iter([1000, 1500, 2000])
    reader._now_ms = lambda: next(times)
    _load(reader, "Ann: a\nBob: b\nAnn: c\nBob: d")
    _step(reader, 2)   # Bob at 1000: plays a two-note chime, 570 ms long
    _step(reader, 2)   # Ann at 1500: past the 400 ms minimum, but Bob's is still ringing
    _step(reader, 2)   # Bob at 2000: plays
    assert player.played == [(SPEAKER_PATTERNS[1], "bell"), (SPEAKER_PATTERNS[1], "bell")]

def test_an_unknown_style_plays_the_default(reader):
    player = _with_player(reader, style="trumpet")
    _load(reader)
    _step(reader, 3)
    assert player.played == [(SPEAKER_PATTERNS[1], "bell")]

def test_the_chimes_are_prepared_when_there_is_something_to_play(reader):
    player = _with_player(reader, style="wood")
    player.prepared.clear()
    _load(reader)
    assert player.prepared == ["wood"]

@pytest.mark.parametrize("sound, text, cues", [
    ("off", TEXT, True),                  # no sound
    ("per_speaker", "plain words", True),  # no speakers
    ("per_speaker", TEXT, False),         # cues off
])
def test_nothing_is_prepared_when_nothing_would_play(reader, sound, text, cues):
    player = _with_player(reader, sound=sound)
    player.prepared.clear()
    _load(reader, text, cues=cues)
    assert player.prepared == []

def test_changing_the_style_prepares_the_new_one(reader):
    player = _with_player(reader)
    _load(reader)
    player.prepared.clear()
    reader.set_speaker_cue_options(True, True, "per_speaker", "soft")
    assert player.prepared == ["soft"]

def test_a_new_player_is_prepared_at_once(reader):
    reader.set_speaker_cue_options(True, True, "change", "glass")
    _load(reader)
    player = FakePlayer()
    reader.set_chime_player(player)
    assert player.prepared == ["glass"]


# ---- Turning speaker cues on and off while reading ----

def test_turning_cues_on_mid_reading_shows_the_tag_and_keeps_the_place(reader):
    positions = []
    reader.on_position_changed = positions.append
    _load(reader, cues=False)
    reader.jump_to(4)
    reader.set_speaker_cues(True)
    settle(reader, 20)
    assert reader.session.index == 4
    assert _tag(reader) == "Bob"

def test_turning_cues_on_reports_a_place_that_snapped_to_a_new_chunk(reader):
    positions = []
    reader.on_position_changed = positions.append
    # Grouped in fives, word 5 starts a chunk. With cues on, the chunks break
    # at the turns (0-2, 3-5, ...), so word 5 sits inside one and snaps to 3.
    _load(reader, cues=False, chunk_enabled=True, chunk_size=5)
    reader.jump_to(5)
    assert reader.session.index == 5
    reader.set_speaker_cues(True)
    assert reader.session.index == 3
    assert positions[-1] == 3

def test_turning_cues_off_hides_the_tag(reader):
    _load(reader)
    reader.set_speaker_cues(False)
    settle(reader, 20)
    assert _tag(reader) is None

def test_a_new_list_renames_the_tag_at_once(reader):
    _load(reader)
    reader.set_speaker_cues(True, {"ann": "Interviewer", "bob": "Guest"})
    settle(reader, 20)
    assert _tag(reader) == "Interviewer"

def test_turning_cues_on_regroups_chunks_at_the_turns(reader):
    _load(reader, cues=False, chunk_enabled=True, chunk_size=5)
    assert reader.session.chunk_ranges()[0] == (0, 5)
    reader.set_speaker_cues(True)
    assert reader.session.chunk_ranges()[:2] == [(0, 3), (3, 6)]

def test_turning_cues_on_prepares_the_chimes(reader):
    player = _with_player(reader)
    _load(reader, cues=False)
    player.prepared.clear()
    reader.set_speaker_cues(True)
    assert player.prepared == ["bell"]

def test_setting_cues_with_nothing_loaded_does_nothing(reader):
    reader.set_speaker_cues(True)
    assert reader.session is None
