import docx
import pytest
from pypdf import PdfWriter

from core.importers import (
    SUPPORTED_EXTENSIONS,
    TranscriptImportError,
    import_docx,
    import_file,
    import_html,
    import_md,
    import_pdf,
    import_srt,
    import_txt,
    import_vtt,
)


def _write_text_pdf(path, text_line):
    """Writes a small single-page PDF that really contains the given text,
    so it's not a mock. pypdf can read and modify PDFs but can't write text
    into one, so this builds the raw PDF structure by hand, with just enough
    for PdfReader.extract_text() to find the text."""
    content_stream = f"BT /F1 24 Tf 72 700 Td ({text_line}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n"
        + content_stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    path.write_bytes(bytes(out))


# .txt files

def test_import_txt_plain_utf8(tmp_path):
    path = tmp_path / "plain.txt"
    path.write_bytes("Hello world. Café résumé.\n".encode("utf-8"))
    assert import_txt(str(path)) == "Hello world. Café résumé.\n"

def test_import_txt_strips_utf8_bom(tmp_path):
    path = tmp_path / "bom.txt"
    path.write_bytes("Hello with BOM.\n".encode("utf-8-sig"))
    assert import_txt(str(path)) == "Hello with BOM.\n"

def test_import_txt_falls_back_to_latin1(tmp_path):
    path = tmp_path / "latin1.txt"
    path.write_bytes("Café in Latin-1.\n".encode("latin-1"))
    assert import_txt(str(path)) == "Café in Latin-1.\n"

def test_import_file_rejects_empty_txt(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")
    with pytest.raises(TranscriptImportError, match="readable text"):
        import_file(str(path))


# .srt files

def test_import_srt_drops_index_and_timestamp_lines(tmp_path):
    path = tmp_path / "sample.srt"
    path.write_text(
        "1\n00:00:01,000 --> 00:00:04,000\nHello world.\n\n"
        "2\n00:00:04,500 --> 00:00:06,000\nSecond line.\n",
        encoding="utf-8",
    )
    result = import_srt(str(path))
    assert "-->" not in result
    assert "Hello world." in result
    assert "Second line." in result
    assert "1" not in result.split()
    assert "2" not in result.split()

def test_import_srt_strips_simple_markup_tags(tmp_path):
    path = tmp_path / "italic.srt"
    path.write_text("1\n00:00:01,000 --> 00:00:02,000\n<i>Emphasized</i> text.\n", encoding="utf-8")
    assert import_srt(str(path)) == "Emphasized text."

def test_import_srt_puts_each_subtitle_line_on_its_own_line(tmp_path):
    path = tmp_path / "lines.srt"
    path.write_text(
        "1\n00:00:01,000 --> 00:00:04,000\nHello world.\n\n"
        "2\n00:00:04,500 --> 00:00:06,000\nand then we went\nto the store.\n",
        encoding="utf-8",
    )
    assert import_srt(str(path)) == "Hello world.\nand then we went\nto the store."


# .vtt files

def test_import_vtt_drops_header_and_timing_lines(tmp_path):
    path = tmp_path / "sample.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:04.000\nHello world.\n\n"
        "00:00:04.500 --> 00:00:06.000\nSecond line.\n",
        encoding="utf-8",
    )
    result = import_vtt(str(path))
    assert "WEBVTT" not in result
    assert "-->" not in result
    assert result == "Hello world.\nSecond line."

def test_import_vtt_drops_cue_identifier_lines(tmp_path):
    path = tmp_path / "ids.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "intro\n00:00:01.000 --> 00:00:04.000\nHello world.\n\n"
        "2\n00:00:04.500 --> 00:00:06.000\nSecond line.\n",
        encoding="utf-8",
    )
    assert import_vtt(str(path)) == "Hello world.\nSecond line."

def test_import_vtt_drops_note_blocks(tmp_path):
    path = tmp_path / "notes.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "NOTE This is a comment\nthat spans two lines.\n\n"
        "00:00:01.000 --> 00:00:04.000\nActual subtitle.\n",
        encoding="utf-8",
    )
    result = import_vtt(str(path))
    assert "comment" not in result
    assert result == "Actual subtitle."

def test_import_vtt_drops_style_and_region_blocks(tmp_path):
    path = tmp_path / "style.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "STYLE\n::cue { color: yellow }\n\n"
        "REGION\nid:fred width:40%\n\n"
        "00:00:01.000 --> 00:00:04.000\nReadable text.\n",
        encoding="utf-8",
    )
    result = import_vtt(str(path))
    assert "cue" not in result
    assert "width" not in result
    assert result == "Readable text."

def test_import_vtt_strips_inline_tags(tmp_path):
    path = tmp_path / "tags.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:02.000\n<v Roger>Some <c.yellow>emphasized</c> text.\n",
        encoding="utf-8",
    )
    assert import_vtt(str(path)) == "Some emphasized text."

def test_import_vtt_ignores_cue_settings_on_the_timing_line(tmp_path):
    path = tmp_path / "settings.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:04.000 align:middle line:90%\nCentered text.\n",
        encoding="utf-8",
    )
    assert import_vtt(str(path)) == "Centered text."

def test_import_vtt_keeps_multi_line_cues_on_separate_lines(tmp_path):
    path = tmp_path / "multi.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:04.000\nand then we went\nto the store.\n",
        encoding="utf-8",
    )
    assert import_vtt(str(path)) == "and then we went\nto the store."

def test_import_file_dispatches_vtt(tmp_path):
    path = tmp_path / "dispatch.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nHello world.\n",
        encoding="utf-8",
    )
    assert import_file(str(path)) == "Hello world."


# .md files

def test_import_md_strips_atx_headings(tmp_path):
    path = tmp_path / "h.md"
    path.write_text("# Title\n\n## Subtitle ##\n\nBody text.\n", encoding="utf-8")
    result = import_md(str(path))
    assert "#" not in result
    assert "Title" in result
    assert "Subtitle" in result
    assert "Body text." in result

def test_import_md_drops_setext_underlines_but_keeps_heading(tmp_path):
    path = tmp_path / "setext.md"
    path.write_text("Big Title\n=========\n\nSmall Title\n-----\n", encoding="utf-8")
    result = import_md(str(path))
    assert "Big Title" in result
    assert "Small Title" in result
    assert "=" not in result
    assert "---" not in result

def test_import_md_drops_thematic_breaks(tmp_path):
    path = tmp_path / "hr.md"
    path.write_text("Above.\n\n***\n\nBelow.\n", encoding="utf-8")
    result = import_md(str(path))
    assert "*" not in result
    assert "Above." in result
    assert "Below." in result

def test_import_md_strips_emphasis_markers(tmp_path):
    path = tmp_path / "em.md"
    path.write_text("This is **bold**, *italic*, and ~~struck~~.\n", encoding="utf-8")
    assert import_md(str(path)) == "This is bold, italic, and struck."

def test_import_md_strips_inline_code(tmp_path):
    path = tmp_path / "code.md"
    path.write_text("Run `pip install` first.\n", encoding="utf-8")
    assert import_md(str(path)) == "Run pip install first."

def test_import_md_keeps_link_and_image_text(tmp_path):
    path = tmp_path / "links.md"
    path.write_text("See [the docs](https://example.com) and ![a logo](logo.png).\n", encoding="utf-8")
    assert import_md(str(path)) == "See the docs and a logo."

def test_import_md_strips_list_markers(tmp_path):
    path = tmp_path / "lists.md"
    path.write_text("- First\n- Second\n\n1. One\n2. Two\n", encoding="utf-8")
    assert import_md(str(path)) == "First\nSecond\n\nOne\nTwo"

def test_import_md_strips_blockquote_markers(tmp_path):
    path = tmp_path / "quote.md"
    path.write_text("> Quoted line.\n>> Nested quote.\n", encoding="utf-8")
    assert import_md(str(path)) == "Quoted line.\nNested quote."

def test_import_md_keeps_fenced_code_content_without_the_fences(tmp_path):
    path = tmp_path / "fence.md"
    path.write_text("Intro.\n\n```python\nx = 1\n```\n\nOutro.\n", encoding="utf-8")
    result = import_md(str(path))
    assert "```" not in result
    assert "python" not in result
    assert "x = 1" in result
    assert "Intro." in result
    assert "Outro." in result

def test_import_md_leaves_snake_case_intact(tmp_path):
    path = tmp_path / "snake.md"
    path.write_text("Call the some_helper_function today.\n", encoding="utf-8")
    assert import_md(str(path)) == "Call the some_helper_function today."

def test_import_file_dispatches_md(tmp_path):
    path = tmp_path / "doc.md"
    path.write_text("# Heading\n\nSome **bold** prose.\n", encoding="utf-8")
    assert import_file(str(path)) == "Heading\n\nSome bold prose."

def test_import_file_dispatches_markdown_extension(tmp_path):
    path = tmp_path / "doc.markdown"
    path.write_text("Just text.\n", encoding="utf-8")
    assert import_file(str(path)) == "Just text."


# .html files

def test_import_html_extracts_paragraph_text_and_drops_tags(tmp_path):
    path = tmp_path / "page.html"
    path.write_text("<html><body><p>Hello <b>world</b>.</p></body></html>", encoding="utf-8")
    assert import_html(str(path)) == "Hello world."

def test_import_html_drops_script_and_style(tmp_path):
    path = tmp_path / "noisy.html"
    path.write_text(
        "<html><head><style>.x{color:red}</style></head>"
        "<body><script>var a = 1;</script><p>Readable.</p></body></html>",
        encoding="utf-8",
    )
    result = import_html(str(path))
    assert "color" not in result
    assert "var a" not in result
    assert result == "Readable."

def test_import_html_drops_head_metadata(tmp_path):
    path = tmp_path / "titled.html"
    path.write_text(
        "<html><head><title>Page Title</title></head><body><p>Body text.</p></body></html>",
        encoding="utf-8",
    )
    result = import_html(str(path))
    assert "Page Title" not in result
    assert result == "Body text."

def test_import_html_separates_paragraphs_onto_their_own_lines(tmp_path):
    path = tmp_path / "paras.html"
    path.write_text(
        "<html><body><p>First paragraph.</p><p>Second paragraph.</p></body></html>",
        encoding="utf-8",
    )
    assert import_html(str(path)) == "First paragraph.\nSecond paragraph."

def test_import_html_turns_br_into_line_breaks(tmp_path):
    path = tmp_path / "br.html"
    path.write_text("<html><body><p>Line one.<br>Line two.</p></body></html>", encoding="utf-8")
    assert import_html(str(path)) == "Line one.\nLine two."

def test_import_html_puts_list_items_on_separate_lines(tmp_path):
    path = tmp_path / "list.html"
    path.write_text(
        "<html><body><ul><li>First</li><li>Second</li></ul></body></html>",
        encoding="utf-8",
    )
    assert import_html(str(path)) == "First\nSecond"

def test_import_html_collapses_internal_whitespace(tmp_path):
    path = tmp_path / "ws.html"
    path.write_text(
        "<html><body><p>Wrapped\n    across   several\n    lines.</p></body></html>",
        encoding="utf-8",
    )
    assert import_html(str(path)) == "Wrapped across several lines."

def test_import_html_decodes_entities(tmp_path):
    path = tmp_path / "entities.html"
    path.write_text("<html><body><p>Tom &amp; Jerry &lt;3</p></body></html>", encoding="utf-8")
    assert import_html(str(path)) == "Tom & Jerry <3"

def test_import_file_dispatches_html(tmp_path):
    path = tmp_path / "doc.html"
    path.write_text("<html><body><p>Dispatched.</p></body></html>", encoding="utf-8")
    assert import_file(str(path)) == "Dispatched."

def test_import_file_dispatches_htm_extension(tmp_path):
    path = tmp_path / "doc.htm"
    path.write_text("<html><body><p>Short extension.</p></body></html>", encoding="utf-8")
    assert import_file(str(path)) == "Short extension."

def test_import_file_rejects_html_with_no_text(tmp_path):
    path = tmp_path / "empty.html"
    path.write_text("<html><head><title>Only a title</title></head><body></body></html>", encoding="utf-8")
    with pytest.raises(TranscriptImportError, match="readable text"):
        import_file(str(path))


# .docx files

def test_import_docx_extracts_paragraphs_and_drops_blank_ones(tmp_path):
    path = tmp_path / "sample.docx"
    d = docx.Document()
    d.add_paragraph("First paragraph.")
    d.add_paragraph("")
    d.add_paragraph("Second paragraph.")
    d.save(path)
    assert import_docx(str(path)) == "First paragraph.\nSecond paragraph."

def test_import_docx_rejects_corrupt_file(tmp_path):
    path = tmp_path / "corrupt.docx"
    path.write_bytes(b"not a real docx file")
    with pytest.raises(TranscriptImportError):
        import_docx(str(path))

def test_import_file_rejects_empty_docx(tmp_path):
    path = tmp_path / "empty.docx"
    docx.Document().save(path)
    with pytest.raises(TranscriptImportError, match="readable text"):
        import_file(str(path))


# .pdf files

def test_import_pdf_extracts_real_text(tmp_path):
    path = tmp_path / "sample.pdf"
    _write_text_pdf(path, "Hello from a real PDF")
    assert "Hello from a real PDF" in import_pdf(str(path))

def test_import_pdf_rejects_corrupt_file(tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.4 not really valid")
    with pytest.raises(TranscriptImportError):
        import_pdf(str(path))

def test_import_file_rejects_pdf_with_no_extractable_text(tmp_path):
    path = tmp_path / "no_text.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        writer.write(f)
    with pytest.raises(TranscriptImportError, match="readable text"):
        import_file(str(path))

def test_import_pdf_decrypts_when_user_password_is_empty(tmp_path):
    """Some PDFs are encrypted with only an owner password and an empty user
    password. This is common for files that just block printing or editing
    but open without a password. pypdf's is_encrypted stays True even after
    a successful decrypt(), so import_pdf() has to check what decrypt()
    returns instead. This test makes sure that path really works, not just
    that it doesn't crash."""
    path = tmp_path / "encrypted_emptyuserpw.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(user_password="", owner_password="ownersecret")
    with open(path, "wb") as f:
        writer.write(f)
    # The blank page has no text, so this should fail with "no readable
    # text" and not "password-protected". That proves the decrypt with the
    # empty password succeeded first.
    with pytest.raises(TranscriptImportError, match="readable text"):
        import_file(str(path))

def test_import_pdf_reports_password_protected_when_password_is_required(tmp_path):
    path = tmp_path / "encrypted_realpw.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(user_password="realpassword", owner_password="ownersecret2")
    with open(path, "wb") as f:
        writer.write(f)
    with pytest.raises(TranscriptImportError, match="password-protected"):
        import_file(str(path))


# Picking the importer by file extension

def test_import_file_dispatches_by_extension(tmp_path):
    path = tmp_path / "plain.txt"
    path.write_text("Hello world.", encoding="utf-8")
    assert import_file(str(path)) == "Hello world."

def test_import_file_keeps_line_breaks(tmp_path):
    path = tmp_path / "lines.txt"
    path.write_text("1. Buy milk\n2. Buy eggs\n", encoding="utf-8")
    assert import_file(str(path)) == "1. Buy milk\n2. Buy eggs"

def test_import_file_tidies_spaces_and_blank_lines(tmp_path):
    path = tmp_path / "messy.txt"
    # Written as bytes so the Windows line endings are exactly these,
    # whichever OS the test runs on.
    path.write_bytes(b"  First   line.  \r\n\r\n\r\n\r\nSecond\tline.\n")
    assert import_file(str(path)) == "First line.\n\nSecond line."

def test_import_file_still_strips_timestamps(tmp_path):
    path = tmp_path / "stamped.txt"
    path.write_text("[00:00:01] Welcome.\n(1:23) Goodbye.", encoding="utf-8")
    assert import_file(str(path)) == "Welcome.\nGoodbye."

def test_import_file_keeps_docx_paragraphs_on_separate_lines(tmp_path):
    path = tmp_path / "paragraphs.docx"
    d = docx.Document()
    d.add_paragraph("First paragraph.")
    d.add_paragraph("Second paragraph.")
    d.save(path)
    assert import_file(str(path)) == "First paragraph.\nSecond paragraph."

def test_import_file_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "sample.xyz"
    path.write_text("irrelevant", encoding="utf-8")
    with pytest.raises(TranscriptImportError, match="Unsupported"):
        import_file(str(path))

def test_supported_extensions_contents():
    assert SUPPORTED_EXTENSIONS == {".txt", ".srt", ".vtt", ".md", ".markdown", ".html", ".htm", ".docx", ".pdf"}