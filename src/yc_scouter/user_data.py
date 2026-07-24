"""Personal annotations (favorite / tags / funnel stage / notes).

Keyed by the **immutable company ``id``** so notes survive data refreshes *and*
company renames (``slug`` can change; ``id`` cannot). Two storage backends share
the same schema:

* a local CSV (``data/user_data.csv``) — used in Colab / locally, and
* Google Sheets (see :mod:`yc_scouter.gsheets`) — used when the dashboard is
  hosted on Streamlit Community Cloud, whose container disk is ephemeral.

The merge/coerce helpers are backend-agnostic: give them an annotations frame
from *either* source and they attach it to the company table by ``id``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_PATH = Path("data/user_data.csv")

#: ``id`` is the immutable join key; the rest are user-owned.
#: (a 0-5 rating existed once — dropped in favour of the favorite flag + stage.)
USER_COLUMNS = ("id", "watchlist", "my_tags", "my_stage", "my_notes")

#: Personal deal-flow (funnel) stages, in order. ``watchlist`` is the quick
#: "favorite" flag; ``my_stage`` is where the company sits in your own pipeline.
STAGES = ("New", "To review", "Contacted", "Passed", "Invested")
DEFAULT_STAGE = "New"


def empty_user_frame() -> pd.DataFrame:
    """An empty annotations table with the canonical schema."""
    return pd.DataFrame(columns=list(USER_COLUMNS))


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` with every USER_COLUMN present and ``id`` as nullable int."""
    df = df.copy()
    for col in USER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[list(USER_COLUMNS)]
    df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    return df


def coerce_types(out: pd.DataFrame) -> pd.DataFrame:
    """Apply sensible defaults/dtypes to the annotation columns of ``out``."""
    out = out.copy()
    out["watchlist"] = out["watchlist"].astype("boolean").fillna(False).astype(bool)
    out["my_notes"] = out["my_notes"].fillna("").astype(str)
    out["my_tags"] = out["my_tags"].fillna("").astype(str)
    stage = out["my_stage"].fillna("").astype(str).str.strip()
    out["my_stage"] = stage.where(stage != "", DEFAULT_STAGE)
    return out


def load_user_data(path: Path = DEFAULT_PATH) -> pd.DataFrame:
    """Return the CSV annotations table, or an empty one with the right schema."""
    path = Path(path)
    if not path.exists():
        return empty_user_frame()
    return _ensure_columns(pd.read_csv(path))


def save_user_data(rows: list[dict] | pd.DataFrame, path: Path = DEFAULT_PATH) -> None:
    """Write annotations to CSV atomically (tmp + rename)."""
    path = Path(path)
    df = pd.DataFrame(rows) if not isinstance(rows, pd.DataFrame) else rows.copy()
    df = _ensure_columns(df)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def merge_annotations(df: pd.DataFrame, user: pd.DataFrame) -> pd.DataFrame:
    """Left-join an already-loaded annotations frame onto ``df`` by ``id``.

    Idempotent: if ``df`` already carries the annotation columns (e.g. it was
    exported after a previous merge), they are dropped first so re-merging never
    produces suffixed ``_x`` / ``_y`` columns.
    """
    user = _ensure_columns(user)
    dupes = [c for c in USER_COLUMNS if c != "id" and c in df.columns]
    out = df.drop(columns=dupes).merge(user, on="id", how="left")
    return coerce_types(out)


def merge_user_data(df: pd.DataFrame, path: Path = DEFAULT_PATH) -> pd.DataFrame:
    """Convenience: load the CSV backend and merge it onto ``df``."""
    return merge_annotations(df, load_user_data(path))


def migrate_slug_to_id(
    old: Path,
    dataset: pd.DataFrame | str | Path,
    *,
    out_path: Path | None = None,
    backup: bool = True,
) -> pd.DataFrame:
    """One-off: convert a legacy **slug-keyed** annotations CSV to the id-keyed schema.

    ``dataset`` provides the slug→id map (a DataFrame or a path to a Base/AI parquet
    that has both ``slug`` and ``id``). Rows whose slug isn't found are dropped. The
    old file is renamed to ``*.slug.bak`` (when ``backup``) before the new one is
    written. Returns the migrated frame.
    """
    old = Path(old)
    old_df = pd.read_csv(old)
    if isinstance(dataset, (str, Path)):
        dataset = pd.read_parquet(dataset)
    smap = (
        dataset.dropna(subset=["slug", "id"]).astype({"id": "Int64"}).set_index("slug")["id"]
    ).to_dict()
    old_df["id"] = old_df["slug"].map(smap)
    migrated = _ensure_columns(old_df.dropna(subset=["id"]))

    out_path = Path(out_path) if out_path else old
    if backup and out_path.exists():
        out_path.replace(out_path.with_suffix(out_path.suffix + ".slug.bak"))
    save_user_data(migrated, path=out_path)
    return migrated
