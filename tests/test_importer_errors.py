"""Tests for what the PDF importer does when pypdf fails partway through a file
(core/importers.py, import_pdf()), on top of the importer tests in
test_importers.py.

Two failures are handled on purpose, and nothing tested either:

  - decrypt() raising instead of answering, which happens with an encryption
    entry pypdf can't work with. The file is reported as password-protected,
    the same as a PDF whose password really is needed.
  - One page whose text can't be extracted. It's skipped and the rest of the
    document is kept. When every page fails, import_file() reports that the
    file has no readable text.

Both are made to happen on real PDFs, built the same way test_importers.py
builds them, by making the one pypdf call involved raise."""

import pytest
from pypdf import PageObject, PdfReader, PdfWriter

from core.importers import TranscriptImportError, import_file, import_pdf

from test_importers import _write_text_pdf


def _pdf_with_pages(tmp_path, *lines):
    """A real PDF with one page of text for each line, in order."""
    writer = PdfWriter()
    for number, line in enumerate(lines):
        page = tmp_path / f"page{number}.pdf"
        _write_text_pdf(page, line)
        writer.append(PdfReader(page))
    path = tmp_path / "pages.pdf"
    with open(path, "wb") as f:
        writer.write(f)
    return path


@pytest.fixture
def unreadable_pages(monkeypatch):
    """Make extract_text() raise for the pages whose text contains any of the
    words added to the returned set."""
    words = set()
    real_extract_text = PageObject.extract_text

    def extract_text(page, *args, **kwargs):
        text = real_extract_text(page, *args, **kwargs)
        if any(word in text for word in words):
            raise ValueError("this page can't be read")
        return text

    monkeypatch.setattr(PageObject, "extract_text", extract_text)
    return words


def test_the_pdfs_are_real(tmp_path):
    """The pages built here really hold their text, so a page that goes
    missing below was skipped, not empty to begin with."""
    path = _pdf_with_pages(tmp_path, "First page", "Second page", "Third page")
    text = import_pdf(str(path))
    assert text.splitlines() == ["First page", "Second page", "Third page"]


# ---- a page that can't be read ----

def test_a_page_that_cant_be_read_is_skipped_and_the_rest_kept(tmp_path, unreadable_pages):
    path = _pdf_with_pages(tmp_path, "First page", "Second page", "Third page")
    unreadable_pages.add("Second")

    assert import_file(str(path)).splitlines() == ["First page", "Third page"]


def test_a_pdf_whose_pages_all_fail_has_no_readable_text(tmp_path, unreadable_pages):
    path = _pdf_with_pages(tmp_path, "First page", "Second page")
    unreadable_pages.update({"First", "Second"})

    with pytest.raises(TranscriptImportError, match="pages.pdf didn't contain any readable text"):
        import_file(str(path))


# ---- decrypt() raising ----

def _encrypted_pdf(tmp_path, user_password):
    plain = tmp_path / "plain.pdf"
    _write_text_pdf(plain, "Behind a password")
    writer = PdfWriter(clone_from=PdfReader(plain))
    writer.encrypt(user_password=user_password, owner_password="owner", algorithm="RC4-128")
    path = tmp_path / "locked.pdf"
    with open(path, "wb") as f:
        writer.write(f)
    return path


@pytest.mark.parametrize("user_password", ["", "secret"], ids=["no_password_needed", "password_needed"])
def test_a_pdf_that_decrypt_fails_on_is_reported_as_password_protected(tmp_path, monkeypatch, user_password):
    """Whatever the password would have been, a decrypt() that raises means
    the text can't be got at, and the message says why in words the person
    can act on."""
    path = _encrypted_pdf(tmp_path, user_password)

    def decrypt(reader, password):
        raise NotImplementedError("unsupported encryption")

    monkeypatch.setattr(PdfReader, "decrypt", decrypt)

    with pytest.raises(TranscriptImportError, match="locked.pdf is password-protected, so it can't be imported"):
        import_file(str(path))


def test_without_the_failure_the_same_pdf_imports(tmp_path):
    """The file above with no password needed is readable when decrypt()
    works, so the message above came from decrypt() raising."""
    path = _encrypted_pdf(tmp_path, "")
    assert import_file(str(path)) == "Behind a password"