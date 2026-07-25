"""Regressions for the defects the second (cross-verified) audit confirmed.

Each test fails without its fix. The two that matter most are first: notes being
silently deleted by a second session, and one click blanking the whole dashboard.
"""

import app
import pandas as pd
import pytest
import streamlit as st

from yc_scouter import export, filters, gsheets, user_data


@pytest.fixture(autouse=True)
def clean_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


class FakeWorksheet:
    """gspread worksheet double: a fixed grid that refuses writes beyond it."""

    def __init__(self, rows=None, row_count=1000):
        self.rows = rows or [list(user_data.USER_COLUMNS)]
        self.row_count = row_count
        self.calls = []

    def get_all_values(self):
        return [list(r) for r in self.rows]

    def get_all_records(self):
        header, *body = self.rows
        return [dict(zip(header, r, strict=False)) for r in body]

    def update(self, values, range_name=None, **kw):
        self.calls.append("update")
        if range_name:
            last = int("".join(c for c in range_name.split(":")[-1] if c.isdigit()))
            if last > self.row_count:
                raise RuntimeError(
                    f"exceeds grid limits: range {range_name} vs {self.row_count} rows"
                )
        grid = [list(r) for r in values]
        self.rows = grid + [list(r) for r in self.rows[len(grid) :]]

    def batch_clear(self, ranges):
        self.calls.append("batch_clear")
        first = int("".join(c for c in ranges[0].split(":")[0] if c.isdigit()))
        self.rows = self.rows[: first - 1]

    def resize(self, rows=None, cols=None):
        self.calls.append("resize")
        if rows:
            self.row_count = max(self.row_count, rows)


def _sheet(*records):
    rows = [list(user_data.USER_COLUMNS)] + [list(r) for r in records]
    return FakeWorksheet(rows)


# ------------------------------------------------------- 1. two sessions, one sheet
def test_a_save_does_not_delete_notes_written_by_another_session(monkeypatch):
    """The killer case: two tabs open, each saving a different company.

    Tab A holds a snapshot from before tab B wrote. Writing that snapshot back would
    erase tab B's company entirely — silently, with a success message.
    """
    ws = _sheet(["101", "TRUE", "fintech", "Contacted", "first meeting"])
    monkeypatch.setattr(gsheets, "_open_worksheet", lambda s: ws)
    monkeypatch.setattr(app, "use_gsheets", lambda: True)
    monkeypatch.setattr(app, "is_owner", lambda: True)

    app.load_annotations()  # tab A caches the sheet as it is now
    ws.rows.append(["303", "TRUE", "hot", "Invested", "wired the term sheet"])  # tab B saves

    app.save_one(
        101, {"watchlist": True, "my_stage": "Passed", "my_tags": "", "my_notes": "edited"}
    )

    ids = [r[0] for r in ws.rows[1:]]
    assert "303" in ids, "a save from a stale session deleted another session's note"
    saved = {r[0]: r for r in ws.rows[1:]}
    assert saved["101"][4] == "edited"
    assert saved["303"][4] == "wired the term sheet"


def test_a_save_survives_a_worksheet_smaller_than_the_store(monkeypatch):
    """The auto-created worksheet has 1000 rows; the store can be much larger."""
    ws = FakeWorksheet(row_count=1000)
    monkeypatch.setattr(gsheets, "_open_worksheet", lambda s: ws)
    big = pd.DataFrame({"id": range(1, 1501), "my_notes": ["x"] * 1500})

    gsheets.save({}, big)

    assert "resize" in ws.calls, "the grid must be grown before writing past it"
    assert len(ws.rows) == 1501


def test_upsert_touches_only_the_changed_companies():
    store = user_data._ensure_columns(
        pd.DataFrame([{"id": 1, "my_notes": "one"}, {"id": 2, "my_notes": "two"}])
    )
    out = user_data.upsert(store, {2: {"my_notes": "TWO"}, 3: {"my_notes": "three"}})
    by_id = out.set_index("id")
    assert by_id.loc[1, "my_notes"] == "one"  # untouched
    assert by_id.loc[2, "my_notes"] == "TWO"  # updated
    assert by_id.loc[3, "my_notes"] == "three"  # added
    assert len(out) == 3


def test_upsert_is_vectorised_not_row_by_row():
    """4000 changes must take milliseconds, not ~20 s of frame reallocation."""
    import time

    store = user_data._ensure_columns(pd.DataFrame({"id": range(4000)}))
    changes = {i: {"my_notes": "n"} for i in range(4000)}
    t = time.perf_counter()
    out = user_data.upsert(store, changes)
    assert time.perf_counter() - t < 2.0
    assert len(out) == 4000


# --------------------------------------------------- 2. the card close-button crash
def test_the_overview_table_and_card_live_in_a_fragment():
    """`st.rerun(scope="fragment")` outside a fragment raises and blanks the page."""
    import inspect

    src = inspect.getsource(app.tab_overview)
    assert "table_and_card(" in src, "the Overview card must be rendered inside the fragment"
    assert "detail_card(" not in src, "a bare detail_card here reruns the whole app"


def test_table_and_card_accepts_its_own_columns_and_table_rows():
    assert "cols" in app.table_and_card.__wrapped__.__code__.co_varnames
    assert "table_df" in app.table_and_card.__wrapped__.__code__.co_varnames


# --------------------------------------------------- 3. unreadable secrets, access
def test_unreadable_secrets_do_not_make_everyone_the_owner(monkeypatch):
    """A malformed secrets.toml used to read as "no secrets" -> single-user mode."""

    class Boom:
        def get(self, *a, **k):
            raise RuntimeError("Invalid format: please check your secrets file")

        def __contains__(self, k):
            raise RuntimeError("Invalid format")

    monkeypatch.setattr(app.st, "secrets", Boom())
    assert app.secrets_unreadable() is True
    assert app.is_owner() is False


def test_readable_but_empty_secrets_still_mean_single_user_mode(monkeypatch):
    monkeypatch.setattr(app.st, "secrets", {})
    assert app.secrets_unreadable() is False
    assert app.is_owner() is True


# ------------------------------------------------------------ 4. exports and arrays
def test_exports_render_array_cells_as_readable_text():
    """Parquet gives list columns back as numpy arrays, not lists."""
    import numpy as np

    df = pd.DataFrame({"id": [1], "tags": [np.array(["Bio", "Climate"], dtype=object)]})
    flat = export._flatten_for_sheet(df)
    assert flat.loc[0, "tags"] == "Bio, Climate"
    assert app._clean_cell(np.array(["Bio", "Climate"], dtype=object)) == "Bio, Climate"
    assert filters.is_sequence(np.array(["a"]))


# --------------------------------------------------------------- 5. hostile ids
def test_non_finite_and_out_of_range_ids_are_dropped_not_fatal():
    import numpy as np

    df = pd.DataFrame(
        {
            "id": [1, np.inf, -np.inf, 1e19, 2],
            "name": ["a", "b", "c", "d", "e"],
        }
    )
    out, notes = app.prepare_data(df)
    assert out["id"].tolist() == [1, 2]
    assert any("id" in n for n in notes)


# ------------------------------------------------- 6. a broken sheet is tried once
def test_an_unreachable_sheet_is_contacted_once_per_session(monkeypatch):
    monkeypatch.setattr(app, "use_gsheets", lambda: True)
    monkeypatch.setattr(app, "is_owner", lambda: True)
    calls = []

    def _boom(_secrets):
        calls.append(1)
        raise RuntimeError("connection timed out")

    monkeypatch.setattr(app.gsheets, "load", _boom)
    for _ in range(5):
        assert app.load_annotations().empty
    assert len(calls) == 1, f"the dead sheet was contacted {len(calls)} times"

    app.refresh_annotations()
    app.load_annotations()
    assert len(calls) == 2


# ------------------------------------------------- 7. the bulk save writes the diff
def test_bulk_save_writes_only_what_changed():
    before = pd.DataFrame(
        [
            {"id": 1, "watchlist": False, "my_stage": "New", "my_tags": "", "my_notes": ""},
            {"id": 2, "watchlist": False, "my_stage": "New", "my_tags": "", "my_notes": ""},
        ]
    )
    after = before.copy()
    after.loc[1, "my_notes"] = "called them"
    changes = app.changed_rows(before, after)
    assert list(changes) == [2], "an untouched company must not be rewritten"
    assert changes[2]["my_notes"] == "called them"
    assert app.changed_rows(before, before) == {}, "saving without edits must write nothing"


# ----------------------------------------------- 8. the ✕ actually closes the card
def test_closing_the_card_also_unticks_the_row():
    """Clearing only the selected id let the table re-select on the next rerun."""
    st.session_state["selected_id"] = 42
    st.session_state["table_all_deadbeef"] = {"selection": {"rows": [3], "columns": []}}

    app.close_card("table_all_deadbeef")

    assert app.selected_id() is None
    assert "table_all_deadbeef" not in st.session_state, "the row stayed ticked, card reopens"


def test_detail_card_receives_the_table_key():
    import inspect

    assert "table_key" in inspect.signature(app.detail_card).parameters
    src = inspect.getsource(app.table_and_card.__wrapped__)
    assert "table_key=table_key" in src
