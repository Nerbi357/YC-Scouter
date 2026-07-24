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


def save(secrets: Any, df: pd.DataFrame) -> None:
    """Overwrite the sheet with ``df`` (header + rows), keyed by slug."""
    ws = _open_worksheet(secrets)
    out = df.copy()
    for col in user_data.USER_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[list(user_data.USER_COLUMNS)].fillna("").astype(str)
    ws.clear()
    ws.update([list(user_data.USER_COLUMNS)] + out.values.tolist())
