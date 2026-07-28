"""Saving must work no matter how sparse the existing store is.

An empty column in the store (nobody set a stage/tag yet) is inferred as float64;
pandas 3 then refuses to write text into it, so the very first save crashed.
"""

import pandas as pd

from yc_scouter import user_data


def test_first_save_into_a_store_with_empty_columns(tmp_path):
    path = tmp_path / "notes.csv"
    # only a flag was ever set: my_tags / my_stage / my_notes are empty -> float64
    user_data.save_user_data([{"id": 101, "watchlist": True}], path=path)

    store = user_data._ensure_columns(user_data.load_user_data(path)).set_index("id")
    store.loc[101] = {
        "watchlist": True,
        "my_stage": "Passed",  # text into a previously all-empty column
        "my_tags": "fav",
        "my_notes": "first note",
    }
    user_data.save_user_data(store.reset_index(), path=path)

    back = user_data.load_user_data(path).set_index("id")
    assert back.loc[101, "my_stage"] == "Passed"
    assert back.loc[101, "my_notes"] == "first note"


def test_save_into_a_completely_empty_store(tmp_path):
    path = tmp_path / "notes.csv"
    store = user_data._ensure_columns(user_data.empty_user_frame()).set_index("id")
    store.loc[7] = {
        "watchlist": True,
        "my_stage": "Contacted",
        "my_tags": "new",
        "my_notes": "text",
    }
    user_data.save_user_data(store.reset_index(), path=path)

    back = user_data.load_user_data(path).set_index("id")
    assert back.loc[7, "my_stage"] == "Contacted"


def test_text_columns_are_object_dtype_so_assignment_never_upcasts():
    frame = user_data._ensure_columns(pd.DataFrame([{"id": 1}]))
    for col in ("watchlist", "my_tags", "my_stage", "my_notes"):
        assert frame[col].dtype == object, col
