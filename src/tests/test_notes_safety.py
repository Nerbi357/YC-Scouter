"""The shared notes store must never be destroyed by a failure or a stranger.

Audit findings covered here:

* a failed Sheets *read* returned an empty frame, and the next save happily wrote
  that emptiness over every note in the sheet;
* :func:`yc_scouter.gsheets.save` cleared the sheet **before** writing, so a crash
  in between left it blank;
* with the notes going to a shared sheet, a missing/misspelled ``owner_key`` made
  every visitor an owner — the gate has to fail *closed*;
* every rerun did a fresh (uncached) Sheets read.
"""

import app
import pandas as pd
import pytest
import streamlit as st

from yc_scouter import gsheets, user_data


@pytest.fixture(autouse=True)
def clean_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


class FakeWorksheet:
    """Minimal gspread worksheet: remembers the call order and the grid."""

    def __init__(self, rows: list[list[str]] | None = None):
        self.rows = rows or [list(user_data.USER_COLUMNS)]
        self.calls: list[str] = []

    def get_all_values(self):
        return [list(r) for r in self.rows]

    def get_all_records(self):
        header, *body = self.rows
        return [dict(zip(header, r, strict=False)) for r in body]

    def update(self, values, range_name=None, **kw):
        self.calls.append("update")
        grid = [list(r) for r in values]
        keep = self.rows[len(grid) :]
        self.rows = grid + [list(r) for r in keep]

    def batch_clear(self, ranges):
        self.calls.append("batch_clear")
        first = int(ranges[0].split(":")[0][1:])
        self.rows = self.rows[: first - 1]

    def clear(self):
        self.calls.append("clear")
        self.rows = []


def _sheet_with_notes() -> FakeWorksheet:
    return FakeWorksheet(
        [
            list(user_data.USER_COLUMNS),
            ["101", "TRUE", "secret", "Contacted", "owner note"],
            ["202", "FALSE", "", "New", "second"],
        ]
    )


# ------------------------------------------------------------------ gsheets.save
def test_save_refuses_to_erase_a_populated_sheet(monkeypatch):
    ws = _sheet_with_notes()
    monkeypatch.setattr(gsheets, "_open_worksheet", lambda s: ws)

    with pytest.raises(ValueError, match="2"):
        gsheets.save({}, user_data.empty_user_frame())

    assert len(ws.rows) == 3, "the notes must still be there"
    assert "clear" not in ws.calls


def test_save_writes_before_clearing_leftovers(monkeypatch):
    ws = _sheet_with_notes()
    monkeypatch.setattr(gsheets, "_open_worksheet", lambda s: ws)

    gsheets.save({}, pd.DataFrame([{"id": 101, "my_notes": "one"}]))

    assert ws.calls[0] == "update", "the sheet must never be blanked before the write"
    assert "clear" not in ws.calls
    assert len(ws.rows) == 2, "the removed row must not linger"
    assert ws.rows[1][0] == "101"


def test_save_can_empty_the_sheet_when_asked(monkeypatch):
    ws = _sheet_with_notes()
    monkeypatch.setattr(gsheets, "_open_worksheet", lambda s: ws)
    gsheets.save({}, user_data.empty_user_frame(), allow_empty=True)
    assert ws.rows == [list(user_data.USER_COLUMNS)]


# ------------------------------------------------------- app-level read/write guard
def _configure_sheets(monkeypatch, *, owner=True):
    monkeypatch.setattr(app, "use_gsheets", lambda: True)
    monkeypatch.setattr(app, "is_owner", lambda: owner)


def test_a_failed_read_blocks_saving_instead_of_wiping(monkeypatch):
    _configure_sheets(monkeypatch)
    monkeypatch.setattr(app.gsheets, "load", lambda s: (_ for _ in ()).throw(RuntimeError("boom")))
    saved = []
    monkeypatch.setattr(app.gsheets, "save", lambda s, df, **k: saved.append(df))

    assert app.load_annotations().empty  # degrades, does not crash
    with pytest.raises(RuntimeError, match="unreadable"):
        app.save_annotations(user_data.empty_user_frame())
    assert saved == [], "nothing may be written while the store is unreadable"


def test_the_sheet_is_read_once_per_session_not_once_per_rerun(monkeypatch):
    _configure_sheets(monkeypatch)
    reads = []

    def _load(_secrets):
        reads.append(1)
        return pd.DataFrame([{"id": 101, "my_notes": "a"}])

    monkeypatch.setattr(app.gsheets, "load", _load)
    for _ in range(5):
        app.load_annotations()
    assert len(reads) == 1, f"{len(reads)} network reads for 5 reruns"

    monkeypatch.setattr(app.gsheets, "save", lambda s, df, **k: None)
    app.save_annotations(pd.DataFrame([{"id": 101, "my_notes": "b"}]))
    assert app.load_annotations().set_index("id").loc[101, "my_notes"] == "b"
    assert len(reads) == 1, "a save must refresh the cache, not re-read the sheet"

    app.refresh_annotations()
    app.load_annotations()
    assert len(reads) == 2, "the explicit refresh button must re-read"


# --------------------------------------------------------------------- owner gate
def test_owner_gate_fails_closed_on_a_shared_deployment(monkeypatch):
    """No key + a shared sheet = everyone is a visitor, not everyone an owner."""
    monkeypatch.setattr(app, "use_gsheets", lambda: True)
    for key in (None, "", "   "):
        monkeypatch.setattr(app, "_owner_key", lambda k=key: k)
        assert app.is_owner() is False, f"owner_key={key!r} let a stranger in"


def test_single_user_mode_stays_open_without_sheets(monkeypatch):
    monkeypatch.setattr(app, "use_gsheets", lambda: False)
    monkeypatch.setattr(app, "_owner_key", lambda: None)
    assert app.is_owner() is True  # local / Colab


def test_owner_unlocks_with_the_exact_key(monkeypatch):
    monkeypatch.setattr(app, "use_gsheets", lambda: True)
    monkeypatch.setattr(app, "_owner_key", lambda: "s3cret")
    assert app.is_owner() is False
    assert app.check_owner_key(" wrong ") is False
    assert app.is_owner() is False
    assert app.check_owner_key(" s3cret ") is True  # stray spaces from a paste
    assert app.is_owner() is True
