"""Tests for the pure filter/search helpers used by the Streamlit app."""

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
