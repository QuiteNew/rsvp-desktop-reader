"""Tests for store/listing.md, the text pasted into Partner Center.

Partner Center turns a listing down when a field is over its limit, and it only
says so after the text has been pasted in. These tests read the file and catch
that here instead: every field is checked against the limit the Store gives
it, the links are the ones the app really has, and a few phrases that would
make a claim the app can't back up are kept out."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LISTING = ROOT / "store" / "listing.md"

DESCRIPTION_LIMIT = 10_000
FEATURE_COUNT_LIMIT = 20
FEATURE_LIMIT = 200
SEARCH_TERM_COUNT_LIMIT = 7
SEARCH_TERM_LIMIT = 30
COPYRIGHT_LIMIT = 200
WHATS_NEW_LIMIT = 1_500
CERTIFICATION_NOTES_LIMIT = 2_000

# Claims the app can't back up. The README once said reading this way keeps
# comprehension intact, which docs/technique.md contradicts, and the Store
# asks for accurate listings. "Bionic Reading" is somebody else's trademark.
BANNED_PHRASES = (
    "without losing comprehension",
    "bionic reading",
)


def _sections():
    """Split listing.md into {heading: body}. HTML comments (the limit
    notes) are dropped, since they aren't part of what gets pasted."""
    text = LISTING.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    sections = {}
    # Everything before the first "## " is the file's own intro.
    for chunk in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        heading, _, body = chunk.partition("\n")
        sections[heading.strip()] = body.strip()
    return sections


@pytest.fixture(scope="module")
def sections():
    return _sections()


def _numbered(body):
    return [m.group(1) for m in re.finditer(r"^\d+\. (.+)$", body, flags=re.MULTILINE)]


def _bulleted(body):
    return [m.group(1) for m in re.finditer(r"^- (.+)$", body, flags=re.MULTILINE)]


def test_every_field_is_there(sections):
    wanted = {
        "Description",
        "Product features",
        "Search terms",
        "Copyright and trademark info",
        "Links",
        "Category",
        "What's new",
        "Notes for certification",
        "runFullTrust justification",
    }
    assert wanted <= set(sections)


def test_description_is_within_the_limit(sections):
    assert 0 < len(sections["Description"]) <= DESCRIPTION_LIMIT


def test_description_has_no_markdown_the_store_would_show_as_typed(sections):
    # Partner Center shows the description as plain text.
    description = sections["Description"]
    for mark in ("**", "__", "```", "\n#", "\n- "):
        assert mark not in description


def test_features_are_within_the_limits(sections):
    features = _numbered(sections["Product features"])
    assert 0 < len(features) <= FEATURE_COUNT_LIMIT
    for feature in features:
        assert len(feature) <= FEATURE_LIMIT, feature


def test_features_are_numbered_without_gaps(sections):
    numbers = [
        int(m.group(1))
        for m in re.finditer(r"^(\d+)\. ", sections["Product features"], flags=re.MULTILINE)
    ]
    assert numbers == list(range(1, len(numbers) + 1))


def test_no_feature_is_listed_twice(sections):
    features = [f.lower() for f in _numbered(sections["Product features"])]
    assert len(features) == len(set(features))


def test_search_terms_are_within_the_limits(sections):
    terms = _bulleted(sections["Search terms"])
    assert 0 < len(terms) <= SEARCH_TERM_COUNT_LIMIT
    for term in terms:
        assert len(term) <= SEARCH_TERM_LIMIT, term


def test_no_search_term_is_listed_twice(sections):
    terms = [t.lower() for t in _bulleted(sections["Search terms"])]
    assert len(terms) == len(set(terms))


def test_copyright_line(sections):
    line = sections["Copyright and trademark info"]
    assert line == "© 2026 QuiteNew"
    assert len(line) <= COPYRIGHT_LIMIT


def test_links_are_the_ones_the_app_has(sections):
    links = dict(re.findall(r"^- ([^:]+): (\S+)$", sections["Links"], flags=re.MULTILINE))
    assert links == {
        "Privacy policy": "https://quitenew.github.io/rsvp-desktop-reader/privacy/",
        "Website": "https://quitenew.github.io/rsvp-desktop-reader/",
        "Support": "https://github.com/QuiteNew/rsvp-desktop-reader/issues",
    }


def test_privacy_link_matches_the_one_in_the_app():
    # The About window links to the same page; the two must not drift apart.
    from core.app_info import PRIVACY_URL

    links = re.findall(r"https://\S+/privacy/", LISTING.read_text(encoding="utf-8"))
    assert links == [PRIVACY_URL]


def test_category(sections):
    assert sections["Category"] == "Productivity"


def test_whats_new_is_within_the_limit(sections):
    assert len(sections["What's new"]) <= WHATS_NEW_LIMIT


def test_certification_notes_are_within_the_limit(sections):
    notes = sections["Notes for certification"]
    assert 0 < len(notes) <= CERTIFICATION_NOTES_LIMIT


def test_certification_notes_say_no_account_is_needed(sections):
    # A tester who can't sign in fails the app, so this must be said up front.
    assert "No account" in sections["Notes for certification"]


def test_full_trust_justification_says_what_it_is_used_for(sections):
    text = sections["runFullTrust justification"]
    assert text
    assert "runFullTrust" in text
    assert ".rsvp_reader" in text


@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_banned_phrases_are_kept_out(phrase):
    assert phrase not in LISTING.read_text(encoding="utf-8").lower()