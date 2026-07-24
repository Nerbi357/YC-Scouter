"""Tests for the high-level pipeline orchestration (File 1 / File 2 helpers)."""

import json

import pandas as pd

from yc_scouter import pipeline


def test_build_base_from_records(tmp_path, sample_records):
    df, paths = pipeline.build_base(records=sample_records, out_dir=tmp_path, date="2026-01-27")
    assert paths["parquet"].name == "yc_dataset_base_2026-01-27.parquet"
    assert paths["parquet"].exists() and paths["xlsx"].exists()
    for col in ("id", "score", "investability", "yc_url"):
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
