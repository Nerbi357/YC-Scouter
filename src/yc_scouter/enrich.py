"""Enrichment: investability heuristic and open-source deep-dive links.

None of this fabricates private financials. ``investability`` is an honest,
status-derived heuristic; the links point only at freely accessible pages so the
user can research each company at no cost.
"""

from __future__ import annotations

from urllib.parse import quote_plus

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


# OPEN sources only — every URL points at a freely accessible page. These are
# name-based *candidate* search links (not authoritative profiles), so the user
# can research without hitting any paywall or login wall. No Crunchbase/LinkedIn.
LINK_BUILDERS: dict[str, str] = {
    "news_url": "https://news.google.com/search?q={q}",
    "producthunt_url": "https://www.producthunt.com/search?q={q}",
    "hn_url": "https://hn.algolia.com/?q={q}",
    "github_url": "https://github.com/search?q={q}&type=repositories",
    "wikipedia_url": "https://en.wikipedia.org/w/index.php?search={q}",
}


def add_links(df: pd.DataFrame) -> pd.DataFrame:
    """Add open-source deep-dive link columns keyed off the company name.

    An empty ``name`` yields empty links rather than a malformed URL. Existing
    ``website`` / ``yc_url`` columns are left untouched.
    """
    out = df.copy()
    names = out["name"].fillna("") if "name" in out.columns else pd.Series([""] * len(out))

    for col, template in LINK_BUILDERS.items():
        out[col] = [template.format(q=quote_plus(str(n))) if str(n).strip() else "" for n in names]
    return out
