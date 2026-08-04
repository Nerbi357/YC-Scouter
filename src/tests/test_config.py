"""Tests for the shared configuration / constants module."""

import datetime as dt
from pathlib import Path

from yc_scouter import config


def test_dated_path_builds_ascii_iso_name(tmp_path):
    p = config.dated_path("base", "2026-01-27", "parquet", out_dir=tmp_path)
    assert p == tmp_path / "yc_dataset_base_2026-01-27.parquet"
    p2 = config.dated_path("ai", dt.date(2026, 1, 27), "xlsx", out_dir=tmp_path)
    assert p2.name == "yc_dataset_ai_2026-01-27.xlsx"


def test_dated_path_rejects_bad_stage_or_ext(tmp_path):
    for bad in [("nope", "parquet"), ("base", "txt")]:
        try:
            config.dated_path(bad[0], "2026-01-27", bad[1], out_dir=tmp_path)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad}")


def test_latest_dated_picks_newest_by_iso_name(tmp_path):
    for d in ["2026-01-05", "2026-02-01", "2025-12-31"]:
        config.dated_path("base", d, "parquet", out_dir=tmp_path).write_bytes(b"x")
    newest = config.latest_dated("base", "parquet", out_dir=tmp_path)
    assert newest.name == "yc_dataset_base_2026-02-01.parquet"
    assert config.latest_dated("ai", "parquet", out_dir=tmp_path) is None


def test_prompt_version_is_stable_12_hex():
    v1 = config.prompt_version("SYS", "TMPL")
    v2 = config.prompt_version("SYS", "TMPL")
    v3 = config.prompt_version("SYS", "TMPL2")
    assert v1 == v2 and v1 != v3
    assert len(v1) == 12 and all(c in "0123456789abcdef" for c in v1)


def test_estimate_cost_matches_price_table():
    # 1M input + 1M output on Haiku 4.5 = $1 + $5
    usd = config.estimate_cost(1_000_000, 1_000_000, config.CLAUDE_MODEL)
    assert round(usd, 2) == 6.00


def test_target_years_span_2020_to_current():
    years = config.target_years(today=dt.date(2026, 7, 24))
    assert years[0] == 2020 and years[-1] == 2026
    assert set(years) == {2020, 2021, 2022, 2023, 2024, 2025, 2026}


def test_key_constants_present():
    assert config.PROVIDER_DEFAULT == "claude"
    assert config.CLAUDE_MODEL == "claude-haiku-4-5"
    assert config.MAX_DESC_CHARS == 2200
    assert config.MAX_TOKENS == 430
    assert isinstance(config.DATA_DIR, Path)
