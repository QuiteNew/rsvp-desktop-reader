"""Pure matching for the Settings search box, kept out of gui/ so the rule can
be unit tested without importing the GUI. The Settings window describes each
setting with a name, some extra search terms, and a description; this decides
whether a typed query finds it."""


def query_words(query: str) -> list[str]:
    """Split a typed query into lowercase words. A blank query gives an empty
    list."""
    return query.casefold().split()


def matches(
    query: str,
    name: str,
    keywords: str = "",
    description: str = "",
    include_description: bool = False,
) -> bool:
    """Whether a setting is found by the query.

    The name and the extra keywords are always searched. The description is
    searched only when include_description is on, so by default a long
    explanation does not drag unrelated settings into the results.

    Every word in the query must appear somewhere in the searched text, in any
    order, and a word may be just the start of a longer one ("guid" finds
    "guide"). Case is ignored. A blank query matches everything, which is what
    lets the full list come back when the box is cleared."""
    words = query_words(query)
    if not words:
        return True
    parts = [name, keywords]
    if include_description:
        parts.append(description)
    searched = " ".join(part for part in parts if part).casefold()
    return all(word in searched for word in words)