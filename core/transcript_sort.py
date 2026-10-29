"""The ways the sidebar can sort a space's transcripts.

Each order has a short id, which is what gets saved in the settings, and a
label, which is what the sort menu shows. Keeping the two apart means a label
can be reworded later without the saved choice of everyone who picked it
quietly going back to the default.

The list is drawn by gui/components/transcript_list_body.py, and the choice is
saved by core/settings_store.py. This file only knows how to put transcripts in
order, so it can be tested without a screen."""

from typing import NamedTuple


class SortOrder(NamedTuple):
    label: str   # what the sort menu shows
    key: object  # turns a transcript into the value it is sorted by
    reverse: bool


# In the order the sort menu shows them.
#
# "Date added" goes by the transcript's id, since a transcript has no date of
# its own (see core/models.py). Ids are handed out in increasing order and are
# never reused, so id order is the order the transcripts were added in.
#
# "Most read" and "Most time spent reading" go by two of the totals the Stats
# tab shows (times_read and total_time_spent_seconds). Both only come most
# first: there is no everyday reason to want the least read ones at the top,
# so that direction was left out rather than making the menu twice as long.
SORT_ORDERS = {
    "title_az": SortOrder("Title (A–Z)", lambda t: t.title.lower(), False),
    "title_za": SortOrder("Title (Z–A)", lambda t: t.title.lower(), True),
    "newest": SortOrder("Date added (newest first)", lambda t: t.id, True),
    "oldest": SortOrder("Date added (oldest first)", lambda t: t.id, False),
    "most_read": SortOrder("Most read", lambda t: t.times_read, True),
    "most_time": SortOrder("Most time spent reading", lambda t: t.total_time_spent_seconds, True),
}

# The order the list had before it could be sorted at all, and still the one a
# new install starts with.
DEFAULT_SORT = "oldest"


def known_sort(sort_id) -> str:
    """sort_id if it is one of SORT_ORDERS, otherwise DEFAULT_SORT. Something
    odd in the settings file, or an order a newer version of the app added,
    reads as the default instead of breaking the list."""
    if isinstance(sort_id, str) and sort_id in SORT_ORDERS:
        return sort_id
    return DEFAULT_SORT


def sort_transcripts(transcripts, sort_id) -> list:
    """The transcripts in the order sort_id names, as a new list. Transcripts
    that tie, say two with the same title, stay in the order they came in."""
    order = SORT_ORDERS[known_sort(sort_id)]
    return sorted(transcripts, key=order.key, reverse=order.reverse)
