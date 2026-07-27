"""Comparison and the sidebar pickers must handle real-world duplicates.

* 57 companies in the live dataset share a name with another one. The comparison
  tab indexed by ``name``, so picking one of them compared several and produced a
  frame with duplicate columns — which crashes the renderer.
* Choosing an industry rewrites the subindustry options, and Streamlit drops the
  whole selection when options change; the still-valid part must survive.
"""

import app
import pandas as pd


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": 1, "name": "Vera", "batch": "Winter 2021", "score": 10},
            {"id": 2, "name": "Vera", "batch": "Summer 2023", "score": 20},
            {"id": 3, "name": "Solo", "batch": "Winter 2021", "score": 30},
        ]
    )


def test_labels_are_unique_even_when_names_repeat():
    labels = app.compare_labels(_df())
    assert len(labels) == 3, labels
    assert sorted(labels.values()) == [1, 2, 3]


def test_labels_stay_unique_when_name_and_batch_both_repeat():
    df = _df()
    df.loc[1, "batch"] = "Winter 2021"  # same name AND same batch as row 0
    labels = app.compare_labels(df)
    assert len(labels) == 3
    assert sorted(labels.values()) == [1, 2, 3]


def test_a_label_points_at_exactly_one_company():
    df = _df()
    labels = app.compare_labels(df)
    for label, cid in labels.items():
        rows = df[df["id"] == cid]
        assert len(rows) == 1, label


def test_comparison_frame_has_one_column_per_picked_company():
    df = _df()
    labels = app.compare_labels(df)
    picked = [label for label, cid in labels.items() if cid in (1, 2)]
    comp = app.comparison_frame(df, labels, picked, ["score"])
    assert list(comp.columns) == picked, "duplicate names must not collapse into one column"
    assert comp.loc["score"].tolist() == [10, 20]


def test_keep_valid_preserves_what_still_exists():
    assert app.keep_valid(["Robotics", "Payments"], ["Robotics", "Drones"]) == ["Robotics"]
    assert app.keep_valid([], ["Robotics"]) == []
    assert app.keep_valid(["Robotics"], ["Robotics"]) == ["Robotics"]
