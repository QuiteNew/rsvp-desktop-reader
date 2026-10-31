"""Tests for remembering how the sidebar sorts the transcripts: the orders in
core/transcript_sort.py, the setting that holds the choice
(core/settings_store.py), the sidebar list (gui/components/transcript_list_body.py)
and the app between them (gui/app.py).

What was agreed: the order picked from the sidebar's sort menu is remembered,
and the list comes back in it at the next launch. On top of that: it is one
order for the whole sidebar, not one per space, and the search text is still
not remembered. A new install, and a settings file with something odd in this
spot, get the order the list always had, oldest first.

One test builds the real app. After it, the list runs against a real Tk with
one hidden root for the rest of the module, the same as
test_transcript_list_current.py."""

import json
import tkinter

import customtkinter as ctk
import pytest

from core.models import Transcript
from core.profiles import PROFILE_KEYS
from core.settings_store import AppSettings, SettingsStore
from core.transcript_sort import DEFAULT_SORT, SORT_ORDERS, known_sort, sort_transcripts


def _transcript(id, title, times_read=0, seconds=0):
    return Transcript(id=id, title=title, space="General", times_read=times_read, total_time_spent_seconds=seconds)


TRANSCRIPTS = [
    _transcript(1, "beta", times_read=2, seconds=300),
    _transcript(2, "Alpha", times_read=5, seconds=100),
    _transcript(3, "gamma", times_read=1, seconds=900),
]


def ids(transcripts):
    return [t.id for t in transcripts]


# ---- the orders (core/transcript_sort.py) ----

@pytest.mark.parametrize("sort_id, expected", [
    ("title_az", [2, 1, 3]),  # upper and lower case sort together
    ("title_za", [3, 1, 2]),
    ("newest", [3, 2, 1]),
    ("oldest", [1, 2, 3]),
    ("most_read", [2, 1, 3]),
    ("most_time", [3, 1, 2]),
])
def test_each_order_sorts_the_way_its_label_says(sort_id, expected):
    assert ids(sort_transcripts(TRANSCRIPTS, sort_id)) == expected


def test_the_menu_shows_the_same_six_orders_in_the_same_order_as_before():
    assert [order.label for order in SORT_ORDERS.values()] == [
        "Title (A–Z)", "Title (Z–A)", "Date added (newest first)",
        "Date added (oldest first)", "Most read", "Most time spent reading",
    ]


def test_the_default_is_the_order_the_list_always_had():
    assert DEFAULT_SORT == "oldest"
    assert SORT_ORDERS[DEFAULT_SORT].label == "Date added (oldest first)"


@pytest.mark.parametrize("odd", ["", "Title (A–Z)", "TITLE_AZ", None, 3, ["title_az"]])
def test_anything_that_is_not_a_known_id_reads_as_the_default(odd):
    assert known_sort(odd) == DEFAULT_SORT
    assert ids(sort_transcripts(TRANSCRIPTS, odd)) == [1, 2, 3]


def test_every_id_is_known():
    for sort_id in SORT_ORDERS:
        assert known_sort(sort_id) == sort_id


def test_transcripts_that_tie_keep_the_order_they_came_in():
    tied = [_transcript(1, "same"), _transcript(2, "Same"), _transcript(3, "same")]
    assert ids(sort_transcripts(tied, "title_az")) == [1, 2, 3]
    assert ids(sort_transcripts(tied, "title_za")) == [1, 2, 3]
    assert ids(sort_transcripts(tied, "most_read")) == [1, 2, 3]


def test_sorting_gives_a_new_list_and_leaves_the_old_one_alone():
    given = list(TRANSCRIPTS)
    result = sort_transcripts(given, "newest")
    assert result is not given
    assert ids(given) == [1, 2, 3]


# ---- the setting (core/settings_store.py) ----

@pytest.fixture
def settings(tmp_path):
    return SettingsStore(str(tmp_path / "settings"))


def test_a_new_install_starts_oldest_first(settings):
    assert AppSettings().transcript_sort == DEFAULT_SORT
    assert settings.transcript_sort == DEFAULT_SORT


def test_the_order_is_saved_and_survives_a_restart(settings, tmp_path):
    settings.set_transcript_sort("most_time")
    assert SettingsStore(str(tmp_path / "settings")).transcript_sort == "most_time"


@pytest.mark.parametrize("odd", ["Most read", "sideways", 1, True, None])
def test_an_odd_value_in_the_file_reads_as_the_default(settings, odd):
    settings._settings.transcript_sort = odd
    assert settings.transcript_sort == DEFAULT_SORT


def test_picking_the_order_already_in_use_does_not_write_the_file(settings, monkeypatch):
    settings.set_transcript_sort("title_az")
    writes = []
    monkeypatch.setattr(settings, "_save", lambda: writes.append(1))
    settings.set_transcript_sort("title_az")
    assert writes == []
    settings.set_transcript_sort("newest")
    assert writes == [1]


def test_an_old_settings_file_without_it_gets_the_default(tmp_path):
    folder = tmp_path / "settings"
    folder.mkdir()
    old = {key: value for key, value in vars(AppSettings()).items() if key != "transcript_sort"}
    old["default_wpm"] = 450
    (folder / "settings.json").write_text(json.dumps(old), encoding="utf-8")
    loaded = SettingsStore(str(folder))
    assert loaded.transcript_sort == DEFAULT_SORT
    assert loaded.default_wpm == 450


def test_the_order_is_not_part_of_a_reading_profile():
    assert "transcript_sort" not in PROFILE_KEYS


# ---- the app (gui/app.py) ----

def test_the_app_opens_in_the_saved_order_and_saves_a_new_one(tmp_path, open_real_app):
    """This comes before the list tests on purpose. They share one Tk root for
    the rest of the module, and the app has to be the only root while it is
    up, because CustomTkinter ties fonts and pictures to the first one."""
    def save_an_order():
        SettingsStore().set_transcript_sort("title_za")

    with open_real_app(tmp_path, before_start=save_an_order) as application:
        assert application.list_body._sort == "title_za"
        application.list_body._handle_sort_selected("most_read")
        saved = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
        assert saved["transcript_sort"] == "most_read"


# ---- the sidebar list (gui/components/transcript_list_body.py) ----


@pytest.fixture
def make_list(root):
    """Builds the sidebar list in a window of its own, with the transcripts in
    it, and takes the window down again afterwards."""
    from gui.components.transcript_list_body import TranscriptListBody

    windows = []

    def make(**options):
        top = ctk.CTkToplevel(root)
        top.withdraw()
        widget = TranscriptListBody(top, **options)
        widget.pack(fill="both", expand=True)
        widget.render_transcripts(TRANSCRIPTS)
        windows.append(top)
        return widget

    yield make
    for top in windows:
        for timer in top.tk.splitlist(top.tk.call("after", "info")):
            top.tk.call("after", "cancel", timer)
        top.destroy()


def shown_ids(body):
    return list(body._rows)


def test_the_list_starts_in_the_order_it_is_given(make_list):
    assert shown_ids(make_list(sort="title_za")) == [3, 1, 2]


def test_without_an_order_the_list_starts_oldest_first(make_list):
    assert shown_ids(make_list()) == [1, 2, 3]


def test_an_unknown_order_starts_oldest_first(make_list):
    body = make_list(sort="sideways")
    assert shown_ids(body) == [1, 2, 3]
    assert body._sort == DEFAULT_SORT  # so the menu ticks it


def test_picking_an_order_sorts_the_list_and_reports_it(make_list):
    picked = []
    body = make_list(on_sort_changed=picked.append)
    body._handle_sort_selected("most_read")
    assert shown_ids(body) == [2, 1, 3]
    assert picked == ["most_read"]


def test_a_list_nobody_listens_to_still_sorts(make_list):
    body = make_list()
    body._handle_sort_selected("newest")
    assert shown_ids(body) == [3, 2, 1]


def test_the_order_stays_when_the_list_is_given_again(make_list):
    body = make_list(sort="title_az")
    body.render_transcripts(TRANSCRIPTS)
    assert shown_ids(body) == [2, 1, 3]


def test_the_menu_offers_every_order_with_the_one_in_use_ticked(make_list, monkeypatch):
    """The menu is built for real, but stopped just before it would pop up and
    take over the mouse. What is ticked is read at that moment, while the menu
    would be open, because the variable behind the ticks only lasts that long."""
    import gui.components.transcript_list_body as body_module

    built, ticked = [], []

    class _Menu(tkinter.Menu):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            built.append(self)

        def tk_popup(self, *args):
            ticked.append(self.getvar(self.entrycget(0, "variable")))

    monkeypatch.setattr(body_module.tk, "Menu", _Menu)
    body = make_list(sort="most_time")
    body._show_sort_menu()
    menu = built[0]
    labels = [menu.entrycget(index, "label") for index in range(menu.index("end") + 1)]
    assert labels == [order.label for order in SORT_ORDERS.values()]
    assert ticked == ["most_time"]
    menu.invoke(labels.index("Title (A–Z)"))
    assert shown_ids(body) == [2, 1, 3]
    menu.destroy()
