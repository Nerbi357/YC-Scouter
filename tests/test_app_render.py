"""Headless render test for the dashboard via Streamlit AppTest.

Skipped if Streamlit's testing harness isn't installed; runs in CI (full lock).
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

from yc_scouter import pipeline  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_dashboard_renders_without_exception(tmp_path, sample_records, monkeypatch):
    base, _ = pipeline.build_base(records=sample_records, out_dir=tmp_path, date="2026-01-27")
    _, paths = pipeline.build_ai(
        df=base,
        provider="mock",
        cache_path=tmp_path / "c.json",
        out_dir=tmp_path,
        date="2026-01-27",
    )
    monkeypatch.setenv("YC_SCOUTER_DATASET", str(paths["parquet"]))
    monkeypatch.setenv("YC_SCOUTER_USERDATA", str(tmp_path / "user_data.csv"))

    at = AppTest.from_file(str(APP), default_timeout=30).run()

    assert not at.exception, at.exception
    assert at.title[0].value.startswith("🛰️ YC Scouter")
    assert [t.label for t in at.tabs] == ["📊 Обзор", "🔎 Компании", "⚖️ Сравнение", "📝 Заметки"]
    labels = {m.label for m in at.metric}
    assert {"Компаний", "Индустрий"} <= labels
