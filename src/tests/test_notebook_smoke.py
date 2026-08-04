"""Papermill smoke test for the notebooks — skipped if papermill isn't installed.

Runs in CI (which installs the full lock incl. papermill + ipykernel) and locally
when available; skipped otherwise so the core suite stays dependency-light.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

pm = pytest.importorskip("papermill")

ROOT = Path(__file__).resolve().parents[2]  # repo root (src/tests/..)
FIXTURE = Path(__file__).parent / "fixtures" / "companies_sample.json"


def test_file1_notebook_builds_dated_base(tmp_path):
    out_dir = tmp_path / "data"
    pm.execute_notebook(
        str(ROOT / "notebooks" / "01_dataset_base.ipynb"),
        str(tmp_path / "out.ipynb"),
        parameters={
            "source_json": str(FIXTURE),
            "out_dir": str(out_dir),
            "date": "2026-01-27",
            "output": "commit",
        },
        kernel_name="python3",
    )
    parquet = out_dir / "yc_dataset_base_2026-01-27.parquet"
    xlsx = out_dir / "yc_dataset_base_2026-01-27.xlsx"
    assert parquet.exists() and xlsx.exists()
    df = pd.read_parquet(parquet)
    assert len(df) > 0 and "custom_score" in df.columns and "id" in df.columns


def test_file2_notebook_adds_ai_fields_mock(tmp_path):
    out_dir = tmp_path / "data"
    # File 1 first (builds the Base the AI notebook reads)
    pm.execute_notebook(
        str(ROOT / "notebooks" / "01_dataset_base.ipynb"),
        str(tmp_path / "out1.ipynb"),
        parameters={
            "source_json": str(FIXTURE),
            "out_dir": str(out_dir),
            "date": "2026-01-27",
            "output": "commit",
        },
        kernel_name="python3",
    )
    # File 2 with the offline mock provider (no spend)
    pm.execute_notebook(
        str(ROOT / "notebooks" / "02_ai_summary.ipynb"),
        str(tmp_path / "out2.ipynb"),
        parameters={
            "provider": "mock",
            "out_dir": str(out_dir),
            "date": "2026-01-27",
            "cache_path": str(out_dir / "cache" / "ai_cache.json"),
            "output": "commit",
        },
        kernel_name="python3",
    )
    ai_parquet = out_dir / "yc_dataset_ai_2026-01-27.parquet"
    assert ai_parquet.exists()
    df = pd.read_parquet(ai_parquet)
    assert "ai_description" in df.columns and "ai_risks" in df.columns
    assert (df["ai_description"].str.contains("MOCK")).all()


def test_spike_notebook_runs_and_writes_a_report(tmp_path):
    """Plumbing only: with an empty sample it makes no requests and still reports.

    Keeping the sample at zero is deliberate — the test suite must never depend on
    SEC being reachable, and the measurement itself belongs in the workflow, not
    here.
    """
    out_dir = tmp_path / "spikes"
    pm.execute_notebook(
        str(ROOT / "notebooks" / "03_spike_formd_coverage.ipynb"),
        str(tmp_path / "out_spike.ipynb"),
        parameters={"sample_size": 0, "out_dir": str(out_dir), "pause": 0},
        kernel_name="python3",
    )
    reports = list(out_dir.glob("formd_coverage_*.json"))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text())
    assert report["sample_size"] == 0
    assert sum(report["counts"].values()) == 0
    assert "browse-edgar" in report["source"]
