"""Tests for personal annotations that persist across data refreshes."""

import pandas as pd

from yc_radar import normalize, user_data


def test_merge_without_file_adds_empty_columns(tmp_path, sample_records):
    df = normalize.normalize(sample_records)
    out = user_data.merge_user_data(df, path=tmp_path / "user_data.csv")
    for col in ("my_rating", "watchlist", "my_notes"):
        assert col in out.columns
    assert (out["watchlist"] == False).all()  # noqa: E712
    assert (out["my_notes"] == "").all()


def test_save_and_merge_roundtrip(tmp_path, sample_records):
    path = tmp_path / "user_data.csv"
    user_data.save_user_data(
        [{"slug": "acme-ai", "my_rating": 5, "watchlist": True, "my_notes": "hot lead"}],
        path=path,
    )
    df = normalize.normalize(sample_records)
    out = user_data.merge_user_data(df, path=path).set_index("slug")
    assert out.loc["acme-ai", "my_rating"] == 5
    assert bool(out.loc["acme-ai", "watchlist"]) is True
    assert out.loc["acme-ai", "my_notes"] == "hot lead"


def test_refresh_preserves_annotations(tmp_path, sample_records):
    path = tmp_path / "user_data.csv"
    user_data.save_user_data(
        [{"slug": "gamma-labs", "my_rating": 4, "watchlist": True, "my_notes": "watch"}],
        path=path,
    )
    # simulate two independent pipeline refreshes
    for _ in range(2):
        df = normalize.normalize(sample_records)
        out = user_data.merge_user_data(df, path=path).set_index("slug")
        assert out.loc["gamma-labs", "my_rating"] == 4


def test_load_missing_returns_empty_schema(tmp_path):
    ud = user_data.load_user_data(tmp_path / "nope.csv")
    assert list(ud.columns) == list(user_data.USER_COLUMNS)
    assert len(ud) == 0
    assert isinstance(ud, pd.DataFrame)
