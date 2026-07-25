"""Google Sheets annotations backend for the hosted dashboard.

Streamlit Community Cloud gives each app an *ephemeral* container: anything
written to local disk is wiped on the next restart (sleep/wake, redeploy,
maintenance). So personal notes must live outside the container. This module
reads/writes them to a Google Sheet via a service account, which persists.

It is imported lazily by ``app.py`` and only when Sheets is configured, so the
heavy ``gspread`` / ``google-auth`` deps stay optional for local/Colab use.

Configuration lives in Streamlit secrets (``.streamlit/secrets.toml``)::

    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
    client_email = "yc-radar@....iam.gserviceaccount.com"
    # ... (the full service-account JSON, as TOML keys)

    [gsheets]
    spreadsheet = "https://docs.google.com/spreadsheets/d/<ID>/edit"  # or the ID
    worksheet = "annotations"
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from . import user_data

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def is_configured(secrets: Any) -> bool:
    """True when both the service account and the target sheet are in secrets."""
    try:
        return bool(secrets.get("gcp_service_account")) and bool(secrets.get("gsheets"))
    except Exception:
        return False


def _open_worksheet(secrets: Any):
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(
        dict(secrets["gcp_service_account"]), scopes=SCOPES
    )
    client = gspread.authorize(creds)
    cfg = secrets["gsheets"]
    ref = cfg["spreadsheet"]
    book = client.open_by_url(ref) if str(ref).startswith("http") else client.open_by_key(ref)
    title = cfg.get("worksheet", "annotations")
    try:
        return book.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(title=title, rows=1000, cols=len(user_data.USER_COLUMNS))
        ws.update([list(user_data.USER_COLUMNS)])
        return ws


def load(secrets: Any) -> pd.DataFrame:
    """Return the annotations frame from the sheet (empty schema if blank)."""
    ws = _open_worksheet(secrets)
    records = ws.get_all_records()
    if not records:
        return user_data.empty_user_frame()
    df = pd.DataFrame(records)
    for col in user_data.USER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[list(user_data.USER_COLUMNS)]


def _last_column_letter() -> str:
    return chr(ord("A") + len(user_data.USER_COLUMNS) - 1)


def save(secrets: Any, df: pd.DataFrame, *, allow_empty: bool = False) -> None:
    """Overwrite the sheet with ``df`` (header + rows), keyed by company id.

    Cells are written as plain text, so the boolean flag is normalised to
    ``TRUE``/``FALSE`` — readable in the spreadsheet and parsed back by
    :func:`yc_scouter.user_data.to_bool` (which also tolerates older spellings).

    Two guards, because this sheet is the only copy of the owner's notes:

    * writing an **empty** frame over a populated sheet raises instead of erasing
      it (that is what an unreadable sheet or a lost session looks like) — pass
      ``allow_empty=True`` to mean it;
    * rows are written **first** and only leftovers below are cleared afterwards,
      so a failure mid-way can never leave the sheet blank (``ws.clear()`` up front
      did exactly that).
    """
    ws = _open_worksheet(secrets)
    out = user_data._ensure_columns(df)
    out["watchlist"] = out["watchlist"].map(lambda v: "TRUE" if user_data.to_bool(v) else "FALSE")
    out = out.fillna("").astype(str)

    existing = len(ws.get_all_values())
    if out.empty and existing > 1 and not allow_empty:
        raise ValueError(
            f"refusing to erase {existing - 1} saved rows with an empty table; "
            "pass allow_empty=True if that is really intended"
        )

    grid = [list(user_data.USER_COLUMNS)] + out.values.tolist()
    # A worksheet created by _open_worksheet has 1000 rows; the store outgrows that as
    # soon as the owner saves the whole table. Sheets rejects a range past the grid, so
    # the save would fail outright — grow it first.
    row_count = getattr(ws, "row_count", None)
    if row_count is not None and len(grid) > row_count:
        ws.resize(rows=len(grid) + 100)
    ws.update(grid, f"A1:{_last_column_letter()}{len(grid)}")
    if existing > len(grid):
        ws.batch_clear([f"A{len(grid) + 1}:{_last_column_letter()}{existing}"])
