"""Edge cases the adversarial audit found in the dashboard's filters.

Two classes of bug, both silent (no traceback — just wrong results):

* list-valued cells. Parquet hands ``tags`` back as a **numpy array**, not a list,
  so the search used to fall back to ``str(array)`` and match its repr — typing
  ``[`` returned every company;
* an unknown ``team_size`` was read as ``0``, so companies whose size YC doesn't
  publish quietly passed an explicit "up to N" filter.
"""

import numpy as np
import pandas as pd

from yc_scouter import filters


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": "Alpha",
                "one_liner": "robotics for farms",
                "long_description": "",
                "tags": np.array(["AI", "B2B"], dtype=object),
                "my_tags": "",
                "my_notes": "",
                "team_size": 5,
                "custom_score": 50,
            },
            {
                "name": "Beta",
                "one_liner": "payments",
                "long_description": "",
                "tags": np.array(["Fintech"], dtype=object),
                "my_tags": "",
                "my_notes": "",
                "team_size": None,  # YC publishes nothing for this one
                "custom_score": 60,
            },
        ]
    )


def test_search_does_not_match_the_repr_of_an_array_cell():
    """`[`, `'` and `,` are part of an array's repr — never of the data."""
    for needle in ("[", "'", "', '"):
        assert filters.apply_filters(_df(), query=needle).empty, needle


def test_search_still_finds_words_inside_array_cells():
    assert filters.apply_filters(_df(), query="fintech")["name"].tolist() == ["Beta"]
    assert filters.apply_filters(_df(), query="b2b")["name"].tolist() == ["Alpha"]


def test_search_treats_regex_metacharacters_literally():
    df = _df()
    df.loc[0, "one_liner"] = "a.b (c)"
    assert filters.apply_filters(df, query="a.b (c)")["name"].tolist() == ["Alpha"]
    assert filters.apply_filters(df, query=".*").empty


def test_unknown_team_size_is_not_zero():
    """An explicit bound must not be passed by a company we have no size for."""
    upper = filters.apply_filters(_df(), max_team_size=3)
    assert upper["name"].tolist() == [], "unknown size sneaked past 'up to 3'"

    within = filters.apply_filters(_df(), min_team_size=1, max_team_size=10)
    assert within["name"].tolist() == ["Alpha"]

    # No bound at all -> unknowns are kept, nothing is hidden silently.
    assert len(filters.apply_filters(_df())) == 2


def test_tags_from_an_array_cell_are_parsed_as_tags():
    df = _df()
    df["my_tags"] = [np.array(["ai", "hot"], dtype=object), ""]
    assert filters.all_tags(df) == ["ai", "hot"]
    assert filters.apply_filters(df, tags=["hot"])["name"].tolist() == ["Alpha"]
