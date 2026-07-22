"""Personal annotations (rating / watchlist / notes) that survive data refreshes.

Stored in a small ``data/user_data.csv`` keyed by company ``slug``. Both the
notebook export and the Streamlit app merge it in, so re-running the pipeline with
fresh YC data never wipes the user's notes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_PATH = Path("data/user_data.csv")

#: slug is the join key; the rest are user-owned.
USER_COLUMNS = ("slug", "my_rating", "watchlist", "my_notes")


def load_user_data(path: Path = DEFAULT_PATH) -> pd.DataFrame:
    """Return the annotations table, or an empty one with the right schema."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=list(USER_COLUMNS))
    df = pd.read_csv(path)
    for col in USER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[list(USER_COLUMNS)]


def save_user_data(rows: list[dict] | pd.DataFrame, path: Path = DEFAULT_PATH) -> None:
    """Write annotations atomically (tmp + rename)."""
    path = Path(path)
    df = pd.DataFrame(rows) if not isinstance(rows, pd.DataFrame) else rows.copy()
    for col in USER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[list(USER_COLUMNS)]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def merge_user_data(df: pd.DataFrame, path: Path = DEFAULT_PATH) -> pd.DataFrame:
    """Left-join annotations onto ``df`` by slug, filling sensible defaults."""
    user = load_user_data(path)
    out = df.merge(user, on="slug", how="left")
    out["watchlist"] = out["watchlist"].astype("boolean").fillna(False).astype(bool)
    out["my_notes"] = out["my_notes"].fillna("").astype(str)
    # my_rating stays nullable numeric
    out["my_rating"] = pd.to_numeric(out["my_rating"], errors="coerce").astype("Int64")
    return out
