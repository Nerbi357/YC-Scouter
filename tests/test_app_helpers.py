"""Tests for the pure filter/search helpers used by the Streamlit app."""

import pandas as pd

from yc_radar import enrich, filters, normalize, score


def _full_df(sample_records):
    df = normalize.normalize(sample_records)
    df = enrich.add_investability(df)
    df = enrich.add_links(df)
    return score.score(df)


def test_filter_by_status(sample_records):
    out = filters.apply_filters(_full_df(sample_records), statuses=["Public"])
    assert out["slug"].tolist() == ["delta-public"]


def test_filter_by_batch_year(sample_records):
    out = filters.apply_filters(_full_df(sample_records), batch_years=[2026])
    assert out["slug"].tolist() == ["epsilon-26"]


def test_filter_min_score_reduces_rows(sample_records):
    df = _full_df(sample_records)
    hi = filters.apply_filters(df, min_score=df["score"].max())
    assert len(hi) < len(df)
    assert (hi["score"] >= df["score"].max()).all()


def test_search_matches_description_case_insensitive(sample_records):
    out = filters.apply_filters(_full_df(sample_records), query="ROBOT")
    assert "acme-ai" in out["slug"].tolist()


def test_no_filters_returns_all(sample_records):
    df = _full_df(sample_records)
    assert len(filters.apply_filters(df)) == len(df)


def test_filter_by_investability(sample_records):
    df = _full_df(sample_records)
    tier = df["investability"].iloc[0]
    out = filters.apply_filters(df, investabilities=[tier])
    assert (out["investability"] == tier).all()
    assert len(out) >= 1


def test_filter_by_subindustry(sample_records):
    df = _full_df(sample_records)
    sub = df["subindustry"].dropna().iloc[0]
    out = filters.apply_filters(df, subindustries=[sub])
    assert (out["subindustry"] == sub).all()


def test_score_range_bounds(sample_records):
    df = _full_df(sample_records)
    lo, hi = 10, 40
    out = filters.apply_filters(df, min_score=lo, max_score=hi)
    assert out["score"].between(lo, hi).all()


def test_watchlist_only(sample_records):
    df = _full_df(sample_records)
    df["watchlist"] = False
    df.loc[df.index[0], "watchlist"] = True
    out = filters.apply_filters(df, watchlist_only=True)
    assert len(out) == 1 and bool(out["watchlist"].iloc[0])


def test_filter_by_tags_and_stage(sample_records):
    df = _full_df(sample_records)
    df["my_tags"] = ""
    df["my_stage"] = "New"
    df.loc[df.index[0], "my_tags"] = "favorite, deep-tech"
    df.loc[df.index[0], "my_stage"] = "Contacted"
    by_tag = filters.apply_filters(df, tags=["favorite"])
    assert len(by_tag) == 1
    by_stage = filters.apply_filters(df, stages=["Contacted"])
    assert len(by_stage) == 1


def test_split_and_all_tags():
    assert filters.split_tags("ai, fintech ,, ") == ["ai", "fintech"]
    assert filters.split_tags(None) == []
    df = pd.DataFrame({"my_tags": ["ai, fintech", "ai", ""]})
    assert filters.all_tags(df) == ["ai", "fintech"]
