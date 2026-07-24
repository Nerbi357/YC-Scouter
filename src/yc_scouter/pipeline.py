"""High-level pipeline orchestration so the notebooks stay thin.

File 1 (Dataset Base) and File 2 (AI Summary) are 2-3 cells that just call these
functions with the notebook's parameters. All real logic lives in the package,
which keeps the notebooks self-contained and identical across Colab / Actions /
local runs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from . import ai, config, enrich, export, fetch, normalize, score


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


def _pick_summarizer(provider, model, api_key, progress_every):
    """Resolve a summarizer from the provider switch. ``mock`` never spends; the
    real providers only build a client when a key is present, else return None so
    the columns get a placeholder."""
    if provider == "mock":
        return ai.mock_summarizer, model or config.CLAUDE_MODEL
    if provider == "groq":
        model = model or config.GROQ_MODEL
        if api_key or os.environ.get("GROQ_API_KEY"):
            return (
                ai.make_groq_summarizer(
                    api_key=api_key, model=model, progress_every=progress_every
                ),
                model,
            )
        return None, model
    # default: claude
    model = model or config.CLAUDE_MODEL
    if api_key or os.environ.get("ANTHROPIC_API_KEY"):
        return (
            ai.make_claude_summarizer(api_key=api_key, model=model, progress_every=progress_every),
            model,
        )
    return None, model


def build_ai(
    *,
    df: pd.DataFrame | None = None,
    base_path: str | Path | None = None,
    provider: str = config.PROVIDER_DEFAULT,
    model: str | None = None,
    summarizer=None,
    api_key: str | None = None,
    cache_path: Path = ai.DEFAULT_CACHE_PATH,
    out_dir: Path = config.DATA_DIR,
    date: str | None = None,
    progress_every: int = 50,
    limit: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Path]]:
    """Build the "AI Summary": load the newest Base, add ``ai_description``/``ai_risks``
    for NEW cache keys only, and write the dated AI export.

    Provider is ``"claude"`` (default), ``"groq"``, or ``"mock"`` (offline, no spend).
    Pass ``summarizer`` to inject one directly (tests/demos).
    """
    if df is None:
        if base_path is None:
            base_path = config.latest_dated("base", "parquet", out_dir=out_dir)
        if base_path is None:
            raise FileNotFoundError("No base dataset found — run File 1 first.")
        df = pd.read_parquet(base_path)

    if summarizer is not None:
        model = model or config.CLAUDE_MODEL
    else:
        summarizer, model = _pick_summarizer(provider, model, api_key, progress_every)

    out = ai.add_ai_summaries(
        df, cache_path=cache_path, model=model, summarizer=summarizer, limit=limit
    )
    paths = export.export(out, stage="ai", date=date, out_dir=out_dir)
    return out, paths
