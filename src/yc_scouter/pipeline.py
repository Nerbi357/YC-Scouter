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

from . import ai, config, enrich, export, fetch, normalize, preflight, score


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
    check_first: bool = True,
) -> tuple[pd.DataFrame, dict[str, Path]]:
    """Build the "AI Summary": load the newest Base, add ``ai_description``/``ai_risks``
    for NEW cache keys only, and write the dated AI export.

    Provider is ``"claude"`` (default), ``"groq"``, or ``"mock"`` (offline, no spend).
    Pass ``summarizer`` to inject one directly (tests/demos). ``check_first`` runs the
    preflight (key, credits, model id) before spending anything — see
    :mod:`yc_scouter.preflight`.
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
        if summarizer is not None and check_first:
            # Fail before the loop rather than in the middle of a few thousand
            # companies: a rotated key, an empty balance and a retired model are
            # all invisible until the first call. Costs one token.
            report = preflight.check(provider, model=model, api_key=api_key)
            if report.warning:
                print(f"  preflight warning: {report.warning}", flush=True)

    out = ai.add_ai_summaries(
        df, cache_path=cache_path, model=model, summarizer=summarizer, limit=limit
    )
    paths = export.export(out, stage="ai", date=date, out_dir=out_dir)
    return out, paths


def build_facts(
    *,
    datasets: list[Path] | None = None,
    data_dir: Path = config.DATA_DIR,
    facts_path: Path | None = None,
) -> pd.DataFrame:
    """Fold every dated dataset into the facts table, oldest first.

    The dated files in ``data/`` are an archive of what each source said on a given
    day, so replaying them **is** the project's history — no snapshot storage
    needed, and nothing has to be recovered retroactively. Replaying is safe to
    repeat: an unchanged value only refreshes when it was last confirmed, so
    running this twice produces the same table.
    """
    from . import facts as facts_layer
    from .sources import yc as yc_source

    files = sorted(datasets or Path(data_dir).glob("yc_dataset_*_*.parquet"))
    target = Path(facts_path) if facts_path else Path(data_dir) / "facts.parquet"
    store = facts_layer.load(target)

    for path in files:
        observed_at = path.stem.rsplit("_", 1)[-1]  # yc_dataset_base_2026-07-24
        frame = pd.read_parquet(path)
        store = facts_layer.record(store, yc_source.to_facts(frame, observed_at=observed_at))

    facts_layer.save(store, target)
    return store
