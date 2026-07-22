"""Tests for normalize: typed DataFrame, batch-year parse, filter, dedup."""

import pandas as pd

from yc_radar import normalize


def test_parse_batch_year_full_words():
    assert normalize.parse_batch_year("Winter 2024") == 2024
    assert normalize.parse_batch_year("Summer 2025") == 2025
    assert normalize.parse_batch_year("Fall 2024") == 2024
    assert normalize.parse_batch_year("Spring 2026") == 2026


def test_parse_batch_year_short_forms():
    assert normalize.parse_batch_year("S25") == 2025
    assert normalize.parse_batch_year("W24") == 2024
    assert normalize.parse_batch_year("X25") == 2025


def test_parse_batch_year_unknown_returns_none():
    assert normalize.parse_batch_year("") is None
    assert normalize.parse_batch_year("IK12") is None
    assert normalize.parse_batch_year(None) is None


def test_normalize_filters_to_target_years(sample_records):
    df = normalize.normalize(sample_records)
    assert set(df["batch_year"].unique()) <= {2024, 2025, 2026}
    assert "old-co" not in df["slug"].values  # 2012 filtered out


def test_normalize_dedupes_by_slug(sample_records):
    df = normalize.normalize(sample_records)
    assert df["slug"].is_unique
    assert (df["slug"] == "acme-ai").sum() == 1


def test_normalize_renames_and_types(sample_records):
    df = normalize.normalize(sample_records)
    for col in normalize.CORE_COLUMNS:
        assert col in df.columns, f"missing column {col}"
    # renamed fields
    assert "is_hiring" in df.columns and "isHiring" not in df.columns
    assert "yc_url" in df.columns
    # team_size numeric & nullable
    assert pd.api.types.is_integer_dtype(df["team_size"])
    noweb = df[df["slug"] == "noweb-nonprofit"].iloc[0]
    assert pd.isna(noweb["team_size"])


def test_normalize_custom_years(sample_records):
    df = normalize.normalize(sample_records, years=(2026,))
    assert set(df["batch_year"].unique()) == {2026}
    assert df["slug"].tolist() == ["epsilon-26"]
