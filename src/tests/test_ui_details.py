"""Small UI contracts the owner reported as broken.

* the pager offered "Next →" on the last page (the button's disabled state was
  computed *before* the click was applied, so it stayed active for one render);
* the batch-year chart drew fractional years (2020.5) — Plotly reads numeric-looking
  labels as a continuous axis, which is nonsense for a year, and obvious when a
  single year is selected;
* saving a note gave no confirmation: the success message was wiped by the rerun
  that refreshes the stars and counters.
"""

import app
import pandas as pd
import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def clean_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


# --------------------------------------------------------------------------- pager
def test_page_step_never_leaves_the_valid_range():
    st.session_state["card_page"] = 3
    app._step_page(1, pages=3)
    assert st.session_state["card_page"] == 3, "there is no page 4"
    app._step_page(-1, pages=3)
    assert st.session_state["card_page"] == 2
    app._step_page(-5, pages=3)
    assert st.session_state["card_page"] == 1


def test_page_step_runs_before_the_buttons_are_drawn():
    """It must be an on_click callback — that is what fixes the stale button."""
    import inspect

    src = inspect.getsource(app._page_number)
    assert "on_click=_step_page" in src, "the pager must update the page in a callback"
    assert "disabled=page >= pages" in src


# ---------------------------------------------------------------------- year chart
def test_batch_year_axis_is_categorical():
    df = pd.DataFrame({"batch_year": [2021] * 3})
    fig = app.year_bar(df)
    assert fig is not None
    assert fig.layout.xaxis.type == "category", "a continuous axis invents 2020.5"
    assert list(fig.data[0].x) == ["2021"]


def test_batch_year_chart_handles_several_years_in_order():
    df = pd.DataFrame({"batch_year": [2022, 2020, 2021, 2020]})
    fig = app.year_bar(df)
    assert list(fig.data[0].x) == ["2020", "2021", "2022"]
    assert list(fig.data[0].y) == [2, 1, 1]


def test_batch_year_chart_is_skipped_when_there_is_nothing_to_draw():
    assert app.year_bar(pd.DataFrame({"batch_year": [None, None]})) is None


# -------------------------------------------------------------------- saved flash
def test_saved_flash_is_shown_for_the_saved_company_only():
    assert app._flash_is_fresh((7, 100.0), 7, now=105.0, ttl=60) is True
    assert app._flash_is_fresh((7, 100.0), 8, now=105.0, ttl=60) is False


def test_saved_flash_expires():
    assert app._flash_is_fresh((7, 100.0), 7, now=100.0 + 61, ttl=60) is False
    assert app._flash_is_fresh(None, 7, now=100.0, ttl=60) is False


def test_mark_saved_records_the_company():
    app.mark_saved(42)
    cid, _stamp = st.session_state[app.SAVED_FLASH]
    assert cid == 42
    assert app.saved_recently(42) is True
    assert app.saved_recently(43) is False


# --------------------------------------------------------------- notes pagination
def test_paginate_returns_the_right_slice():
    df = pd.DataFrame({"id": range(120)})
    chunk, start, pages = app.paginate(df, page=2, size=50)
    assert pages == 3 and start == 50
    assert chunk["id"].tolist() == list(range(50, 100))


def test_paginate_clamps_and_survives_an_empty_frame():
    df = pd.DataFrame({"id": range(10)})
    chunk, start, pages = app.paginate(df, page=99, size=50)
    assert pages == 1 and start == 0 and len(chunk) == 10
    chunk, start, pages = app.paginate(pd.DataFrame({"id": []}), page=1, size=50)
    assert pages == 1 and start == 0 and chunk.empty


def test_pagers_do_not_share_state():
    st.session_state["card_page"] = 3
    st.session_state["notes_page"] = 1
    app._step_page(1, pages=5, key="notes_page")
    assert st.session_state["notes_page"] == 2
    assert st.session_state["card_page"] == 3, "the card pager must not move"


def test_notes_editor_key_follows_the_visible_rows():
    """st.data_editor stores edits by row *position*.

    With a fixed key, edits made before a filter change would be replayed onto
    whichever companies now sit at those positions.
    """
    import inspect

    src = inspect.getsource(app.tab_notes)
    assert '_selection_key("annotations_editor"' in src
