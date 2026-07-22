"""Pure filter/search helpers shared by the Streamlit dashboard.

Kept free of any Streamlit import so they can be unit-tested headless.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

_SEARCH_FIELDS = ("name", "one_liner", "long_description", "tags")


def _row_text(row: pd.Series) -> str:
    parts = []
    for field in _SEARCH_FIELDS:
        val = row.get(field)
        if isinstance(val, list):
            parts.append(" ".join(map(str, val)))
        elif pd.notna(val):
            parts.append(str(val))
    return " ".join(parts).lower()


def apply_filters(
    df: pd.DataFrame,
    *,
    industries: Sequence[str] | None = None,
    statuses: Sequence[str] | None = None,
    batch_years: Sequence[int] | None = None,
    min_team_size: int | None = None,
    min_score: float | None = None,
    query: str | None = None,
) -> pd.DataFrame:
    """Return the subset of ``df`` matching every provided criterion."""
    out = df
    if industries:
        out = out[out["industry"].isin(list(industries))]
    if statuses:
        out = out[out["status"].isin(list(statuses))]
    if batch_years:
        out = out[out["batch_year"].isin(list(batch_years))]
    if min_team_size is not None:
        out = out[out["team_size"].fillna(0) >= min_team_size]
    if min_score is not None:
        out = out[out["score"] >= min_score]
    if query and query.strip():
        needle = query.strip().lower()
        mask = out.apply(lambda r: needle in _row_text(r), axis=1)
        out = out[mask]
    return out.reset_index(drop=True)
