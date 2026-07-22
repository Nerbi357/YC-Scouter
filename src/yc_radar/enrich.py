"""Enrichment: investability heuristic and open-source deep-dive links.

None of this fabricates private financials. ``investability`` is an honest,
status-derived heuristic; the links point only at freely accessible pages so the
user can research each company at no cost.
"""

from __future__ import annotations

import pandas as pd

# Honest, status-derived heuristic (see SPEC §3). Private YC startups are not
# directly buyable by retail investors; only post-IPO companies trade openly.
INVESTABILITY: dict[str, str] = {
    "Public": "Public — buyable on the open market",
    "Acquired": "Acquired — not directly investable",
    "Active": "Private — accredited / SPV / secondary only",
    "Inactive": "Inactive — not investable",
}
INVESTABILITY_UNKNOWN = "Unknown"


def add_investability(df: pd.DataFrame) -> pd.DataFrame:
    """Add an ``investability`` column derived from ``status``."""
    out = df.copy()
    out["investability"] = out["status"].map(INVESTABILITY).fillna(INVESTABILITY_UNKNOWN)
    return out
