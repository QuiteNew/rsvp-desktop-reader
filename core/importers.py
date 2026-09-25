"""Turns a file the user picks into plain transcript text.

One function per format (import_txt/import_srt/import_docx/import_pdf),
a dispatcher (import_file) that picks one by extension, and a single
exception (TranscriptImportError) that every failure collapses into,
whether that's a corrupt file, bad encoding, a password-protected PDF,
or no extractable text at all. That way gui/ only ever has to catch
one thing and show its message as-is.

Every importer's output passes through clean_transcript() before being
returned, so an imported file is normalized exactly like a pasted one.

No GUI dependency here (see core/ vs gui/ in the project brief).
gui/app.py picks the file, calls import_file(), and either shows the
error or hands the text to AddTranscriptDialog, the same as a blank
transcript."""

import re
from pathlib import Path

import docx
import pypdf

from core.parser import clean_transcript

# Also used by gui/app.py for its file-dialog filter list, so the two
# lists can't drift apart.
SUPPORTED_EXTENSIONS = {".txt", ".srt", ".docx", ".pdf"}


class TranscriptImportError(Exception):
    """Raised when a file being imported can't be turned into transcript
    text: unreadable, corrupt, wrong format, password-protected, or with
    no extractable text at all. The message is meant to be shown to the
    user as-is."""


def _read_text_with_fallback(path: str) -> str:
    """Decodes file bytes, handling what plain utf-8 misses: a UTF-8 BOM
    (utf-8-sig strips it if present, and behaves like plain utf-8 if not,
    so trying it first is free) and genuinely non-UTF-8 files, usually an
    older Windows text file. latin-1 is the last resort, and it never
    raises, since every byte maps to some character. That means this
    always returns something instead of crashing, even if it mis-renders
    rare encodings."""
    raw_bytes = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise TranscriptImportError(f"Couldn't read {Path(path).name} as text.")  # pragma: no cover: latin-1 above is total, so this is unreachable in practice


def import_txt(path: str) -> str:
    return _read_text_with_fallback(path)


def import_srt(path: str) -> str:
    """A plain, dependency-free .srt parser. Subtitle blocks look like:

        1
        00:00:01,000 --> 00:00:04,000
        Hello world.

    Line-based rather than block-based: drop a line if it's blank, purely
    numeric (the index), or has "-->" (the timestamp); keep everything
    else as subtitle text, stripping simple <...> markup tags. More
    tolerant of malformed files than requiring a strict block shape.
    core/parser.py's timestamp regex doesn't match .srt's format, so this
    needs its own pass."""
    text = _read_text_with_fallback(path)
    kept_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.isdigit():
            continue
        if "-->" in stripped:
            continue
        stripped = re.sub(r"<[^>]+>", "", stripped).strip()
        if stripped:
            kept_lines.append(stripped)
    return " ".join(kept_lines)


def import_docx(path: str) -> str:
    try:
        document = docx.Document(path)
    except Exception as e:
        raise TranscriptImportError(
            f"Couldn't open {Path(path).name} as a Word document:\n\n{e}"
        ) from e
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def import_pdf(path: str) -> str:
    try:
        reader = pypdf.PdfReader(path)
    except Exception as e:
        raise TranscriptImportError(
            f"Couldn't open {Path(path).name} as a PDF:\n\n{e}"
        ) from e

    if reader.is_encrypted:
        # is_encrypted stays True even after a successful decrypt(), so
        # whether we can actually read it comes from decrypt()'s return
        # value instead. An empty password is a common real case, since
        # some PDFs are "encrypted" only to block printing or editing,
        # with nothing needed to open and read them.
        try:
            decrypt_result = reader.decrypt("")
        except Exception:
            decrypt_result = 0
        if not decrypt_result:
            raise TranscriptImportError(
                f"{Path(path).name} is password-protected, so it can't be imported."
            )

    pages_text = []
    for page in reader.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception:
            # One unreadable page shouldn't sink an otherwise-readable
            # document, so skip it and keep going.
            continue
    return "\n".join(pages_text)


def import_file(path: str) -> str:
    """Picks the right importer by extension, normalizes the result
    through clean_transcript(), and rejects empty output (a scanned PDF
    with no text layer, an empty file) as an error instead of silently
    creating a blank transcript."""
    suffix = Path(path).suffix.lower()
    if suffix == ".txt":
        raw = import_txt(path)
    elif suffix == ".srt":
        raw = import_srt(path)
    elif suffix == ".docx":
        raw = import_docx(path)
    elif suffix == ".pdf":
        raw = import_pdf(path)
    else:
        raise TranscriptImportError(f"Unsupported file type: {suffix or Path(path).name}")

    cleaned = clean_transcript(raw)
    if not cleaned:
        raise TranscriptImportError(f"{Path(path).name} didn't contain any readable text.")
    return cleaned