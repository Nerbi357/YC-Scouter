"""Pure filter/search helpers shared by the Streamlit dashboard.

Kept free of any Streamlit import so they can be unit-tested headless.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

_SEARCH_FIELDS = ("name", "one_liner", "long_description", "tags", "my_notes", "my_tags")


def _row_text(row: pd.Series) -> str:
    parts = []
    for field in _SEARCH_FIELDS:
        val = row.get(field)
        if isinstance(val, list):
            parts.append(" ".join(map(str, val)))
        elif pd.notna(val):
            parts.append(str(val))
    return " ".join(parts).lower()


def split_tags(value: object) -> list[str]:
    """Parse a personal-tags cell (``"ai, fintech"`` or a list) into a clean list."""
    if isinstance(value, list):
        items = value
    elif value is None or (isinstance(value, float) and pd.isna(value)):
        items = []
    else:
        items = str(value).split(",")
    return [t.strip() for t in items if str(t).strip()]


def all_tags(df: pd.DataFrame) -> list[str]:
    """Every distinct personal tag used across ``df``, sorted."""
    if "my_tags" not in df.columns:
        return []
    seen: set[str] = set()
    for val in df["my_tags"]:
        seen.update(split_tags(val))
    return sorted(seen)


def apply_filters(
    df: pd.DataFrame,
    *,
    industries: Sequence[str] | None = None,
    subindustries: Sequence[str] | None = None,
    statuses: Sequence[str] | None = None,
    investabilities: Sequence[str] | None = None,
    stages: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    batch_years: Sequence[int] | None = None,
    min_team_size: int | None = None,
    max_team_size: int | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    watchlist_only: bool = False,
    query: str | None = None,
) -> pd.DataFrame:
    """Return the subset of ``df`` matching every provided criterion."""
    out = df
    if industries:
        out = out[out["industry"].isin(list(industries))]
    if subindustries and "subindustry" in out.columns:
        out = out[out["subindustry"].isin(list(subindustries))]
    if statuses:
        out = out[out["status"].isin(list(statuses))]
    if investabilities and "investability" in out.columns:
        out = out[out["investability"].isin(list(investabilities))]
    if stages and "my_stage" in out.columns:
        out = out[out["my_stage"].isin(list(stages))]
    if batch_years:
        out = out[out["batch_year"].isin(list(batch_years))]
    if watchlist_only and "watchlist" in out.columns:
        out = out[out["watchlist"].fillna(False).astype(bool)]
    if tags and "my_tags" in out.columns:
        wanted = {t.strip().lower() for t in tags if str(t).strip()}
        mask = out["my_tags"].apply(lambda v: bool(wanted & {t.lower() for t in split_tags(v)}))
        out = out[mask]
    if min_team_size is not None:
        out = out[out["team_size"].fillna(0) >= min_team_size]
    if max_team_size is not None:
        out = out[out["team_size"].fillna(0) <= max_team_size]
    if min_score is not None:
        out = out[out["score"] >= min_score]
    if max_score is not None:
        out = out[out["score"] <= max_score]
    if query and query.strip():
        needle = query.strip().lower()
        mask = out.apply(lambda r: needle in _row_text(r), axis=1)
        out = out[mask]
    return out.reset_index(drop=True)
