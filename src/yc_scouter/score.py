"""Configurable interestingness score (0-100) for ranking companies.

The score is a weighted blend of cheap, transparent signals. Weights live in a
plain dict so the user can retune what "interesting" means. Output is
deterministic and lands in [0, 100].

The column is called ``custom_score`` on purpose: it is *this project's* opinion,
not a number Y Combinator publishes. Everything the source provides keeps its own
name, so a reader can always tell whose claim they are looking at.
"""

from __future__ import annotations

import pandas as pd

#: Component weights. Override any subset via the ``weights`` argument.
DEFAULT_WEIGHTS: dict[str, float] = {
    "top_company": 3.0,  # YC's own breakout flag — strongest signal
    "recency": 2.0,  # newer batch = fresher opportunity
    "hiring": 1.0,  # actively hiring = alive & growing
    "team": 1.0,  # has a real (but not bloated) team
    "description": 0.5,  # has a substantive description
    "tags": 0.5,  # richer categorization
}

#: The name of the column this module writes.
COLUMN = "custom_score"

_MIN_YEAR = 2023  # 2024 -> 1/3, 2025 -> 2/3, 2026 -> 1.0


def _tag_count(tags: object) -> int:
    if isinstance(tags, list):
        return len(tags)
    if isinstance(tags, str) and tags.strip():
        return len([t for t in tags.split(",") if t.strip()])
    return 0


def _components(row: pd.Series) -> dict[str, float]:
    year = row.get("batch_year")
    team = row.get("team_size")
    desc = row.get("long_description") or ""
    return {
        "top_company": 1.0 if bool(row.get("top_company")) else 0.0,
        "recency": (min(max((int(year) - _MIN_YEAR) / 3.0, 0.0), 1.0) if pd.notna(year) else 0.0),
        "hiring": 1.0 if bool(row.get("is_hiring")) else 0.0,
        "team": (min(int(team), 50) / 50.0 if pd.notna(team) else 0.0),
        "description": 1.0 if len(str(desc)) >= 40 else 0.0,
        "tags": min(_tag_count(row.get("tags")), 3) / 3.0,
    }


def score(df: pd.DataFrame, *, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Add a ``custom_score`` column in [0, 100] computed from weighted signals."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    total_w = sum(w.values()) or 1.0

    def _row_score(row: pd.Series) -> float:
        comps = _components(row)
        raw = sum(w.get(k, 0.0) * v for k, v in comps.items())
        return round(100.0 * raw / total_w, 1)

    out = df.copy()
    out[COLUMN] = out.apply(_row_score, axis=1) if len(out) else []
    return out
