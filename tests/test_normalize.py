"""Tests for normalize: typed DataFrame, batch-year parse, filter, dedup."""

import pandas as pd

from yc_scouter import normalize


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


def test_normalize_filters_2020_to_current(sample_records):
    df = normalize.normalize(sample_records)
    # 2012 is filtered out; 2020 (left boundary) is kept.
    assert "old-co" not in df["slug"].values
    assert 2020 in set(df["batch_year"].unique())
    assert "twenty-twenty" in df["slug"].values
    assert df["batch_year"].min() >= 2020


def test_normalize_dedupes_by_id(sample_records):
    df = normalize.normalize(sample_records)
    # two source rows share id 101 (acme-ai + its dupe) -> collapse to one
    assert df["id"].is_unique
    assert (df["id"] == 101).sum() == 1


def test_normalize_stable_sort_by_id(sample_records):
    df = normalize.normalize(sample_records)
    ids = df["id"].tolist()
    assert ids == sorted(ids)  # deterministic ascending-id order


def test_normalize_renames_and_types(sample_records):
    df = normalize.normalize(sample_records)
    for col in normalize.CORE_COLUMNS:
        assert col in df.columns, f"missing column {col}"
    assert "id" in normalize.CORE_COLUMNS
    assert pd.api.types.is_integer_dtype(df["id"])
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
