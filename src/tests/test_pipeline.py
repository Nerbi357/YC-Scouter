"""Tests for the high-level pipeline orchestration (File 1 / File 2 helpers)."""

import json

import pandas as pd

from yc_scouter import pipeline


def test_build_base_from_records(tmp_path, sample_records):
    df, paths = pipeline.build_base(records=sample_records, out_dir=tmp_path, date="2026-01-27")
    assert paths["parquet"].name == "yc_dataset_base_2026-01-27.parquet"
    assert paths["parquet"].exists() and paths["xlsx"].exists()
    for col in ("id", "custom_score", "investability", "yc_url"):
        assert col in df.columns
    back = pd.read_parquet(paths["parquet"])
    assert len(back) == len(df)


def test_build_base_from_source_json(tmp_path, sample_records):
    src = tmp_path / "src.json"
    src.write_text(json.dumps(sample_records))
    df, paths = pipeline.build_base(source_json=src, out_dir=tmp_path, date="2026-01-27")
    assert len(df) > 0
    assert paths["parquet"].exists()


def test_build_base_respects_years(tmp_path, sample_records):
    df, _ = pipeline.build_base(
        records=sample_records, out_dir=tmp_path, date="2026-01-27", years=(2026,)
    )
    assert set(df["batch_year"].unique()) == {2026}


def test_build_ai_mock_provider_no_spend(tmp_path, sample_records):
    base, _ = pipeline.build_base(records=sample_records, out_dir=tmp_path, date="2026-01-27")
    out, paths = pipeline.build_ai(
        df=base,
        provider="mock",
        cache_path=tmp_path / "ai_cache.json",
        out_dir=tmp_path,
        date="2026-01-27",
    )
    assert paths["parquet"].name == "yc_dataset_ai_2026-01-27.parquet"
    assert paths["parquet"].exists() and paths["xlsx"].exists()
    assert "ai_description" in out.columns and "ai_risks" in out.columns
    assert (out["ai_description"].str.contains("MOCK")).all()
    assert (out["ai_model"] != "").all()


def test_build_ai_loads_latest_base_from_disk(tmp_path, sample_records):
    pipeline.build_base(records=sample_records, out_dir=tmp_path, date="2026-01-27")
    out, paths = pipeline.build_ai(
        provider="mock", cache_path=tmp_path / "c.json", out_dir=tmp_path, date="2026-01-28"
    )
    assert len(out) > 0 and paths["parquet"].name == "yc_dataset_ai_2026-01-28.parquet"


def test_build_ai_no_provider_no_key_uses_placeholder(tmp_path, sample_records, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    base, _ = pipeline.build_base(records=sample_records, out_dir=tmp_path, date="2026-01-27")
    out, _ = pipeline.build_ai(
        df=base, provider="claude", cache_path=tmp_path / "c.json", out_dir=tmp_path
    )
    from yc_scouter import ai

    assert (out["ai_description"] == ai.AI_DISABLED).all()
