"""High-level pipeline orchestration so the notebooks stay thin.

File 1 (Dataset Base) and File 2 (AI Summary) are 2-3 cells that just call these
functions with the notebook's parameters. All real logic lives in the package,
which keeps the notebooks self-contained and identical across Colab / Actions /
local runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import config, enrich, export, fetch, normalize, score


def _load_records(
    records: list[dict] | None,
    source_json: str | Path | None,
    *,
    use_cache: bool,
    cache_path: Path | None,
) -> list[dict]:
    """Resolve input records: explicit list, a local JSON file, or a fresh fetch."""
    if records is not None:
        return records
    if source_json is not None:
        return json.loads(Path(source_json).read_text())
    return fetch.fetch_companies(cache_path=cache_path, use_cache=use_cache)


def build_base(
    *,
    records: list[dict] | None = None,
    source_json: str | Path | None = None,
    use_cache: bool = False,
    cache_path: Path | None = None,
    out_dir: Path = config.DATA_DIR,
    date: str | None = None,
    years: tuple[int, ...] | None = None,
) -> tuple[pd.DataFrame, dict[str, Path]]:
    """Build the "Dataset Base": fetch → normalize → enrich → score → dated export.

    Returns the DataFrame and the written ``{"parquet", "xlsx"}`` paths. Pass
    ``records`` or ``source_json`` to run offline (tests/CI); otherwise it fetches
    fresh from yc-oss.
    """
    raw = _load_records(records, source_json, use_cache=use_cache, cache_path=cache_path)
    df = normalize.normalize(raw, years=years)
    df = enrich.add_investability(df)
    df = enrich.add_links(df)
    df = score.score(df)
    paths = export.export(df, stage="base", date=date, out_dir=out_dir)
    return df, paths
