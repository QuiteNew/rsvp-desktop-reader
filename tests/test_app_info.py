"""Tests for core/app_info.py, the app's name, version, licence and project
link shown in the About dialog.

The constants are only data, so most of what can go wrong is them drifting
away from the places they have to agree with: the docs config, the README, the
LICENSE file, the main window's title, and the release tags. These tests read
those files and compare, so a rename, a new repository address or a forgotten
version bump shows up here instead of in a released build."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from core.app_info import APP_NAME, APP_VERSION, LICENSE_NAME, REPO_URL

ROOT = Path(__file__).resolve().parent.parent


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _newest_release_tag(repo: Path):
    """The highest vMAJOR.MINOR.PATCH tag in the repository as a tuple of
    numbers, or None when there is nothing to compare with: git is not
    installed, this is not a repository, or it has no such tags. Compared as
    numbers, so v1.10.0 beats v1.9.5, which a plain text sort would get
    wrong. Tags that are not plain releases (a stray "main", "v2", a
    "-rc1") are ignored."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "tag", "--list"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    versions = []
    for tag in result.stdout.split():
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
        if match:
            versions.append(tuple(int(part) for part in match.groups()))
    return max(versions) if versions else None


def _make_repo(path: Path, tags) -> None:
    """A throwaway repository with one empty commit and the given tags. Signing
    is switched off so a global gpgsign setting cannot stall the test."""
    git = ["git", "-C", str(path), "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
           "-c", "user.name=test", "-c", "user.email=test@example.com"]
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "first"], check=True, capture_output=True)
    for tag in tags:
        subprocess.run([*git, "tag", tag], check=True, capture_output=True)


needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


# ---- The constants themselves ----

def test_version_is_three_plain_numbers():
    assert re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", APP_VERSION)


def test_repo_url_is_a_plain_github_project_address():
    assert re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+", REPO_URL)
    assert not REPO_URL.endswith(("/", ".git"))


def test_shown_values_are_not_empty_or_padded():
    for value in (APP_NAME, APP_VERSION, LICENSE_NAME, REPO_URL):
        assert value
        assert value == value.strip()


# ---- Agreement with the rest of the project ----

def test_repo_url_matches_the_docs_config():
    match = re.search(r"^repo_url:\s*(\S+)\s*$", _read("mkdocs.yml"), flags=re.MULTILINE)
    assert match, "mkdocs.yml has no repo_url line"
    assert match.group(1) == REPO_URL


def test_repo_url_is_the_one_the_readme_links_to():
    assert REPO_URL in _read("README.md")


def test_licence_name_matches_the_licence_file():
    first_line = _read("LICENSE").splitlines()[0].strip()
    assert first_line == f"{LICENSE_NAME} License"


def test_app_name_matches_the_main_window_title():
    assert f'self.title("{APP_NAME}")' in _read("gui/app.py")


# ---- The release-time check ----

def test_version_is_not_behind_the_newest_release_tag():
    """The version is bumped by hand, so this catches the one way that goes
    wrong: tagging a release without updating APP_VERSION first. It only fails
    once the tag exists, as a prompt to fix it before the build ships. It is
    skipped where there is no git or no release tag to compare with."""
    newest = _newest_release_tag(ROOT)
    if newest is None:
        pytest.skip("no release tags to compare with (no git, or no vX.Y.Z tags here)")
    current = tuple(int(part) for part in APP_VERSION.split("."))
    newest_text = ".".join(str(part) for part in newest)
    assert current >= newest, (
        f"APP_VERSION is {APP_VERSION} but the newest release tag is v{newest_text}. "
        f"Bump APP_VERSION in core/app_info.py before tagging a release."
    )


# ---- The tag reader behind that check ----

@needs_git
def test_newest_tag_is_found_by_number_not_by_text(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    _make_repo(tmp_path, ["v1.2.0", "v1.10.0", "v1.9.5"])
    assert _newest_release_tag(tmp_path) == (1, 10, 0)


@needs_git
def test_tags_that_are_not_plain_releases_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    _make_repo(tmp_path, ["main", "v2", "v1.0", "v9.9.9-rc1", "release-9.9.9", "v1.0.0"])
    assert _newest_release_tag(tmp_path) == (1, 0, 0)


@needs_git
def test_a_repository_with_no_release_tags_gives_nothing_to_compare(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    _make_repo(tmp_path, ["main"])
    assert _newest_release_tag(tmp_path) is None


@needs_git
def test_a_folder_that_is_not_a_repository_gives_nothing_to_compare(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert _newest_release_tag(tmp_path) is None