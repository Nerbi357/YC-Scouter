"""Y Combinator — the first source, and the template for every other one.

It supplies who exists and a handful of fields about them. Everything here is
already in the pipeline; the difference is that it now arrives as **facts with
provenance** rather than as columns, so a second source can disagree with it and
both statements survive.
"""

from __future__ import annotations

import numbers
from typing import Any

import pandas as pd

from . import Source, register

#: What YC publishes that is worth recording as an observation. Deliberately not
#: everything: derived fields belong to the layer that derives them, never here.
FIELDS = (
    "status",
    "stage",
    "team_size",
    "is_hiring",
    "top_company",
    "batch",
    "industry",
    "subindustry",
)

DIRECTORY = "https://www.ycombinator.com/companies"


def _url(row: pd.Series) -> str:
    """Where a person can check this company. Provenance is never blank."""
    return str(row.get("yc_url") or "").strip() or DIRECTORY


def _value(raw: Any) -> str:
    """One canonical spelling of a value, so a rerun does not look like a change.

    Whole numbers lose the float tail pandas gives them: a column holding one
    missing value turns 30 into ``30.0``, and recording that would both read badly
    ("30.0 people") and make every rerun look like a new observation.
    """
    try:
        if raw is None or pd.isna(raw):
            return ""
    except (TypeError, ValueError):  # arrays and other non-scalars
        pass
    if isinstance(raw, bool):
        return "true" if raw else ""
    if isinstance(raw, numbers.Real):
        number = float(raw)
        return str(int(number)) if number.is_integer() else str(number)
    return str(raw).strip()


def to_facts(frame: pd.DataFrame, *, observed_at: str) -> list[dict[str, Any]]:
    """Turn a company table into facts.

    Two rules, both about honesty rather than tidiness:

    * an **absent** field produces no fact — recording a blank would claim we
      observed something we did not;
    * every company gets a ``checked`` marker, so "we asked YC about this company
      and it said nothing" is distinguishable from "nobody asked".
    """
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        company_id = int(row["id"])
        url = _url(row)
        rows.append(
            {
                "company_id": company_id,
                "field": "checked",
                "value": "",
                "observed_at": observed_at,
                "source": "yc",
                "source_url": url,
                "confidence": "verified",
            }
        )
        for field in FIELDS:
            if field not in frame.columns:
                continue
            value = _value(row.get(field))
            if not value:
                continue
            rows.append(
                {
                    "company_id": company_id,
                    "field": field,
                    "value": value,
                    "observed_at": observed_at,
                    "source": "yc",
                    "source_url": url,
                    "confidence": "verified",
                }
            )
    return rows


SOURCE = register(
    Source(
        id="yc",
        title="Y Combinator portfolio (via the yc-oss mirror)",
        url="https://yc-oss.github.io/api/companies/all.json",
        licence="Open data, no key. Published by YC and mirrored by the community.",
        covers=FIELDS,
        emits=lambda frame, observed_at: to_facts(frame, observed_at=observed_at),
    )
)
