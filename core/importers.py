"""Turning a file the user picks into plain transcript text.

One function per supported format (import_txt, import_srt, import_docx,
import_pdf), a dispatcher (import_file) that picks the right one by
extension, and a single exception (TranscriptImportError) that every
failure mode -- corrupt file, wrong encoding, password-protected PDF, no
extractable text at all -- collapses into, so gui/ only ever has to
catch one thing and show its message to the user as-is. Mirrors
core/data_bundle.py's BundleFormatError in shape, for the same reason.

Every importer's raw extracted text is passed through clean_transcript()
before being handed back, same as a manually pasted transcript would be
-- so all four formats end up normalized the same way, through the one
place that already does it.

This module has no GUI dependency -- see core/ vs gui/ in the project
brief. gui/app.py collects the file path via a native file dialog, calls
import_file(), and either shows a MessageDialog (on TranscriptImportError)
or hands the returned text to AddTranscriptDialog, same shape as the
existing blank-transcript flow.
"""

import logging
import re
from pathlib import Path

import docx
import pypdf

from core.parser import clean_transcript

# pypdf logs (doesn't raise) a warning through Python's logging module
# every time extract_text() meets a font it can only partially decode
# without the optional fontTools package -- see import_pdf() below.
# Harmless as a one-off notice, but confirmed against pypdf's own source
# (_cmap.py's _parse_to_unicode()) that this is NOT cached across pages:
# a PDF where many pages share the same such font re-triggers the
# identical warning once per page, each one built from and printed with
# that font's FULL width table. On a large, font-heavy PDF that can mean
# constructing and writing out hundreds of these multi-hundred-number
# strings before any actual text extraction happens -- a real, measurable
# cost sitting directly in import_pdf()'s per-page loop. Whether it's
# THE cause of a hang on a specific huge PDF isn't confirmed -- a complex
# enough document can be slow to extract for unrelated reasons too -- but
# it's worth eliminating regardless: this app never shows the user a
# console, so these warnings were always pure waste, not just noise.
# Raising the logger's level is pypdf's own documented way to quiet it:
# https://pypdf.readthedocs.io/en/stable/user/suppress-warnings.html
logging.getLogger("pypdf").setLevel(logging.ERROR)

# The only formats v1 supports -- also used by gui/app.py to build the
# native file dialog's filetypes list, so the two can never drift apart.
SUPPORTED_EXTENSIONS = {".txt", ".srt", ".docx", ".pdf"}


class TranscriptImportError(Exception):
    """Raised when a file being imported can't be turned into transcript
    text -- unreadable, corrupt, wrong format, password-protected, or
    with no extractable text at all. The message is meant to be shown to
    the user as-is."""


def _read_text_with_fallback(path: str) -> str:
    """Decodes a text-ish file's bytes, tolerating the two real-world
    cases plain utf-8 alone doesn't handle: a UTF-8 BOM (utf-8-sig
    strips it if present, and behaves exactly like utf-8 if not, so
    trying it first costs nothing) and a genuinely non-UTF-8 file, most
    often an older Windows text file saved in some 8-bit encoding.
    latin-1 never raises UnicodeDecodeError -- every byte value maps to
    *some* character in it -- so it's a safe last-resort fallback that's
    guaranteed to return something rather than crash, even though it can
    mis-render a handful of exotic non-Latin encodings."""
    raw_bytes = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise TranscriptImportError(f"Couldn't read {Path(path).name} as text.")  # pragma: no cover -- latin-1 above is total, so this is unreachable in practice


def import_txt(path: str) -> str:
    return _read_text_with_fallback(path)


def import_srt(path: str) -> str:
    """A plain, dependency-free .srt parser. Subtitle blocks look like:

        1
        00:00:01,000 --> 00:00:04,000
        Hello world.

    Deliberately line-based rather than block-based (splitting on blank
    lines first): a line is dropped if it's blank, purely numeric (the
    block's index), or contains "-->" (the timestamp line); everything
    else is kept as subtitle text, with simple <...> markup tags (italics
    etc., which some .srt files include) stripped out. This is more
    tolerant of slightly malformed files than requiring a strict
    index/timestamp/text/blank-line block shape would be, and every real
    .srt line that matters still gets handled correctly either way.
    core/parser.py's own timestamp regex doesn't apply here -- .srt's
    "00:00:01,000 --> 00:00:04,000" shape isn't what it matches -- so
    this needs its own pass rather than reusing it directly."""
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
        # reader.is_encrypted only reports whether the FILE is an
        # encrypted PDF -- confirmed against a real one that it stays
        # True even *after* a successful decrypt(), so whether we can
        # actually read it has to come from decrypt()'s own return value
        # instead: PasswordType.NOT_DECRYPTED (falsy) means the empty
        # string wasn't the right password. An empty user password is a
        # real, common case -- some PDFs are "encrypted" only to restrict
        # printing/editing (an owner password), with no password actually
        # needed to open and read them.
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
            # document -- skip it and keep going.
            continue
    return "\n".join(pages_text)


def import_file(path: str) -> str:
    """The one entry point gui/app.py calls: picks the right importer by
    extension, then runs the result through clean_transcript() -- the
    same normalization a manually pasted transcript gets -- and rejects
    anything that comes out empty (a scanned PDF with no text layer, an
    empty file, an otherwise-blank document) as an error rather than
    silently creating a blank transcript."""
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