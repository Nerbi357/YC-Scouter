"""The dashboard must survive an imperfect dataset and a changing result set.

Audit findings covered here:

* a duplicated company ``id`` produced two widgets with the same key
  (``DuplicateWidgetID``) and took the whole app down;
* a column missing after a pipeline change killed the app with a ``KeyError``
  instead of degrading;
* ``st.dataframe`` remembers the selected **row position**, so after a filter
  change the card opened a different company than the one highlighted.
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


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ------------------------------------------------------------------- prepare_data
def test_duplicate_ids_are_collapsed_with_a_warning():
    df, notes = app.prepare_data(
        _df([{"id": 1, "name": "A"}, {"id": 1, "name": "A (dup)"}, {"id": 2, "name": "B"}])
    )
    assert df["id"].tolist() == [1, 2], "duplicate ids would collide as widget keys"
    assert any("duplicate" in n.lower() for n in notes), notes


def test_rows_without_a_usable_id_are_dropped():
    df, notes = app.prepare_data(_df([{"id": None, "name": "A"}, {"id": 3, "name": "B"}]))
    assert df["id"].tolist() == [3]
    assert notes


def test_missing_optional_columns_are_filled_not_fatal():
    df, notes = app.prepare_data(_df([{"id": 1, "name": "A"}]))
    for col in (
        "industry",
        "subindustry",
        "status",
        "batch",
        "custom_score",
        "team_size",
        "ai_risks",
    ):
        assert col in df.columns, col
    assert app.sidebar_filters is not None  # the filters read exactly these columns
    assert any("column" in n.lower() for n in notes), notes


def test_a_dataset_without_id_or_name_is_reported_not_crashed():
    with pytest.raises(app.DatasetError) as err:
        app.prepare_data(_df([{"name": "A"}]))
    assert "id" in str(err.value)


def test_prepare_data_keeps_good_data_untouched():
    full = dict.fromkeys(app.OPTIONAL_DEFAULTS, "")
    good = _df(
        [
            {**full, "id": 1, "name": "A", "custom_score": 10},
            {**full, "id": 2, "name": "B", "custom_score": 20},
        ]
    )
    df, notes = app.prepare_data(good)
    assert notes == [], "a healthy dataset must not be flagged"
    assert df["name"].tolist() == ["A", "B"] and df["custom_score"].tolist() == [10, 20]


# ---------------------------------------------------------------- table selection
def test_selection_key_changes_with_the_result_set():
    a = _df([{"id": 1}, {"id": 2}])
    b = _df([{"id": 2}, {"id": 3}])
    assert app._selection_key("t", a) == app._selection_key("t", a)
    assert app._selection_key("t", a) != app._selection_key("t", b), (
        "a stale row position must not survive a filter change"
    )


def test_selection_key_forgets_the_previous_result_sets_state():
    a = _df([{"id": 1}, {"id": 2}])
    key_a = app._selection_key("t", a)
    st.session_state[key_a] = {"selection": {"rows": [1], "columns": []}}

    key_b = app._selection_key("t", _df([{"id": 5}]))

    assert key_a not in st.session_state, "old selection state leaks into the new table"
    assert key_b != key_a


def test_a_dataset_from_before_the_rename_still_opens():
    """`data/` is an archive: every dated file there must stay readable.

    The column became ``custom_score`` to make clear it is this project's opinion and
    not something YC publishes. Older files carry ``score`` — mapping them beats
    filling the column with blanks, which would silently show every archived company
    as unscored.
    """
    old = pd.DataFrame(
        [{"id": 1, "name": "A", "score": 42.5}, {"id": 2, "name": "B", "score": 7.0}]
    )
    out, _ = app.prepare_data(old)
    assert out["custom_score"].tolist() == [42.5, 7.0]
    assert "score" not in out.columns
