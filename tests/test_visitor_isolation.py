"""Visitors and the owner must never see or overwrite each other's notes.

Contract:
* a VISITOR's notes live only in their browser session (st.session_state);
* a visitor never reads the owner's notes and never writes into the shared store;
* the OWNER keeps using the shared store (local CSV here; Google Sheets in prod).
"""

import app
import pandas as pd
import pytest
import streamlit as st

from yc_scouter import user_data


@pytest.fixture(autouse=True)
def clean_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


@pytest.fixture
def owner_store(tmp_path, monkeypatch):
    """A shared store that already holds one of the owner's notes."""
    path = tmp_path / "owner_notes.csv"
    user_data.save_user_data(
        [{"id": 101, "watchlist": True, "my_tags": "секрет", "my_notes": "заметка владельца"}],
        path=path,
    )
    monkeypatch.setattr(app, "USER_DATA_CSV", path)
    monkeypatch.setattr(app, "use_gsheets", lambda: False)
    return path


def _as_visitor(monkeypatch):
    monkeypatch.setattr(app, "is_owner", lambda: False)


def _as_owner(monkeypatch):
    monkeypatch.setattr(app, "is_owner", lambda: True)


def test_visitor_does_not_see_owner_notes(owner_store, monkeypatch):
    _as_visitor(monkeypatch)
    notes = app.load_annotations()
    assert notes.empty, "a visitor must start from a blank slate"
    assert "заметка владельца" not in notes.to_csv()


def test_visitor_save_never_touches_the_shared_store(owner_store, monkeypatch):
    _as_visitor(monkeypatch)
    before = owner_store.read_text()

    app.save_one(
        202, {"watchlist": True, "my_stage": "Contacted", "my_tags": "", "my_notes": "моё"}
    )

    assert owner_store.read_text() == before, "visitor wrote into the owner's store"
    session = st.session_state[app.VISITOR_STORE].set_index("id")
    assert session.loc[202, "my_notes"] == "моё"
    assert bool(session.loc[202, "watchlist"]) is True


def test_visitor_notes_apply_within_the_session(owner_store, monkeypatch):
    _as_visitor(monkeypatch)
    app.save_one(202, {"watchlist": True, "my_stage": "Passed", "my_tags": "тег", "my_notes": "x"})

    companies = pd.DataFrame([{"id": 101, "name": "A"}, {"id": 202, "name": "B"}])
    merged = user_data.merge_annotations(companies, app.load_annotations()).set_index("id")

    assert bool(merged.loc[202, "watchlist"]) is True  # the visitor's own edit sticks
    assert merged.loc[202, "my_stage"] == "Passed"
    assert bool(merged.loc[101, "watchlist"]) is False  # owner's favourite not leaked
    assert merged.loc[101, "my_notes"] == ""


def test_owner_still_reads_and_writes_the_shared_store(owner_store, monkeypatch):
    _as_owner(monkeypatch)
    loaded = app.load_annotations().set_index("id")
    assert loaded.loc[101, "my_notes"] == "заметка владельца"

    app.save_one(
        101, {"watchlist": False, "my_stage": "Passed", "my_tags": "", "my_notes": "обновил"}
    )

    on_disk = user_data.load_user_data(owner_store).set_index("id")
    assert on_disk.loc[101, "my_notes"] == "обновил"
    assert app.VISITOR_STORE not in st.session_state


def test_owner_edits_do_not_bleed_into_a_visitor_session(owner_store, monkeypatch):
    _as_owner(monkeypatch)
    app.save_one(
        101, {"watchlist": True, "my_stage": "Invested", "my_tags": "", "my_notes": "приватно"}
    )

    _as_visitor(monkeypatch)
    assert app.load_annotations().empty
