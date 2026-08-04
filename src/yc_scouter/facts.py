"""The facts layer — every observation, with where it came from.

**Long, not wide.** One row per `(company, field, value, source)` rather than one
column per source. The consequence is the point: **adding the eleventh source is an
insert, not a migration**, and no downstream code changes when a new one appears.

Three properties fall out of the shape rather than being separate features:

* **provenance** — every value carries its source and a link, so the interface can
  always say where a number came from;
* **a timeline** — a company's history is its rows sorted by time, and it costs
  nothing extra to store, because only *changes* are appended;
* **coverage** — asking a source and getting nothing is recorded, so an empty cell
  is distinguishable from a company nobody looked up. Confusing those two is the
  fastest way to mislead someone: a blank that reads as "raised no money".

Storing changes rather than snapshots is also what keeps the archive small. A
weekly refresh of a source that has not moved adds **zero** rows; it only updates
when the value was last confirmed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

#: The whole schema. ``value`` is canonical text (what a human reads);
#: ``value_num`` is the same thing as a number when it is one, so charts and
#: comparisons do not need a second table.
COLUMNS = (
    "company_id",
    "field",
    "value",
    "value_num",
    "observed_at",
    "last_seen",
    "source",
    "source_url",
    "confidence",
)

#: Provenance is not optional — a fact without it cannot be defended later.
REQUIRED = ("source", "source_url", "observed_at")

#: The key that decides whether an observation is new or a repeat.
_IDENTITY = ("company_id", "field", "value", "source")


class ProvenanceError(ValueError):
    """A fact arrived without the information that makes it checkable."""


def empty() -> pd.DataFrame:
    """An empty facts table with the canonical schema."""
    return pd.DataFrame({c: pd.Series(dtype="object") for c in COLUMNS})


def _as_number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _clean(row: Mapping[str, Any]) -> dict[str, Any]:
    out = {c: row.get(c) for c in COLUMNS}
    for field in REQUIRED:
        if not str(out.get(field) or "").strip():
            raise ProvenanceError(
                f"a fact needs {field!r}: {row.get('field')!r} for company "
                f"{row.get('company_id')!r} arrived without it"
            )
    out["company_id"] = int(row["company_id"])
    out["value"] = "" if row.get("value") is None else str(row["value"])
    out["value_num"] = _as_number(out["value"])
    out["last_seen"] = str(row.get("last_seen") or row["observed_at"])
    out["observed_at"] = str(row["observed_at"])
    out["confidence"] = str(row.get("confidence") or "reported")
    return out


def record(store: pd.DataFrame, rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Add observations, keeping the first sighting and refreshing the last.

    An observation already present (same company, field, value and source) is not
    duplicated: its ``last_seen`` moves forward instead. A *different* value from
    the same source is a new row — that is the history.
    """
    incoming = [_clean(r) for r in rows]
    if not incoming:
        return store

    out = store.copy() if len(store) else empty()
    known = {
        tuple(str(rec[k]) for k in _IDENTITY): index for index, rec in out.to_dict("index").items()
    }

    fresh: list[dict[str, Any]] = []
    for rec in incoming:
        key = tuple(str(rec[k]) for k in _IDENTITY)
        index = known.get(key)
        if index is None:
            known[key] = len(out) + len(fresh)
            fresh.append(rec)
            continue
        # Seen before: keep the original sighting, move the confirmation forward.
        if str(rec["last_seen"]) > str(out.at[index, "last_seen"]):
            out.at[index, "last_seen"] = rec["last_seen"]

    if fresh:
        out = pd.concat([out, pd.DataFrame(fresh, columns=list(COLUMNS))], ignore_index=True)
    return out.reset_index(drop=True)


def latest(store: pd.DataFrame, company_id: int, field: str) -> str | None:
    """The most recently observed value, or ``None`` — never a guess."""
    if not len(store):
        return None
    rows = store[(store["company_id"] == int(company_id)) & (store["field"] == field)]
    if rows.empty:
        return None
    return str(rows.sort_values("observed_at").iloc[-1]["value"])


def timeline(store: pd.DataFrame, company_id: int) -> list[dict[str, Any]]:
    """Everything known about one company, oldest first — the profile's spine."""
    if not len(store):
        return []
    rows = store[store["company_id"] == int(company_id)]
    if rows.empty:
        return []
    return rows.sort_values(["observed_at", "field"]).to_dict("records")


def coverage(
    store: pd.DataFrame,
    *,
    company_ids: Iterable[int],
    sources: Iterable[str],
) -> dict[tuple[int, str], str]:
    """Which sources were actually consulted for which companies.

    ``covered`` means the source was asked and its answer — including "nothing" —
    is recorded. ``uncovered`` means nobody asked, and the interface must say so
    rather than showing a blank that reads like an answer.
    """
    seen: set[tuple[int, str]] = set()
    if len(store):
        seen = {
            (int(row["company_id"]), str(row["source"]))
            for row in store[["company_id", "source"]].to_dict("records")
        }
    return {
        (int(cid), str(src)): ("covered" if (int(cid), str(src)) in seen else "uncovered")
        for cid in company_ids
        for src in sources
    }


def save(store: pd.DataFrame, path: str | Path) -> Path:
    """Write the table where the next run will find it."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    store.to_parquet(target, index=False)
    return target


def load(path: str | Path) -> pd.DataFrame:
    """Read the table, or start an empty one — a first run is not an error."""
    source = Path(path)
    if not source.exists():
        return empty()
    frame = pd.read_parquet(source)
    for column in COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    return frame[list(COLUMNS)]
