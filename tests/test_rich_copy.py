"""Tests for core/rich_copy.py, the text-with-bold to clipboard HTML conversion.

Two kinds of check. The header is read back the way a program reading the
clipboard would read it, and every offset is checked against the bytes, with
Cyrillic and emoji in the text since they are what moves byte counts away from
character counts. And the HTML is parsed back into lines of characters with a
bold flag each, which has to equal what went in, so nothing is lost, doubled or
bolded by mistake, whatever the text holds (a fuzz test does the same with random
text)."""

import random
import re
from html.parser import HTMLParser

import pytest

from core.rich_copy import cf_html, segments_text


# ---- reading the result back ----

def read_header(data: bytes) -> dict:
    """The four offsets from the header at the front of the data."""
    head = data[:data.index(b"<html")].decode("ascii")
    assert head.startswith("Version:0.9\r\n")
    found = dict(re.findall(r"(\w+):(\d+)\r\n", head))
    assert set(found) == {"StartHTML", "EndHTML", "StartFragment", "EndFragment"}
    assert all(len(number) == 10 for number in found.values())
    return {name: int(number) for name, number in found.items()}


def fragment_of(data: bytes) -> str:
    """The text between StartFragment and EndFragment, as the offsets give it."""
    offsets = read_header(data)
    return data[offsets["StartFragment"]:offsets["EndFragment"]].decode("utf-8")


class _Reader(HTMLParser):
    """Reads the fragment back as lines, each a list of (character, bold)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.bold = False
        self.open = False

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            assert not self.open, "a paragraph inside a paragraph"
            self.open = True
            self.lines.append([])
        elif tag == "b":
            assert self.open and not self.bold, "a bold outside a paragraph or inside a bold"
            self.bold = True

    def handle_endtag(self, tag):
        if tag == "p":
            assert self.open and not self.bold, "a paragraph closed with a bold still open"
            self.open = False
        elif tag == "b":
            assert self.bold
            self.bold = False

    def handle_data(self, data):
        assert self.open, f"text outside a paragraph: {data!r}"
        self.lines[-1].extend((char, self.bold) for char in data)


def read_lines(data: bytes) -> list[list[tuple[str, bool]]]:
    reader = _Reader()
    reader.feed(fragment_of(data))
    reader.close()
    assert not reader.open and not reader.bold
    return reader.lines


def expected_lines(segments):
    """What the segments should read back as: split on "\\n", controls gone, a tab
    as four non-breaking spaces and an empty line as one."""
    lines = [[]]
    for text, bold in segments:
        for char in text:
            if char == "\n":
                lines.append([])
            elif char == "\t":
                lines[-1].extend(("\xa0", bold) for _ in range(4))
            elif char < " " or "\x7f" <= char <= "\x9f":
                continue
            else:
                lines[-1].append((char, bold))
    return [line or [("\xa0", False)] for line in lines]


def normalise(lines):
    """Non-breaking and ordinary spaces are told apart by other tests, here they
    are the same, since both are a space to a reader."""
    return [[(" " if char == "\xa0" else char, bold) for char, bold in line] for line in lines]


# ---- the header ----

TEXTS = [
    "plain ascii",
    "Привет, как дела? Это длинный русский текст",
    "emoji \U0001F600 and \U0001F9D1\u200d\U0001F4BB inside",
    "mixed: abc бвг \U0001F600 ñandú — “quotes”",
    "",
]

@pytest.mark.parametrize("text", TEXTS)
def test_the_header_offsets_point_at_the_right_bytes(text):
    data = cf_html([(text, False), (text, True)])
    offsets = read_header(data)
    assert offsets["EndHTML"] == len(data)
    assert data[offsets["StartHTML"]:].startswith(b"<html")
    assert data[offsets["StartHTML"]:].endswith(b"</html>")
    start, end = offsets["StartFragment"], offsets["EndFragment"]
    assert data[start - len(b"<!--StartFragment-->"):start] == b"<!--StartFragment-->"
    assert data[end:end + len(b"<!--EndFragment-->")] == b"<!--EndFragment-->"
    assert start < end or text == ""

def test_the_header_counts_bytes_not_characters():
    plain = cf_html([("abcd", False)])
    cyrillic = cf_html([("абвг", False)])
    emoji = cf_html([("\U0001F600" * 4, False)])
    width = lambda data: read_header(data)["EndFragment"] - read_header(data)["StartFragment"]
    assert width(cyrillic) - width(plain) == 4          # two bytes a letter against one
    assert width(emoji) - width(plain) == 12            # four bytes a character against one

def test_the_data_is_utf8_with_a_header_of_a_fixed_size():
    short = read_header(cf_html([("a", False)]))["StartHTML"]
    long = read_header(cf_html([("a " * 5000, True)]))["StartHTML"]
    assert short == long
    cf_html([("\U0001F600", True)]).decode("utf-8")

def test_the_document_says_it_is_utf8():
    assert b'<meta charset="utf-8">' in cf_html([("Привет", False)])


# ---- what is written ----

def fragment(*segments):
    return fragment_of(cf_html(list(segments)))

def test_a_bold_stretch_is_wrapped_and_the_rest_is_not():
    assert fragment(("ab", True), ("cd", False)) == '<p style="margin:0"><b>ab</b>cd</p>'

def test_neighbouring_pieces_with_the_same_boldness_join_into_one_stretch():
    assert fragment(("ab", True), ("cd", True), ("ef", False), ("gh", False)) == (
        '<p style="margin:0"><b>abcd</b>efgh</p>')

def test_text_with_markup_characters_is_escaped():
    assert fragment(("<b>&amp;</b>", False)) == '<p style="margin:0">&lt;b&gt;&amp;amp;&lt;/b&gt;</p>'
    assert fragment(("a < b & c > d", True)) == '<p style="margin:0"><b>a &lt; b &amp; c &gt; d</b></p>'

def test_quotes_stay_as_they_are():
    assert fragment(('say "hi" it\'s', False)) == '<p style="margin:0">say "hi" it\'s</p>'

def test_each_line_is_a_paragraph():
    assert fragment(("one\ntwo", False)) == '<p style="margin:0">one</p><p style="margin:0">two</p>'

def test_a_bold_stretch_across_a_line_break_is_closed_and_opened_again():
    assert fragment(("ab\ncd", True)) == '<p style="margin:0"><b>ab</b></p><p style="margin:0"><b>cd</b></p>'

def test_an_empty_line_keeps_a_row():
    assert fragment(("one\n\ntwo", False)) == (
        '<p style="margin:0">one</p><p style="margin:0">&nbsp;</p><p style="margin:0">two</p>')

def test_a_trailing_line_break_gives_a_last_empty_paragraph():
    assert fragment(("one\n", False)).endswith('<p style="margin:0">&nbsp;</p>')

def test_no_text_is_one_empty_paragraph():
    assert fragment() == '<p style="margin:0">&nbsp;</p>'
    assert fragment(("", True)) == '<p style="margin:0">&nbsp;</p>'

def test_a_lone_space_between_words_stays_a_space():
    assert fragment(("a b c", False)) == '<p style="margin:0">a b c</p>'

def test_spaces_html_would_drop_become_non_breaking():
    assert fragment(("a  b", False)) == '<p style="margin:0">a&nbsp;&nbsp;b</p>'
    assert fragment(("   a", False)) == '<p style="margin:0">&nbsp;&nbsp;&nbsp;a</p>'
    assert fragment(("a   ", False)) == '<p style="margin:0">a&nbsp;&nbsp;&nbsp;</p>'
    assert fragment((" ", False)) == '<p style="margin:0">&nbsp;</p>'

def test_a_space_that_has_a_different_boldness_than_its_neighbour_is_still_judged_by_the_line():
    # The space between a plain and a bold word is a lone space, written plainly,
    # and one next to another space is not, wherever the bold starts.
    assert fragment(("a ", False), ("b", True)) == '<p style="margin:0">a <b>b</b></p>'
    assert fragment(("a ", False), (" b", True)) == '<p style="margin:0">a&nbsp;<b>&nbsp;b</b></p>'

def test_a_tab_is_four_non_breaking_spaces():
    assert fragment(("a\tb", False)) == '<p style="margin:0">a&nbsp;&nbsp;&nbsp;&nbsp;b</p>'

def test_a_space_next_to_a_tab_is_made_non_breaking():
    assert fragment(("a \tb", False)) == '<p style="margin:0">a&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;b</p>'

def test_control_characters_and_carriage_returns_are_left_out():
    assert fragment(("a\r\nb\x00c\x1bd\x7fe\x85f", False)) == (
        '<p style="margin:0">a</p><p style="margin:0">bcdef</p>')

def test_other_line_separators_are_not_line_breaks():
    # Only "\n" ends a line, as in a Tk text widget.
    out = fragment(("a\u2028b\u2029c", False))
    assert out.count("<p") == 1 and "\u2028" in out and "\u2029" in out

def test_cyrillic_and_emoji_are_written_as_they_are():
    assert fragment(("Привет \U0001F600", True)) == '<p style="margin:0"><b>Привет \U0001F600</b></p>'


# ---- the plain text next to it ----

def test_the_plain_text_is_the_pieces_joined_untouched():
    pieces = [("ab\r\n", True), ("\tcd\x00", False)]
    assert segments_text(pieces) == "ab\r\n\tcd\x00"
    assert segments_text([]) == ""


# ---- reading the HTML back ----

CASES = [
    [("hello world", True)],
    [("he", True), ("llo ", False), ("wo", True), ("rld", False)],
    [("Прив", True), ("ет мир\n", False), ("\U0001F600 ", True), ("ok", False)],
    [("  indented\n\n\n  tail  ", False), ("\t", True)],
    [("a\n", True), ("\n", False), ("b", True)],
    [("<&>", True), ("\"'", False)],
]

@pytest.mark.parametrize("segments", CASES)
def test_the_html_reads_back_as_the_same_characters_and_bold(segments):
    data = cf_html(segments)
    assert normalise(read_lines(data)) == normalise(expected_lines(segments))

@pytest.mark.parametrize("segments", CASES)
def test_no_space_is_left_that_html_would_squeeze(segments):
    for line in read_lines(cf_html(segments)):
        written = "".join(char for char, _ in line)
        assert "  " not in written
        assert not written.startswith(" ") and not written.endswith(" ")

def test_random_text_reads_back_the_same_and_keeps_its_offsets():
    rng = random.Random(20261021)
    alphabet = ["a", "b", "Z", "б", "ж", "\U0001F600", "&", "<", ">", '"', "'", " ", " ", " ",
                "\t", "\n", "\n", "\r", "\x00", "\x7f", "\x85", "\u200d", "\u00ad", "-", "é", "1"]
    for _ in range(400):
        segments = [("".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12))), rng.random() < 0.5)
                    for _ in range(rng.randint(0, 8))]
        data = cf_html(segments)
        offsets = read_header(data)
        assert offsets["EndHTML"] == len(data)
        assert data[offsets["StartFragment"]:offsets["EndFragment"]].decode("utf-8").startswith("<p")
        assert normalise(read_lines(data)) == normalise(expected_lines(segments)), segments
        for line in read_lines(data):
            written = "".join(char for char, _ in line)
            assert "  " not in written
            assert not written.startswith(" ") and not written.endswith(" ")

def test_a_whole_book_is_quick():
    import time

    words = "the quick brown fox jumps over the lazy dog ".split()
    line = " ".join(words * 12)
    segments = [(line + "\n", i % 2 == 0) for i in range(8000)]   # about a million characters
    started = time.perf_counter()
    data = cf_html(segments)
    elapsed = time.perf_counter() - started
    assert read_header(data)["EndHTML"] == len(data)
    assert elapsed < 5