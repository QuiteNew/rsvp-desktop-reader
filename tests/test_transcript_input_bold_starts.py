"""Tests for the bold word starts button and look in the edit box
(gui/components/transcript_input.py).

These run against a real Tk, like test_reader_letter_spacing.py, with one hidden
root for the whole module. They cover the button, the tag laid over the text,
the font of that tag (including OpenDyslexic and a change of display scaling),
and where the "Nothing to change" label sits now that there are two buttons.

Typing into the box and having the bold follow along is step 4c and is tested
separately."""

import tkinter

import customtkinter as ctk
import pytest

from core.bold_starts import bold_ranges


@pytest.fixture(scope="module")
def root():
    try:
        window = ctk.CTk()
    except tkinter.TclError:
        pytest.skip("no display available for Tk")
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def make_box(root):
    """Builds edit boxes and destroys them again after the test."""
    from gui.components.transcript_input import TranscriptInput

    made = []

    def build(text="", **kwargs):
        box = TranscriptInput(root, on_submit=lambda t: None, initial_text=text, **kwargs)
        box.pack()
        root.update()
        made.append(box)
        return box

    yield build
    for box in made:
        box.destroy()


def shown_box(root, width=500, height=350, **kwargs):
    """An edit box in a real, mapped window of the given size. A hidden window
    never gets a size, so anything that measures where widgets sit needs this.
    Returns (window, box); the caller destroys the window."""
    from gui.components.transcript_input import TranscriptInput

    top = ctk.CTkToplevel(root)
    top.geometry(f"{width}x{height}")
    box = TranscriptInput(top, on_submit=lambda t: None, **kwargs)
    box.pack(fill="both", expand=True)
    top.update()
    assert box.start_button.winfo_width() > 1, "the window was not laid out"
    return top, box


def span(widget):
    """Left and right edge of a widget on screen."""
    return widget.winfo_rootx(), widget.winfo_rootx() + widget.winfo_width()


def bold_pieces(box):
    """The words' bold stretches as the widget really has them, read back out of
    the Text widget through the tag."""
    from gui.components.transcript_input import BOLD_TAG

    inner = box.textbox._textbox
    ranges = inner.tag_ranges(BOLD_TAG)
    return [inner.get(str(ranges[i]), str(ranges[i + 1])) for i in range(0, len(ranges), 2)]


def expected_pieces(text):
    """What the algorithm says should be bold, line by line."""
    pieces = []
    for line in text.split("\n"):
        pieces += [line[a:b] for a, b in bold_ranges(line)]
    return pieces


SAMPLE = (
    "Hello reading well-known world\n"
    "Привет, мир! Это проверка слов.\n"
    "Καλημέρα κόσμε\n"
    "see https://example.com/path?x=1 and don't stop\n"
    "\n"
    "Tabs\tand   spaces"
)


# ---- the button ----

def test_the_look_is_off_by_default(make_box):
    box = make_box("hello world")
    assert bold_pieces(box) == []

def test_clicking_the_button_turns_the_bold_on_and_clicking_again_turns_it_off(make_box):
    box = make_box("hello world")
    box.bold_starts_button.invoke()
    assert bold_pieces(box) == ["hel", "wor"]
    box.bold_starts_button.invoke()
    assert bold_pieces(box) == []

def test_the_icon_switches_with_the_state(make_box):
    box = make_box("hello")
    assert box.bold_starts_button.cget("image") is box._bold_off_image
    box.bold_starts_button.invoke()
    assert box.bold_starts_button.cget("image") is box._bold_on_image
    box.bold_starts_button.invoke()
    assert box.bold_starts_button.cget("image") is box._bold_off_image

def test_the_button_is_the_size_and_colour_of_the_normalize_button(make_box):
    box = make_box()
    for name in ("width", "height", "fg_color", "hover_color", "corner_radius"):
        assert box.bold_starts_button.cget(name) == box.normalize_button.cget(name)

def test_the_button_sits_beside_normalize_without_touching_it(root):
    top, box = shown_box(root)
    try:
        normalize, bold = box.normalize_button, box.bold_starts_button
        assert normalize.winfo_width() > 1 and bold.winfo_width() > 1
        assert span(bold)[0] >= span(normalize)[1]
        assert bold.winfo_rooty() == normalize.winfo_rooty()
    finally:
        top.destroy()


# ---- the callback and set_bold_starts ----

def test_a_click_tells_the_owner_the_new_state(make_box):
    told = []
    box = make_box("hello", on_bold_starts_toggled=told.append)
    box.bold_starts_button.invoke()
    box.bold_starts_button.invoke()
    assert told == [True, False]

def test_set_bold_starts_does_not_tell_the_owner(make_box):
    told = []
    box = make_box("hello", on_bold_starts_toggled=told.append)
    box.set_bold_starts(True)
    box.set_bold_starts(False)
    assert told == []

def test_set_bold_starts_changes_the_look_and_the_icon(make_box):
    box = make_box("hello world")
    box.set_bold_starts(True)
    assert bold_pieces(box) == ["hel", "wor"]
    assert box.bold_starts_button.cget("image") is box._bold_on_image
    box.set_bold_starts(False)
    assert bold_pieces(box) == []
    assert box.bold_starts_button.cget("image") is box._bold_off_image

def test_set_bold_starts_to_the_state_it_already_has_does_nothing(make_box, monkeypatch):
    box = make_box("hello")
    calls = []
    monkeypatch.setattr(box, "_apply_bold_starts", lambda: calls.append(1))
    box.set_bold_starts(False)
    assert calls == []
    box.set_bold_starts(True)
    assert len(calls) == 1
    box.set_bold_starts(True)
    assert len(calls) == 1

def test_a_click_without_an_owner_callback_is_fine(make_box):
    box = make_box("hello")
    box.bold_starts_button.invoke()
    assert bold_pieces(box) == ["hel"]

def test_it_can_start_out_on(make_box):
    box = make_box("hello world", bold_starts=True)
    assert bold_pieces(box) == ["hel", "wor"]
    assert box.bold_starts_button.cget("image") is box._bold_on_image

def test_starting_out_on_with_no_text_marks_nothing(make_box):
    box = make_box("", bold_starts=True)
    assert bold_pieces(box) == []


# ---- the text itself ----

def test_the_text_is_never_changed(make_box):
    box = make_box(SAMPLE)
    before = box.get_text()
    box.set_bold_starts(True)
    assert box.get_text() == before
    box.set_bold_starts(False)
    assert box.get_text() == before

def test_turning_it_on_does_not_mark_the_text_as_edited(make_box, root):
    box = make_box(SAMPLE)
    box.set_bold_starts(True)
    root.update()
    assert not box.textbox.edit_modified()

def test_the_bold_matches_the_algorithm_for_a_mixed_text(make_box):
    box = make_box(SAMPLE, bold_starts=True)
    assert bold_pieces(box) == expected_pieces(SAMPLE)

def test_the_bold_lands_on_the_right_letters_after_an_emoji(make_box):
    # Tk 8.6 counts an emoji as two columns and Tk 9 as one, so this is the
    # test that would fail on one of them if the column were not corrected.
    text = "hello \U0001F600 world \U0001F600\U0001F600 reading"
    box = make_box(text, bold_starts=True)
    assert bold_pieces(box) == expected_pieces(text)

def test_a_text_with_many_more_words_than_one_batch(make_box):
    text = "\n".join("alpha beta gamma delta" for _ in range(400))
    box = make_box(text, bold_starts=True)
    assert len(bold_pieces(box)) == 1600
    assert bold_pieces(box) == expected_pieces(text)

def test_a_text_that_is_exactly_one_batch_and_one_past_it(make_box):
    from gui.components import transcript_input

    batch = transcript_input._TAG_BATCH
    for words in (batch, batch + 1):
        text = " ".join(["word"] * words)
        box = make_box(text, bold_starts=True)
        assert len(bold_pieces(box)) == words

def test_set_text_while_on_marks_the_new_text(make_box):
    box = make_box("hello world", bold_starts=True)
    box.set_text("reading well")
    assert bold_pieces(box) == expected_pieces("reading well")

def test_set_text_while_off_marks_nothing(make_box):
    box = make_box("hello world")
    box.set_text("reading well")
    assert bold_pieces(box) == []

def test_set_text_to_nothing_while_on(make_box):
    box = make_box("hello world", bold_starts=True)
    box.set_text("")
    assert bold_pieces(box) == []

def test_normalize_and_revert_keep_the_look(make_box, root):
    messy = "Hello,   reading\n\n\n\nwell-known  world"
    box = make_box(messy, bold_starts=True)
    box.normalize_button.invoke()
    root.update()
    assert box.get_text().rstrip("\n") != messy
    assert bold_pieces(box) == expected_pieces(box.get_text().rstrip("\n"))
    box.normalize_button.invoke()
    root.update()
    assert bold_pieces(box) == expected_pieces(box.get_text().rstrip("\n"))

def test_normalize_still_works_with_the_look_off(make_box, root):
    box = make_box("Hello,   world")
    box.normalize_button.invoke()
    root.update()
    assert bold_pieces(box) == []


# ---- the font of the bold ----

def tag_font(box):
    from gui.components.transcript_input import BOLD_TAG

    inner = box.textbox._textbox
    return inner.tk.splitlist(inner.tag_cget(BOLD_TAG, "font"))

def test_the_bold_has_the_same_family_and_exact_pixel_size_as_the_text(make_box):
    box = make_box("hello", bold_starts=True)
    inner = box.textbox._textbox
    family, size = inner.tk.splitlist(inner.cget("font"))[:2]
    got = tag_font(box)
    assert got[0] == family
    assert int(got[1]) == int(size)
    assert "bold" in got

def test_the_pixel_size_is_kept_and_not_rounded_to_points(make_box):
    # The Text's font size is a negative number of pixels. A Tk Font object
    # would turn 13 pixels into 9 points; the tag must keep it as it is.
    box = make_box("hello", bold_starts=True)
    assert int(tag_font(box)[1]) < 0

def test_opendyslexic_text_is_bolded_in_the_bold_file_family(make_box, root):
    box = make_box("hello", bold_starts=True)
    box.textbox.configure(font=ctk.CTkFont(family="OpenDyslexic 3", size=14))
    root.update()
    assert tag_font(box)[0] == "OpenDyslexic3"

def test_another_family_is_bolded_in_itself(make_box, root):
    box = make_box("hello", bold_starts=True)
    box.textbox.configure(font=ctk.CTkFont(family="Courier", size=14))
    root.update()
    assert tag_font(box)[0] == "Courier"

def test_a_new_font_while_off_is_picked_up_when_the_look_is_turned_on(make_box, root):
    box = make_box("hello")
    box.textbox.configure(font=ctk.CTkFont(family="OpenDyslexic 3", size=14))
    root.update()
    box.set_bold_starts(True)
    assert tag_font(box)[0] == "OpenDyslexic3"

def test_the_tag_follows_a_change_of_display_scaling(make_box, root):
    box = make_box("hello", bold_starts=True)
    inner = box.textbox._textbox
    before = int(tag_font(box)[1])
    try:
        ctk.set_widget_scaling(1.5)
        root.update()
        text_size = int(inner.tk.splitlist(inner.cget("font"))[1])
        assert int(tag_font(box)[1]) == text_size
        assert abs(text_size) > abs(before)
    finally:
        ctk.set_widget_scaling(1.0)
        root.update()
    assert int(tag_font(box)[1]) == before

def test_the_tag_still_follows_the_text_after_two_scaling_changes(make_box, root):
    box = make_box("hello", bold_starts=True)
    inner = box.textbox._textbox
    try:
        for scale in (2.0, 1.25):
            ctk.set_widget_scaling(scale)
            root.update()
            assert int(tag_font(box)[1]) == int(inner.tk.splitlist(inner.cget("font"))[1])
    finally:
        ctk.set_widget_scaling(1.0)
        root.update()

def test_building_a_box_that_starts_out_on_does_not_crash(root):
    # CustomTkinter can call the font hooks while the edit box is still being
    # built, before the owner has a textbox attribute at all.
    from gui.components.transcript_input import TranscriptInput

    box = TranscriptInput(root, on_submit=lambda t: None, bold_starts=True)
    box.destroy()


# ---- the "Nothing to change" label ----

@pytest.mark.parametrize("scale", [1.0, 2.0])
def test_the_label_does_not_run_into_the_buttons_in_the_narrow_window(root, scale):
    """The detached window is 500px wide, and Start reading is wider than the
    two buttons. With the label beside the buttons it would run into Start
    reading; at the right-hand end of the row it must not touch anything."""
    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)
    top = None
    try:
        top, box = shown_box(root, 500, 350, initial_text="hello")
        box.feedback_label.configure(text="Nothing to change")
        top.update()
        label = box.feedback_label
        assert label.winfo_width() > 1

        l0, l1 = span(label)
        for name in ("start_button", "bold_starts_button", "normalize_button"):
            o0, o1 = span(getattr(box, name))
            assert l0 >= o1 or l1 <= o0, f"label {l0}-{l1} overlaps {name} {o0}-{o1}"

        # The buttons are in a row, in order, and none of it leaves the window.
        n0, n1 = span(box.normalize_button)
        b0, b1 = span(box.bold_starts_button)
        s0, s1 = span(box.start_button)
        assert n1 <= b0 and b1 <= s0 and s1 <= l0
        w0, w1 = span(top)
        assert w0 <= n0 and l1 <= w1
    finally:
        if top is not None:
            top.destroy()
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        root.update()

def test_the_label_is_at_the_right_hand_end_of_the_row(make_box):
    box = make_box()
    info = box.feedback_label.grid_info()
    assert int(info["column"]) == 2
    assert info["sticky"] == "e"

def test_the_label_shows_its_message_after_a_click_that_changes_nothing(make_box):
    box = make_box("hello world")
    box.normalize_button.invoke()
    assert box.feedback_label.cget("text") == "Nothing to change"
    box._clear_feedback()
    assert box.feedback_label.cget("text") == ""