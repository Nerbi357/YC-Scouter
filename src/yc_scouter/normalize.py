"""Normalize raw YC records into a clean, typed, filtered DataFrame.

Turns the ``yc-oss/api`` company objects into a tidy ``pandas.DataFrame`` with
stable column names, parses the batch into a numeric year, filters to the target
years (default 2024-2026), and de-duplicates by ``slug``.
"""

from __future__ import annotations

import re

import pandas as pd

from . import config

#: Columns the rest of the pipeline relies on. ``id`` is the immutable join key.
CORE_COLUMNS: tuple[str, ...] = (
    "id",
    "name",
    "slug",
    "batch",
    "batch_year",
    "industry",
    "subindustry",
    "tags",
    "one_liner",
    "long_description",
    "status",
    "stage",
    "team_size",
    "location",
    "region",
    "is_hiring",
    "top_company",
    "nonprofit",
    "website",
    "yc_url",
    "launched_at",
)

# Full-word season+year, e.g. "Winter 2024".
_FULL_RE = re.compile(r"\b(20\d{2})\b")
# Short form, e.g. "W24", "S25", "F24", "X25".
_SHORT_RE = re.compile(r"^[WSFX](\d{2})$", re.IGNORECASE)


def parse_batch_year(batch: str | None) -> int | None:
    """Extract the 4-digit year from a YC batch label, or None if unknown."""
    if not batch or not isinstance(batch, str):
        return None
    m = _FULL_RE.search(batch)
    if m:
        return int(m.group(1))
    m = _SHORT_RE.match(batch.strip())
    if m:
        return 2000 + int(m.group(1))
    return None


def _first_region(regions: object) -> str:
    if isinstance(regions, list) and regions:
        return str(regions[0])
    return ""


def normalize(
    records: list[dict],
    *,
    years: tuple[int, ...] | None = None,
) -> pd.DataFrame:
    """Return a typed DataFrame filtered to ``years`` and deduped by ``id``.

    ``years`` defaults to 2020..current year (``config.target_years()``). Rows are
    sorted by ``id`` (stable) before de-duplication so output order is
    deterministic across runs and machines.
    """
    if years is None:
        years = config.target_years()
    if not records:
        return pd.DataFrame(columns=list(CORE_COLUMNS))

    df = pd.DataFrame(records)

    df["id"] = pd.to_numeric(df.get("id"), errors="coerce").astype("Int64")
    df["batch_year"] = df.get("batch").map(parse_batch_year).astype("Int64")
    df["is_hiring"] = df.get("isHiring", False).astype("boolean").fillna(False).astype(bool)
    df["yc_url"] = df.get("url", "")
    df["location"] = df.get("all_locations", "").fillna("")
    df["region"] = df.get("regions").map(_first_region)
    df["team_size"] = pd.to_numeric(df.get("team_size"), errors="coerce").astype("Int64")

    for col in (
        "name",
        "slug",
        "batch",
        "industry",
        "subindustry",
        "one_liner",
        "long_description",
        "status",
        "stage",
        "website",
    ):
        if col not in df.columns:
            df[col] = ""
    if "tags" not in df.columns:
        df["tags"] = [[] for _ in range(len(df))]
    for flag in ("top_company", "nonprofit"):
        df[flag] = df.get(flag, False).astype("boolean").fillna(False).astype(bool)
    if "launched_at" not in df.columns:
        df["launched_at"] = pd.NA

    # Stable sort by id, then dedupe by id, then filter years — deterministic order.
    df = df.sort_values("id", kind="stable")
    df = df.drop_duplicates(subset="id", keep="first")
    keep = df["batch_year"].isin(set(years))
    df = df[keep].copy()

    return df[list(CORE_COLUMNS)].reset_index(drop=True)
