"""Integration checks for the dashboard's data plumbing (no Streamlit runtime)."""

import app
import pandas as pd

from yc_scouter import pipeline, user_data


def test_dataset_path_env_override(tmp_path, sample_records, monkeypatch):
    base, _ = pipeline.build_base(records=sample_records, out_dir=tmp_path, date="2026-01-27")
    _, paths = pipeline.build_ai(
        df=base,
        provider="mock",
        cache_path=tmp_path / "c.json",
        out_dir=tmp_path,
        date="2026-01-27",
    )
    monkeypatch.setenv("YC_SCOUTER_DATASET", str(paths["parquet"]))
    assert app.dataset_path() == paths["parquet"]


def test_dataset_path_prefers_newest_ai(tmp_path, sample_records, monkeypatch):
    monkeypatch.delenv("YC_SCOUTER_DATASET", raising=False)
    data_dir = tmp_path / "data"
    base, _ = pipeline.build_base(records=sample_records, out_dir=data_dir, date="2026-01-05")
    pipeline.build_ai(
        df=base,
        provider="mock",
        cache_path=data_dir / "c.json",
        out_dir=data_dir,
        date="2026-02-01",
    )
    monkeypatch.chdir(tmp_path)  # config.latest_dated resolves DATA_DIR="data" from cwd
    chosen = app.dataset_path()
    assert chosen is not None and chosen.name == "yc_dataset_ai_2026-02-01.parquet"


def test_merged_dashboard_frame_has_ai_and_notes(tmp_path, sample_records):
    base, _ = pipeline.build_base(records=sample_records, out_dir=tmp_path, date="2026-01-27")
    _, paths = pipeline.build_ai(
        df=base,
        provider="mock",
        cache_path=tmp_path / "c.json",
        out_dir=tmp_path,
        date="2026-01-27",
    )
    df = pd.read_parquet(paths["parquet"])
    merged = user_data.merge_annotations(df, user_data.empty_user_frame())
    for col in ("ai_description", "ai_risks", "my_stage", "watchlist", "id"):
        assert col in merged.columns
    assert merged["ai_description"].str.contains("MOCK").all()
