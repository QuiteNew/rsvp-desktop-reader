"""Tests for core/self_check.py, the checks the release build runs on the
packaged app (RSVPReader --self-check).

The checks are only worth having if they can fail. A check that always passes
would make the release build look safe while checking nothing, so most of what
is here makes something go wrong on purpose and looks for the failure in the
report: the importer breaking, the PDF library falling back to a stand-in that
can't decrypt, a library that can't be imported. The one thing the packaged app
has gone wrong with before, cryptography being left out, is the same as the
fallback case: pypdf doesn't fail when it's missing, it quietly can't decrypt.

The files the checks make are tested as well, because a check that imports a
file that isn't what it claims to be would pass for the wrong reason: an AES
check on a PDF that isn't encrypted proves nothing."""

import sys
import types

import pytest
from pypdf import PdfReader

from core import self_check
from core.app_info import APP_NAME, APP_VERSION
from core.importers import TranscriptImportError
from core.self_check import (
    CheckResult,
    SelfCheckRequest,
    all_passed,
    format_report,
    parse_self_check_args,
    run_core_checks,
)

EXPECTED_CHECKS = [
    "libraries",
    "PDF encryption provider",
    "PDF import",
    "PDF import (AES-128)",
    "PDF import (AES-256)",
    "Word import",
    "HTML import",
]


def _by_name(results):
    return {result.name: result for result in results}


# ---- The command line ----

def test_nothing_is_asked_for_without_the_flag():
    assert parse_self_check_args([]) is None
    assert parse_self_check_args(["transcript.txt"]) is None


def test_extra_arguments_a_system_adds_do_not_start_a_self_check():
    assert parse_self_check_args(["-psn_0_123456"]) is None


def test_the_flag_alone_means_print_only():
    assert parse_self_check_args(["--self-check"]) == SelfCheckRequest(report_path=None)


def test_the_word_after_the_flag_is_the_report_file():
    assert parse_self_check_args(["--self-check", "report.txt"]) == SelfCheckRequest("report.txt")


def test_another_option_after_the_flag_is_not_taken_for_the_report_file():
    assert parse_self_check_args(["--self-check", "--other"]) == SelfCheckRequest(report_path=None)


def test_the_flag_is_found_wherever_it_is():
    assert parse_self_check_args(["-psn_0_1", "--self-check", "out.txt"]) == SelfCheckRequest("out.txt")


# ---- A normal run ----

def test_every_core_check_passes_when_everything_is_installed(tmp_path):
    results = run_core_checks(tmp_path)
    failed = [f"{result.name}: {result.detail}" for result in results if not result.ok]
    assert failed == []
    assert [result.name for result in results] == EXPECTED_CHECKS


def test_the_folder_for_the_files_is_made_when_it_is_missing(tmp_path):
    folder = tmp_path / "not" / "there" / "yet"
    assert all_passed(run_core_checks(folder))
    assert folder.is_dir()


# ---- The files the checks make are what they claim to be ----

@pytest.mark.parametrize("algorithm, cipher", [("AES-128", "/AESV2"), ("AES-256", "/AESV3")])
def test_the_encrypted_pdfs_really_use_aes_and_open_with_no_password(tmp_path, algorithm, cipher):
    """The cipher is read back out of the file, because an older cipher (RC4)
    is encrypted too and would pass for AES if only is_encrypted were looked
    at. RC4 needs no cryptography package, so it would prove nothing."""
    path = tmp_path / "locked.pdf"
    path.write_bytes(self_check._encrypted_pdf(self_check.PDF_TEXT, algorithm))
    reader = PdfReader(path)
    assert reader.is_encrypted
    assert reader.trailer["/Encrypt"]["/CF"]["/StdCF"]["/CFM"] == cipher
    assert reader.decrypt("")
    assert self_check.PDF_TEXT in reader.pages[0].extract_text()


def test_the_plain_pdf_is_not_encrypted(tmp_path):
    path = tmp_path / "plain.pdf"
    path.write_bytes(self_check._plain_pdf(self_check.PDF_TEXT))
    assert not PdfReader(path).is_encrypted


def test_the_word_file_is_a_real_one_that_python_docx_opens(tmp_path):
    import docx

    path = tmp_path / "word.docx"
    path.write_bytes(self_check._word_document(self_check.WORD_TEXT))
    assert [p.text for p in docx.Document(str(path)).paragraphs] == [self_check.WORD_TEXT]


# ---- A check that goes wrong is reported, and the others still run ----

def test_a_failing_importer_is_reported_and_only_that_check_fails(tmp_path, monkeypatch):
    real_import_file = self_check.import_file

    def import_file(path):
        if path.endswith(".docx"):
            raise TranscriptImportError("Couldn't open it as a Word document")
        return real_import_file(path)

    monkeypatch.setattr(self_check, "import_file", import_file)
    results = _by_name(run_core_checks(tmp_path))
    assert not results["Word import"].ok
    assert "Couldn't open it as a Word document" in results["Word import"].detail
    assert [name for name, result in results.items() if not result.ok] == ["Word import"]


def test_text_that_comes_back_wrong_fails_the_check(tmp_path, monkeypatch):
    monkeypatch.setattr(self_check, "import_file", lambda path: "something else")
    results = _by_name(run_core_checks(tmp_path))
    assert not results["PDF import"].ok
    assert "something else" in results["PDF import"].detail


def test_pdf_encryption_falling_back_to_the_stand_in_is_caught(monkeypatch):
    """What a bundle without cryptography looks like: pypdf starts fine and
    names its stand-in as the provider."""
    monkeypatch.setattr("pypdf._crypt_providers.crypt_provider", ("local_crypt_fallback", object()))
    result = self_check.check_pdf_encryption_provider()
    assert not result.ok
    assert "local_crypt_fallback" in result.detail


def test_aes_pdfs_that_cannot_be_decrypted_fail_their_checks_and_the_plain_one_does_not(tmp_path, monkeypatch):
    """The same failure from the other end: decrypting raises, which is what
    pypdf does without cryptography. The importer reports that as a password
    problem, and the check carries the report."""
    def decrypt(self, password):
        raise RuntimeError("cryptography>=3.1 is required for AES algorithm")

    monkeypatch.setattr(PdfReader, "decrypt", decrypt)
    results = _by_name(run_core_checks(tmp_path))
    assert not results["PDF import (AES-128)"].ok
    assert not results["PDF import (AES-256)"].ok
    assert results["PDF import"].ok
    assert results["Word import"].ok


def test_a_library_that_cannot_be_imported_is_named(monkeypatch):
    real_import_module = self_check.importlib.import_module

    def import_module(name, *args):
        if name == "lxml.etree":
            raise ModuleNotFoundError("No module named 'lxml.etree'")
        return real_import_module(name, *args)

    monkeypatch.setattr(self_check, "importlib", types.SimpleNamespace(import_module=import_module))
    result = self_check.check_libraries()
    assert not result.ok
    assert "lxml.etree" in result.detail
    assert "ModuleNotFoundError" in result.detail


def test_every_library_is_tried_and_all_the_failures_are_listed(monkeypatch):
    def import_module(name, *args):
        raise ImportError("nope")

    monkeypatch.setattr(self_check, "importlib", types.SimpleNamespace(import_module=import_module))
    result = self_check.check_libraries()
    assert not result.ok
    for name in self_check.LIBRARY_MODULES:
        assert name in result.detail


# ---- The report ----

def test_the_report_says_passed_and_names_the_app_and_version():
    report = format_report([CheckResult("one", True), CheckResult("two", True)])
    assert report.splitlines()[0] == f"{APP_NAME} {APP_VERSION} self-check"
    assert "ok    one" in report
    assert report.strip().splitlines()[-1] == "SELF-CHECK PASSED: all 2 checks."


def test_the_report_says_failed_and_gives_the_reason():
    report = format_report([CheckResult("one", True), CheckResult("two", False, "it broke")])
    assert "FAIL  two: it broke" in report
    assert report.strip().splitlines()[-1] == "SELF-CHECK FAILED: 1 of 2 checks failed."
    assert "PASSED" not in report


def test_the_report_says_whether_this_is_the_packaged_app(monkeypatch):
    assert "running from source" in format_report([CheckResult("one", True)])
    # PyInstaller sets sys.frozen in the packaged app
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert "packaged app" in format_report([CheckResult("one", True)])


def test_no_checks_at_all_is_a_failure_not_a_pass():
    assert not all_passed([])
    report = format_report([])
    assert "SELF-CHECK FAILED: no checks ran." in report
    assert "PASSED" not in report


def test_one_failure_among_passes_is_not_a_pass():
    assert not all_passed([CheckResult("a", True), CheckResult("b", False), CheckResult("c", True)])


def test_errors_are_described_on_one_line():
    error = TranscriptImportError("first line\n\nsecond   line")
    assert self_check.describe_error(error) == "TranscriptImportError: first line second line"
