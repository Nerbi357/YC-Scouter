"""Papermill smoke test for the notebooks — skipped if papermill isn't installed.

Runs in CI (which installs the full lock incl. papermill + ipykernel) and locally
when available; skipped otherwise so the core suite stays dependency-light.
"""

from pathlib import Path

import pandas as pd
import pytest

pm = pytest.importorskip("papermill")

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "companies_sample.json"


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
    assert len(df) > 0 and "score" in df.columns and "id" in df.columns
