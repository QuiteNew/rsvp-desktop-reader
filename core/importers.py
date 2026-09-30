"""Turns a file the user picks into plain transcript text.

One function per format (import_txt/import_srt/import_vtt/import_md/
import_docx/import_pdf), a dispatcher (import_file) that picks one by
extension, and a single exception (TranscriptImportError) that every
failure collapses into, whether that's a corrupt file, bad encoding, a
password-protected PDF, or no extractable text at all. That way gui/
only ever has to catch one thing and show its message as-is.

Every importer's output passes through clean_transcript_keep_lines()
before being returned: timestamps and extra spaces are removed, but
line breaks stay, so the edit view shows the file's lines and the
Normalize button (core/normalizer.py) has structure to work with.
Reading isn't affected, since core/reader.py flattens all whitespace
anyway.

No GUI dependency here (see core/ vs gui/ in the project brief).
gui/app.py picks the file, calls import_file(), and either shows the
error or hands the text to AddTranscriptDialog, the same as a blank
transcript."""

import re
from pathlib import Path

import docx
import pypdf

from core.parser import clean_transcript_keep_lines

# Also used by gui/app.py for its file-dialog filter list, so the two
# lists can't drift apart.
SUPPORTED_EXTENSIONS = {".txt", ".srt", ".vtt", ".md", ".markdown", ".docx", ".pdf"}


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
    needs its own pass. Each subtitle line stays on its own line; the
    Normalize button can rejoin sentences that span several of them."""
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
    return "\n".join(kept_lines)


def import_vtt(path: str) -> str:
    """A dependency-free WebVTT (.vtt) parser, the subtitle format that
    largely superseded .srt. A file looks like:

        WEBVTT

        intro
        00:00:01.000 --> 00:00:04.000 align:middle
        Hello world.

    Cues are separated by blank lines, so this is block-based rather than
    line-based like import_srt(). For each block it drops:
      - the WEBVTT header block (the file's first block),
      - NOTE/STYLE/REGION blocks (comments and styling, not content),
      - each cue's optional identifier line and its timing line (the one
        with "-->", cue settings such as align:/line: and all),
    and keeps only the cue's payload lines, stripping inline tags like
    <i>, <c.yellow> and <v Speaker>. Each payload line stays on its own
    line, same as import_srt(), so Normalize can rejoin sentences that
    span several. A block with no timing line is malformed, so it's
    skipped rather than emitted as junk. Timestamps here use "." for the
    fractional second rather than the "," .srt uses, but that never
    matters, since the whole timing line is dropped either way."""
    text = _read_text_with_fallback(path)
    kept_lines = []
    for block in re.split(r"\r?\n[ \t]*\r?\n", text):
        lines = block.strip().splitlines()
        if not lines:
            continue
        first = lines[0].strip()
        if first.startswith("WEBVTT") or first.startswith("NOTE") or first in ("STYLE", "REGION"):
            continue
        timing_idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_idx is None:
            continue
        for payload in lines[timing_idx + 1:]:
            cleaned = re.sub(r"<[^>]+>", "", payload).strip()
            if cleaned:
                kept_lines.append(cleaned)
    return "\n".join(kept_lines)


def _strip_inline_md(text: str) -> str:
    """Remove inline Markdown markup from a single line, keeping the text.
    Pragmatic rather than a full CommonMark parser (which would need a
    dependency): it handles the common cases: images and links (kept as
    their text), inline code, and *, **, _, __, ~~ emphasis, plus any
    stray inline HTML tags and backslash escapes. Emphasis is only
    stripped when it hugs its text (no space just inside the markers) and,
    for underscores, only when not intraword, so snake_case identifiers
    survive."""
    # Images first (![alt](url) -> alt), then links ([text](url) -> text,
    # [text][ref] -> text), so an image's "!" doesn't strand a link match.
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
    # Inline code: `code` (or ``co`de``) -> the code text, backticks gone.
    text = re.sub(r"`+(.+?)`+", r"\1", text)
    # Emphasis: strong before em, so ** isn't half-eaten by the * rule.
    text = re.sub(r"\*\*(?!\s)(.+?)(?<!\s)\*\*", r"\1", text)
    text = re.sub(r"\*(?!\s)(.+?)(?<!\s)\*", r"\1", text)
    text = re.sub(r"~~(?!\s)(.+?)(?<!\s)~~", r"\1", text)
    text = re.sub(r"(?<!\w)__(?!\s)(.+?)(?<!\s)__(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"\1", text)
    # Any leftover inline HTML tags, same as the subtitle importers.
    text = re.sub(r"<[^>]+>", "", text)
    # Backslash escapes: \* -> *, \_ -> _, etc.
    text = re.sub(r"\\([\\`*_{}\[\]()#+.!>~-])", r"\1", text)
    return text


def import_md(path: str) -> str:
    """A dependency-free Markdown (.md/.markdown) reader that strips the
    markup and keeps the text, so a note or article reads as plain prose.
    Not a full CommonMark parser (that would need a dependency); it's a
    line-based pass that:
      - drops fenced code blocks' ``` / ~~~ fence lines but keeps the code
        inside as plain text (nothing is discarded),
      - drops thematic breaks (---, ***, ___) and setext underlines
        (=== / ---),
      - strips ATX heading #'s, blockquote > markers, and unordered/
        ordered list markers, keeping the text after them,
      - strips inline markup via _strip_inline_md() (emphasis, code,
        links/images, stray HTML).
    Blank lines are kept as paragraph breaks; clean_transcript_keep_lines()
    tidies the rest. Each source line stays on its own line, so Normalize
    can rejoin sentences."""
    text = _read_text_with_fallback(path)
    kept_lines = []
    in_fence = False
    fence_marker = None
    for line in text.splitlines():
        fence_match = re.match(r"^\s*(```+|~~~+)", line)
        if fence_match:
            marker = fence_match.group(1)[0]  # ` or ~
            if not in_fence:
                in_fence = True
                fence_marker = marker
                continue
            if marker == fence_marker:
                in_fence = False
                fence_marker = None
                continue
            # A different fence character inside a fence is just content.
        if in_fence:
            kept_lines.append(line.rstrip())
            continue

        stripped = line.strip()
        if not stripped:
            kept_lines.append("")  # paragraph break, tidied later
            continue

        compact = re.sub(r"\s", "", stripped)
        if set(compact) == {"="}:
            continue  # setext H1 underline (===)
        if set(compact) == {"-"} and len(compact) >= 2:
            continue  # setext H2 underline / thematic break (--- etc.)
        if set(compact) <= {"*", "_"} and len(compact) >= 3:
            continue  # * or _ thematic break

        stripped = re.sub(r"^\s*(>\s?)+", "", stripped)          # blockquote markers
        stripped = re.sub(r"^\s*[-*+]\s+", "", stripped)         # unordered list marker
        stripped = re.sub(r"^\s*\d+[.)]\s+", "", stripped)       # ordered list marker
        stripped = re.sub(r"^#{1,6}\s+", "", stripped)           # ATX heading opener
        stripped = re.sub(r"\s+#+\s*$", "", stripped)            # ATX heading closer
        stripped = _strip_inline_md(stripped)

        kept_lines.append(stripped.strip())
    return "\n".join(kept_lines)


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
    """Picks the right importer by extension, tidies the result through
    clean_transcript_keep_lines(), and rejects empty output (a scanned
    PDF with no text layer, an empty file) as an error instead of
    silently creating a blank transcript."""
    suffix = Path(path).suffix.lower()
    if suffix == ".txt":
        raw = import_txt(path)
    elif suffix == ".srt":
        raw = import_srt(path)
    elif suffix == ".vtt":
        raw = import_vtt(path)
    elif suffix in (".md", ".markdown"):
        raw = import_md(path)
    elif suffix == ".docx":
        raw = import_docx(path)
    elif suffix == ".pdf":
        raw = import_pdf(path)
    else:
        raise TranscriptImportError(f"Unsupported file type: {suffix or Path(path).name}")

    cleaned = clean_transcript_keep_lines(raw)
    if not cleaned:
        raise TranscriptImportError(f"{Path(path).name} didn't contain any readable text.")
    return cleaned
