"""The checks behind `RSVPReader --self-check`, which the release build runs on
the packaged app before anything is released.

The tests run from source, where every package is simply installed. A packaged
app only has what PyInstaller decided to put in it, and some of that is found
at runtime, not by reading the imports. The clearest case is the cryptography
package: pypdf only reaches for it when it meets an AES-encrypted PDF, so an
app that starts fine can still fail on one if it was left out of the bundle.
So these checks do real work with the app's own importers on files made here
from scratch, and report which step failed, if one does.

This is pure logic and never touches a window. The window part of the
self-check lives in gui/self_check.py, which also does the reporting. One check
failing never stops the others, so a single run shows everything that is wrong
at once."""

import importlib
import io
import platform
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from core.app_info import APP_NAME, APP_VERSION
from core.importers import import_file

# Whatever the packaged app needs that isn't a plain import in the code the
# build can see. darkdetect is here too: the spec only names it as a hidden
# import, and its own comment says that isn't a guaranteed fix.
LIBRARY_MODULES = (
    "PIL.Image",
    "pypdf",
    "docx",
    "lxml.etree",
    "lxml.html",
    "cryptography",
    "darkdetect",
)

PDF_TEXT = "Self check pdf line"
WORD_TEXT = "Self check word line"
HTML_TEXT = "Self check html line"


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one check: its name, whether it passed, and what went
    wrong when it didn't."""
    name: str
    ok: bool
    detail: str = ""


@dataclass(frozen=True)
class SelfCheckRequest:
    """What the command line asked for. report_path is where the report should
    be written, or None to only print it."""
    report_path: str | None


def parse_self_check_args(argv) -> SelfCheckRequest | None:
    """argv without the program name. Gives None unless --self-check is in it,
    so the app starts as usual for everything else, including the extra
    arguments some systems add when they open an app. The word after
    --self-check is the report file, when it isn't another option."""
    args = list(argv)
    if "--self-check" not in args:
        return None
    after = args[args.index("--self-check") + 1:]
    report_path = after[0] if after and not after[0].startswith("-") else None
    return SelfCheckRequest(report_path)


def describe_error(error: BaseException) -> str:
    """The error on one line, with its type, so a report line stays a line."""
    return f"{type(error).__name__}: {' '.join(str(error).split())}"


# ---- The libraries ----

def check_libraries() -> CheckResult:
    """Every library the app needs can be imported."""
    problems = []
    for name in LIBRARY_MODULES:
        try:
            importlib.import_module(name)
        except Exception as error:
            problems.append(f"{name} ({describe_error(error)})")
    if problems:
        return CheckResult("libraries", False, "; ".join(problems))
    return CheckResult("libraries", True)


def check_pdf_encryption_provider() -> CheckResult:
    """pypdf is using the cryptography package for AES. When that package is
    missing pypdf doesn't fail on import, it quietly falls back to a stand-in
    that can't decrypt, so this asks it which one it picked."""
    try:
        from pypdf._crypt_providers import crypt_provider
        provider = crypt_provider[0]
    except Exception as error:
        return CheckResult("PDF encryption provider", False, describe_error(error))
    if provider != "cryptography":
        return CheckResult("PDF encryption provider", False, f"pypdf is using {provider!r}, not 'cryptography'")
    return CheckResult("PDF encryption provider", True)


# ---- Files made from scratch ----

def _plain_pdf(text: str) -> bytes:
    """A small one-page PDF that really contains the text. pypdf can read and
    change PDFs but can't write text into one, so this builds the raw structure
    by hand, with just enough for text extraction to find the text. It's the
    same approach the tests use."""
    content_stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode("latin-1")
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
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(out)


def _encrypted_pdf(text: str, algorithm: str) -> bytes:
    """The same PDF, locked the way "no editing or printing" PDFs are: with an
    empty password to open it, so the app has to decrypt it without asking
    anyone. Making it needs the cryptography package too."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(_plain_pdf(text))))
    writer.encrypt(user_password="", owner_password="self-check-owner", algorithm=algorithm)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _word_document(text: str) -> bytes:
    """A Word file with one paragraph, written by hand: just the three parts a
    reader needs. python-docx's own Document() would work too, but it builds
    from a template file bundled inside the package, and the app never uses
    that, so a bundle missing it would fail a check for nothing."""
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return out.getvalue()


def _html_page(text: str) -> bytes:
    return f"<html><body><p>{text}</p></body></html>".encode("utf-8")


# What gets imported: the name shown in the report, the file name (its ending
# is what picks the importer), how to make the file, and the text that must
# come back out of it.
_FILE_CASES = (
    ("PDF import", "plain.pdf", lambda: _plain_pdf(PDF_TEXT), PDF_TEXT),
    ("PDF import (AES-128)", "aes128.pdf", lambda: _encrypted_pdf(PDF_TEXT, "AES-128"), PDF_TEXT),
    ("PDF import (AES-256)", "aes256.pdf", lambda: _encrypted_pdf(PDF_TEXT, "AES-256"), PDF_TEXT),
    ("Word import", "word.docx", lambda: _word_document(WORD_TEXT), WORD_TEXT),
    ("HTML import", "page.html", lambda: _html_page(HTML_TEXT), HTML_TEXT),
)


def _check_import(name: str, path: Path, build, expected: str) -> CheckResult:
    """Makes the file, imports it the way the app does, and compares the text.
    Anything that goes wrong on the way is the result, never an exception."""
    try:
        path.write_bytes(build())
        text = import_file(str(path))
    except Exception as error:
        return CheckResult(name, False, describe_error(error))
    if text.strip() != expected:
        return CheckResult(name, False, f"expected {expected!r} but got {text.strip()!r}")
    return CheckResult(name, True)


def run_core_checks(work_dir) -> list[CheckResult]:
    """Every check that needs no window. work_dir is where the files are made,
    and is created if it isn't there."""
    directory = Path(work_dir)
    directory.mkdir(parents=True, exist_ok=True)
    results = [check_libraries(), check_pdf_encryption_provider()]
    for name, filename, build, expected in _FILE_CASES:
        results.append(_check_import(name, directory / filename, build, expected))
    return results


# ---- The report ----

def all_passed(results) -> bool:
    """True when there was something to check and all of it passed. No results
    at all is a failure, not a pass: it would mean nothing ran."""
    return bool(results) and all(result.ok for result in results)


def describe_environment() -> str:
    packaged = "packaged app" if getattr(sys, "frozen", False) else "running from source"
    return f"Python {platform.python_version()} on {sys.platform}, {packaged}"


def format_report(results) -> str:
    """The whole report as text: a header, one line per check and a last line
    that says whether it passed, which is also what the build looks for."""
    lines = [f"{APP_NAME} {APP_VERSION} self-check", describe_environment(), ""]
    for result in results:
        mark = "ok  " if result.ok else "FAIL"
        detail = f": {result.detail}" if result.detail else ""
        lines.append(f"{mark}  {result.name}{detail}")
    lines.append("")
    if not results:
        lines.append("SELF-CHECK FAILED: no checks ran.")
    elif all_passed(results):
        lines.append(f"SELF-CHECK PASSED: all {len(results)} checks.")
    else:
        failed = sum(1 for result in results if not result.ok)
        lines.append(f"SELF-CHECK FAILED: {failed} of {len(results)} checks failed.")
    return "\n".join(lines) + "\n"
