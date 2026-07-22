"""Tests for the interestingness score."""

import pandas as pd

from yc_radar import score


def _rows():
    high = {
        "top_company": True,
        "batch_year": 2026,
        "is_hiring": True,
        "team_size": 40,
        "long_description": "A" * 80,
        "tags": ["AI", "DevTools", "B2B"],
    }
    low = {
        "top_company": False,
        "batch_year": 2024,
        "is_hiring": False,
        "team_size": pd.NA,
        "long_description": "",
        "tags": [],
    }
    return pd.DataFrame([high, low])


def test_score_in_range_and_ordered():
    df = score.score(_rows())
    assert df["score"].between(0, 100).all()
    assert df.loc[0, "score"] > df.loc[1, "score"]


def test_score_is_deterministic():
    a = score.score(_rows())["score"].tolist()
    b = score.score(_rows())["score"].tolist()
    assert a == b


def test_custom_weights_change_result():
    df = _rows()
    only_recency = {
        "top_company": 0,
        "recency": 1,
        "hiring": 0,
        "team": 0,
        "description": 0,
        "tags": 0,
    }
    out = score.score(df, weights=only_recency)
    # 2026 -> full recency (100), 2024 -> lowest
    assert out.loc[0, "score"] == 100.0
    assert out.loc[0, "score"] > out.loc[1, "score"]
