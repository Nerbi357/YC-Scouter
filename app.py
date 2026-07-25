"""YC Scouter — interactive Streamlit dashboard.

Reads the newest dated Parquet produced by the pipeline (it never re-fetches) and
lets you filter, chart, compare, and annotate companies.

Storage for your personal notes/tags/stage is chosen automatically:

* **Google Sheets** when configured in Streamlit secrets (survives restarts —
  required for hosting on Streamlit Community Cloud, whose disk is ephemeral);
* a local **CSV** otherwise (Colab / local use).

Performance note: with a few thousand companies, anything built eagerly on every rerun
(exports, per-row Python loops) blows the free-tier resource limits. Exports are
therefore generated only on demand, and the card list is paginated.

Run locally:  ``streamlit run app.py``
"""

from __future__ import annotations

import hashlib
import hmac
import io
import os
import re
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# Make ``src/yc_scouter`` importable on Streamlit Cloud (repo layout).
_SRC = Path(__file__).parent / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from yc_scouter import config, filters, user_data  # noqa: E402

try:
    from yc_scouter import gsheets  # noqa: E402
except Exception:  # pragma: no cover - optional deps
    gsheets = None

try:
    import plotly.express as px
except Exception:  # pragma: no cover - optional
    px = None

USER_DATA_CSV = Path(os.environ.get("YC_SCOUTER_USERDATA", "data/user_data.csv"))

#: Cards rendered per page (each card is a widget — rendering thousands stalls the app).
PAGE_SIZE = 50

SORT_OPTIONS = {
    "Score (high to low)": ("score", False),
    "Score (low to high)": ("score", True),
    "Batch year (newest first)": ("batch_year", False),
    "Batch year (oldest first)": ("batch_year", True),
    "Name (A to Z)": ("name", True),
    "Name (Z to A)": ("name", False),
}

#: label -> (file extension, MIME type)
EXPORT_FORMATS = {
    "CSV": ("csv", "text/csv"),
    "Excel": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "Parquet": ("parquet", "application/octet-stream"),
}

LINK_COLUMNS = [
    "website",
    "yc_url",
    "news_url",
    "producthunt_url",
    "hn_url",
    "github_url",
    "wikipedia_url",
]
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

CSS = """
<style>
  .block-container {padding-top: 2.2rem;}
  div[data-testid="stMetric"] {
      background: rgba(128,128,128,0.08);
      border: 1px solid rgba(128,128,128,0.18);
      border-radius: 12px; padding: 12px 16px;
  }
  div[data-testid="stMetricValue"] {font-size: 1.7rem;}

  /* Sidebar inputs kept readable on hover (default theme washed the text out). */
  section[data-testid="stSidebar"] input,
  section[data-testid="stSidebar"] input:hover,
  section[data-testid="stSidebar"] input:focus,
  section[data-testid="stSidebar"] [data-baseweb="select"] div {
      color: #16181d !important;
      -webkit-text-fill-color: #16181d !important;
      caret-color: #16181d !important;
  }
  section[data-testid="stSidebar"] input::placeholder {
      color: #6b7280 !important; -webkit-text-fill-color: #6b7280 !important;
  }

  /* Small italic min/max hints under the "From"/"To" inputs. */
  .range-hint {font-size: 0.76rem; font-style: italic; color: #6b7280; margin-top: -0.55rem;}

  /* Export control sits on the tab bar's line, flush right.
     The row is collapsed to zero height (the button overflows visibly) so it
     occupies no hit area at all — a full-width row here would swallow every tab
     click, which is exactly how the tab bar once became unusable. */
  .st-key-export_row {height: 0; overflow: visible; position: relative; z-index: 10;
      pointer-events: none;}
  .st-key-export_row div[data-testid="stPopover"] {display: flex; justify-content: flex-end;}
  .st-key-export_row button, .st-key-export_row [data-testid="stPopoverBody"] {
      pointer-events: auto;}
</style>
"""


def dataset_path() -> Path | None:
    """Newest dated dataset the dashboard should read (AI preferred, else Base)."""
    env = os.environ.get("YC_SCOUTER_DATASET")
    if env:
        return Path(env)
    for stage in ("ai", "base"):
        p = config.latest_dated(stage, "parquet")
        if p is not None:
            return p
    return None


# --------------------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def load_data(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_parquet(path)


class DatasetError(Exception):
    """The dataset lacks something the dashboard cannot work without."""


#: Without these there is no dashboard: ``id`` keys the notes, ``name`` labels rows.
REQUIRED_COLUMNS = ("id", "name")

#: Everything else the UI touches, with the value used when a rebuild drops it.
#: Filling them in beats a KeyError deep inside a chart on a live dashboard.
OPTIONAL_DEFAULTS: dict[str, object] = {
    "batch": "",
    "batch_year": pd.NA,
    "industry": "",
    "subindustry": "",
    "status": "",
    "investability": "",
    "one_liner": "",
    "long_description": "",
    "tags": "",
    "team_size": pd.NA,
    "score": pd.NA,
    "ai_description": "",
    "ai_risks": "",
    "website": "",
    "yc_url": "",
}


def prepare_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Make any dataset the pipeline produced safe to render.

    Returns the cleaned frame plus human-readable notes about what had to be
    repaired (shown to the owner, so a broken rebuild is visible rather than
    silent). Raises :class:`DatasetError` only when nothing sensible can be shown.
    """
    notes: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DatasetError(
            "The dataset is missing required columns: " + ", ".join(missing) + ". "
            "Rebuild the data with File 1 (Base), then File 2 (AI)."
        )

    out = df.copy()
    # to_numeric leaves inf alone and lets 1e19 through; the first raises on the cast
    # below (a blank crash page), the second silently overflows into a negative id that
    # then looks like a duplicate. Both are "no usable id".
    ids = pd.to_numeric(out["id"], errors="coerce")
    usable = ids.notna() & np.isfinite(ids) & ids.between(-(2**63), 2**63 - 1)
    bad = int((~usable).sum())
    if bad:
        out = out[usable]
        ids = ids[usable]
        notes.append(f"Skipped rows without a usable id: {bad}.")
    out["id"] = ids.astype("int64")

    dupes = int(out["id"].duplicated().sum())
    if dupes:
        # Widget keys are built from the id — two rows with the same id crash the app.
        out = out.drop_duplicates(subset="id", keep="first")
        notes.append(f"Collapsed duplicate ids: {dupes}.")

    added = [c for c in OPTIONAL_DEFAULTS if c not in out.columns]
    for col in added:
        out[col] = OPTIONAL_DEFAULTS[col]
    if added:
        notes.append("Added missing columns as empty: " + ", ".join(added) + ".")

    return out.reset_index(drop=True), notes


#: Set when st.secrets itself is unreadable (a malformed secrets.toml — most often a
#: private key pasted with real newlines). "Unreadable" must never be mistaken for
#: "not configured": that would silently drop a shared deployment into single-user
#: mode, where every anonymous visitor is the owner.
SECRETS_BROKEN = "secrets_unreadable"


def _secrets():
    """The secrets mapping, or ``{}`` — recording the difference between the two ways
    of getting ``{}``.

    *No secrets file at all* is the normal local/Colab case and means single-user mode.
    *A file that exists but cannot be parsed* is a broken shared deployment, and must
    not be mistaken for the first: that is what would silently make every anonymous
    visitor the owner.
    """
    try:
        s = st.secrets
        s.get("app")  # force the file to be parsed, not just referenced
    except Exception as exc:
        missing = type(exc).__name__ == "StreamlitSecretNotFoundError"
        try:
            if missing:
                st.session_state.pop(SECRETS_BROKEN, None)
            else:
                st.session_state[SECRETS_BROKEN] = str(exc)
        except Exception:  # pragma: no cover - no session yet
            pass
        return {}
    try:
        st.session_state.pop(SECRETS_BROKEN, None)
    except Exception:  # pragma: no cover
        pass
    return s


def secrets_unreadable() -> bool:
    """True when the secrets file exists but could not be parsed."""
    _secrets()
    try:
        return bool(st.session_state.get(SECRETS_BROKEN))
    except Exception:  # pragma: no cover
        return False


def use_gsheets() -> bool:
    return gsheets is not None and gsheets.is_configured(_secrets())


def _owner_key():
    """The owner password from secrets (``[app] owner_key``), or None.

    A blank / whitespace-only value counts as *not configured* — an accidentally
    empty secret must not become a password anyone can guess by pressing space.
    """
    s = _secrets()
    try:
        app = s.get("app") if hasattr(s, "get") else None
        key = app.get("owner_key") if app else None
    except Exception:
        return None
    return key if str(key or "").strip() else None


def is_owner() -> bool:
    """True for the owner.

    With no ``owner_key`` configured this is single-user mode (local/Colab) and
    everyone is the owner. But when the notes go to a **shared Google Sheet**, a
    missing or misspelled key would hand every visitor write access to them — so
    there the gate fails *closed* and nobody is the owner until a key is set.

    It also fails closed when the secrets file cannot be parsed at all: a malformed
    ``secrets.toml`` used to look exactly like "no secrets configured", i.e. like a
    private laptop, and turned the public dashboard into single-user mode.
    """
    if secrets_unreadable():
        # We cannot tell whether this deployment is shared, so assume it is.
        return False
    if not _owner_key():
        return not use_gsheets()
    return bool(st.session_state.get("is_owner", False))


def check_owner_key(entered: str | None) -> bool:
    """Unlock the session if ``entered`` matches the configured key."""
    key = _owner_key()
    if not key:
        return False
    if hmac.compare_digest(str(entered or "").strip(), str(key).strip()):
        st.session_state["is_owner"] = True
        return True
    return False


def owner_gate() -> None:
    """Sidebar unlock: turns a visitor session into the owner when an
    ``owner_key`` is configured and entered correctly."""
    if st.session_state.get("is_owner"):
        return
    if not _owner_key():
        if use_gsheets():
            st.sidebar.error(
                "🔒 No access key is set (`[app] owner_key` in the secrets), so the shared "
                "notes table is read-only. Add the key to be able to save "
                "(see DOCS/HOW_TO_DEPLOY_DASHBOARD.md)."
            )
        return
    with st.sidebar.expander("🔒 Access key"):
        entered = st.text_input("Access key", type="password", key="owner_key_input")
        if st.button("Unlock"):
            if check_owner_key(entered):
                st.rerun()
            else:
                st.error("Wrong key.")


def storage_banner() -> None:
    """Explain, in plain words, what happens to the notes this visitor makes."""
    if is_owner():
        if use_gsheets() and not st.session_state.get("gsheets_error"):
            st.success(
                "🔓 **Full access.** Your notes go to permanent storage (a Google Sheet) — "
                "they survive a page refresh, an app restart and a data rebuild.",
                icon="✅",
            )
        elif not use_gsheets():
            st.info(
                "🔓 **Full access.** Notes are saved to a local file. When hosting, connect "
                "a Google Sheet (DOCS/HOW_TO_DEPLOY_DASHBOARD.md), otherwise they are "
                "lost on the next restart.",
                icon="💾",
            )
    else:
        st.info(
            "👀 **View mode.** Explore and filter everything without limits. Notes you "
            "make here are **visible only to you** and **disappear when you refresh "
            "the page** — they never reach the shared storage. To keep notes for good, "
            "enter the access key in the sidebar.",
            icon="👀",
        )


#: Where a visitor's own notes live for the duration of their browser session.
VISITOR_STORE = "visitor_notes"
#: The shared store, read once per session instead of once per rerun.
SHEETS_CACHE = "gsheets_cache"
#: Set when the sheet could not be read — writing then would destroy what is in it.
SHEETS_BLOCKED = "gsheets_readonly"


def refresh_annotations() -> None:
    """Forget the cached copy of the shared store (the "reload" button)."""
    st.session_state.pop(SHEETS_CACHE, None)
    st.session_state.pop(SHEETS_BLOCKED, None)
    st.session_state.pop("gsheets_error", None)


def load_annotations() -> pd.DataFrame:
    """Notes for the current viewer.

    Visitors get their **own** session-local set — they neither see the owner's
    notes nor write into them. The owner gets the shared store (Google Sheets or
    local CSV), degrading gracefully if Sheets is unreachable so a credentials
    problem can never take the dashboard down.

    The sheet is read **once per session** and then kept in session state: it was
    a network round-trip on every rerun, i.e. on every keystroke in the filters.
    """
    if not is_owner():
        return st.session_state.get(VISITOR_STORE, user_data.empty_user_frame())
    if use_gsheets():
        cached = st.session_state.get(SHEETS_CACHE)
        if cached is not None:
            return cached
        try:
            loaded = user_data._ensure_columns(gsheets.load(_secrets()))
        except Exception as exc:  # pragma: no cover - network/credentials
            st.session_state["gsheets_error"] = str(exc)
            st.session_state[SHEETS_BLOCKED] = True
            # Cache the failure as well. Without this, every rerun — i.e. every
            # keystroke in the filters — retries a sheet we already know is dead;
            # if the failure mode is a hang rather than a 401, the app crawls.
            # "Reload from the sheet" clears this and retries.
            st.session_state[SHEETS_CACHE] = user_data.empty_user_frame()
            return st.session_state[SHEETS_CACHE]
        st.session_state[SHEETS_CACHE] = loaded
        st.session_state.pop(SHEETS_BLOCKED, None)
        st.session_state.pop("gsheets_error", None)
        return loaded
    return user_data.load_user_data(USER_DATA_CSV)


def secrets_error_banner() -> None:
    """A malformed secrets file is now fail-closed — say so, or it looks like a bug."""
    err = st.session_state.get(SECRETS_BROKEN)
    if err:
        st.error(
            "⚠️ **The secrets file could not be read**, so the dashboard is in "
            "view-only mode for everyone (it cannot tell whether it is deployed "
            f"privately or publicly). Fix the file and reload. Reason: {err}"
        )


def gsheets_error_banner() -> None:
    """Actionable message when the Sheets credentials are rejected."""
    err = st.session_state.get("gsheets_error")
    if not err:
        return
    if "invalid_grant" in err or "account not found" in err:
        st.warning(
            "⚠️ **The Google Sheet is not connected** — notes are currently kept for "
            "this session only.\n\n"
            "Google rejected the service-account key: the account no longer exists or "
            "the key is stale. How to fix it:\n"
            "1. Google Cloud Console → **IAM & Admin → Service Accounts** — check that "
            "the account from `client_email` still exists (recreate it if not).\n"
            "2. On that account → **Keys → Add key → JSON** — download a **new** key.\n"
            "3. Streamlit → **Settings → Secrets** — replace `private_key`, "
            "`private_key_id` and `client_email` with the values from the new file "
            "(copy `private_key` whole, including the `\\n` sequences).\n"
            "4. Remember to share the sheet with `client_email` as **Editor**."
        )
    else:
        st.warning(f"⚠️ The Google Sheet is unavailable — notes are not saved. Reason: {err}")


def save_annotations(df: pd.DataFrame) -> None:
    """Persist notes for the current viewer (session-only for visitors).

    Refuses to write to Sheets while the last read failed: the in-memory table
    would then be *empty*, and saving it would wipe every note in the sheet.
    """
    if not is_owner():
        st.session_state[VISITOR_STORE] = user_data._ensure_columns(df)
        return
    if use_gsheets():
        if st.session_state.get(SHEETS_BLOCKED):
            raise RuntimeError(
                "The Google Sheet is unreadable — saving is disabled so your existing notes "
                'are not erased. Fix the access, then press "Reload from the sheet".'
            )
        gsheets.save(_secrets(), df)
        st.session_state[SHEETS_CACHE] = user_data._ensure_columns(df)
    else:
        user_data.save_user_data(df, path=USER_DATA_CSV)


def upsert_annotations(changes: dict[int, dict]) -> int:
    """Write **only** the given companies, merged into the freshest store.

    Never writes back a snapshot this session read minutes ago. The dashboard can be
    open in two tabs (or on a phone), and the owner may edit the Google Sheet by hand
    — writing a stale whole-table snapshot silently deleted everything the other
    writer had added. Re-reading immediately before the write makes a save
    last-writer-wins *per company* instead of per table.

    Returns how many companies were written.
    """
    if not changes:
        return 0
    if not is_owner():
        store = st.session_state.get(VISITOR_STORE, user_data.empty_user_frame())
        st.session_state[VISITOR_STORE] = user_data.upsert(store, changes)
        return len(changes)

    if use_gsheets():
        if st.session_state.get(SHEETS_BLOCKED):
            raise RuntimeError(
                "The Google Sheet is unreadable — saving is disabled so your existing notes "
                'are not erased. Fix the access, then press "Reload from the sheet".'
            )
        fresh = user_data._ensure_columns(gsheets.load(_secrets()))
        merged = user_data.upsert(fresh, changes)
        gsheets.save(_secrets(), merged)
        st.session_state[SHEETS_CACHE] = merged
        return len(changes)

    merged = user_data.upsert(user_data.load_user_data(USER_DATA_CSV), changes)
    user_data.save_user_data(merged, path=USER_DATA_CSV)
    return len(changes)


def save_one(row_id: int, values: dict) -> None:
    """Upsert a single company's annotations into the store."""
    upsert_annotations({int(row_id): values})


# --------------------------------------------------------------- "saved" feedback
#: (what was saved, when) — a save is followed by a rerun, which wipes an inline
#: st.success, so the confirmation has to survive in session state.
SAVED_FLASH = "saved_flash"
FLASH_TTL_SECONDS = 60
#: Stands in for a company id when the whole notes table was saved at once.
BULK_FLASH_ID = "bulk"


def _flash_is_fresh(flash: object, cid: object, now: float, ttl: float) -> bool:
    if not isinstance(flash, tuple) or len(flash) != 2:
        return False
    saved_cid, stamp = flash
    return saved_cid == cid and (now - float(stamp)) <= ttl


def mark_saved(cid: object) -> None:
    """Remember that ``cid`` was just saved (and pop a toast about it)."""
    st.session_state[SAVED_FLASH] = (cid, time.time())
    try:
        st.toast("Saved ✅", icon="✅")
    except Exception:  # pragma: no cover - toast needs a live runtime
        pass


def saved_recently(cid: object) -> bool:
    """True while the "saved" confirmation for ``cid`` should still be visible."""
    return _flash_is_fresh(st.session_state.get(SAVED_FLASH), cid, time.time(), FLASH_TTL_SECONDS)


# ------------------------------------------------------------------------- export
def _clean_cell(v: object) -> object:
    """One cell, safe for CSV/Excel: multi-value cells joined, control chars stripped.

    ``filters.is_sequence`` rather than ``isinstance(v, list)``: Parquet hands list
    columns back as numpy arrays, which used to be exported as their repr —
    ``"['Bio' 'Climate']"``, newlines and all.
    """
    if filters.is_sequence(v):
        return ", ".join(map(str, v))
    if isinstance(v, str):
        return _CTRL_RE.sub("", v)
    return v


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    safe = df.map(_clean_cell)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        safe.to_excel(xw, index=False, sheet_name="YC Scouter")
    return buf.getvalue()


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.map(_clean_cell).to_csv(index=False).encode("utf-8")


def _to_parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def export_bytes(df: pd.DataFrame, fmt: str) -> bytes:
    """Serialize the filtered view to one of :data:`EXPORT_FORMATS`."""
    if fmt == "CSV":
        return _to_csv_bytes(df)
    if fmt == "Excel":
        return _to_excel_bytes(df)
    if fmt == "Parquet":
        return _to_parquet_bytes(df)
    raise ValueError(f"unknown export format: {fmt}")


def export_panel(df: pd.DataFrame, key: str) -> None:
    """Compact export control (top-right). Files are built only on request —
    doing it on every rerun costs seconds of CPU and hundreds of MB on the full
    dataset."""
    with st.popover("⬇️ Export", width="stretch"):
        st.caption(f"Filtered: **{len(df)}** companies")
        fmt = st.radio("Format", list(EXPORT_FORMATS), horizontal=True, key=f"fmt_{key}")
        state_key = f"export_{key}"
        if st.button("Prepare the file", key=f"prep_{key}", width="stretch"):
            with st.spinner(f"Building {fmt}…"):
                st.session_state[state_key] = {
                    "fmt": fmt,
                    "n": len(df),
                    "data": export_bytes(df, fmt),
                }
        ready = st.session_state.get(state_key)
        if ready:
            ext, mime = EXPORT_FORMATS[ready["fmt"]]
            st.download_button(
                f"⬇️ Download {ready['fmt']} ({ready['n']} companies)",
                ready["data"],
                f"yc_scouter.{ext}",
                mime,
                width="stretch",
                key=f"dl_{key}",
            )
            if ready["n"] != len(df) or ready["fmt"] != fmt:
                st.caption('⚠️ The selection changed — press "Prepare the file" again.')


# ------------------------------------------------------------------------ sidebar
def keep_valid(selected: object, options: list) -> list:
    """The part of a previous selection that still exists in ``options``."""
    return [s for s in (selected or []) if s in options]


def _int_range(label: str, key: str, series: pd.Series) -> tuple[int | None, int | None]:
    """Two integer inputs (From / To) with the data's own min/max as hints.

    Leaving a field empty removes that bound entirely.
    """
    st.sidebar.markdown(f"**{label}**")
    c1, c2 = st.sidebar.columns(2)
    values = pd.to_numeric(series, errors="coerce").dropna()
    lo_hint = int(values.min()) if len(values) else 0
    hi_hint = int(values.max()) if len(values) else 0

    lo = c1.number_input(
        "From",
        min_value=0,
        value=None,
        step=1,
        format="%d",
        key=f"{key}_lo",
        help="Empty = no lower bound",
    )
    c1.markdown(f"<div class='range-hint'>min {lo_hint}</div>", unsafe_allow_html=True)
    hi = c2.number_input(
        "To",
        min_value=0,
        value=None,
        step=1,
        format="%d",
        key=f"{key}_hi",
        help="Empty = no upper bound",
    )
    c2.markdown(f"<div class='range-hint'>max {hi_hint}</div>", unsafe_allow_html=True)
    return (int(lo) if lo is not None else None, int(hi) if hi is not None else None)


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔍 Filters")
    st.sidebar.caption('An empty "From" or "To" means no bound on that side.')
    query = st.sidebar.text_input("Search (name / idea / tags / notes)")

    industries = st.sidebar.multiselect("Industry", sorted(df["industry"].dropna().unique()))

    subindustries = []
    if "subindustry" in df.columns:
        pool = df[df["industry"].isin(industries)] if industries else df
        sub_opts = sorted(pool["subindustry"].dropna().unique())
        # Picking an industry rewrites these options, and Streamlit drops the whole
        # selection when options change — keep the part that is still valid.
        st.session_state["sub_pick"] = keep_valid(st.session_state.get("sub_pick"), sub_opts)
        subindustries = st.sidebar.multiselect("Subindustry", sub_opts, key="sub_pick")

    statuses = st.sidebar.multiselect("Status (YC)", sorted(df["status"].dropna().unique()))

    investabilities = []
    if "investability" in df.columns:
        investabilities = st.sidebar.multiselect(
            "Investability", sorted(df["investability"].dropna().unique())
        )

    stages = st.sidebar.multiselect("Funnel stage", list(user_data.STAGES))

    tag_opts = filters.all_tags(df)
    tags = st.sidebar.multiselect("My tags / labels", tag_opts) if tag_opts else []

    watchlist_only = st.sidebar.toggle("⭐ Favorites only", value=False)

    years = sorted(int(y) for y in df["batch_year"].dropna().unique())
    year_sel = st.sidebar.multiselect("Batch year", years)

    score_lo, score_hi = _int_range("Score (0–100)", "score", df["score"])
    team_lo, team_hi = _int_range("Team size", "team", df["team_size"])

    return filters.apply_filters(
        df,
        industries=industries or None,
        subindustries=subindustries or None,
        statuses=statuses or None,
        investabilities=investabilities or None,
        stages=stages or None,
        tags=tags or None,
        batch_years=year_sel or None,
        watchlist_only=watchlist_only,
        min_team_size=team_lo,
        max_team_size=team_hi,
        min_score=score_lo,
        max_score=score_hi,
        query=query or None,
    )


# --------------------------------------------------------------- selection helpers
def selected_id() -> int | None:
    """The company currently opened in a detail card (session or ?id= in the URL)."""
    if "selected_id" in st.session_state:
        return st.session_state["selected_id"]
    try:
        raw = st.query_params.get("id")
    except Exception:  # pragma: no cover - older runtimes
        return None
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def select_company(row_id: int | None) -> None:
    """Open a company's detail card and reflect it in the URL (shareable link)."""
    st.session_state["selected_id"] = row_id
    try:
        if row_id is None:
            st.query_params.pop("id", None)
        else:
            st.query_params["id"] = str(row_id)
    except Exception:  # pragma: no cover - older runtimes
        pass


def _row_id(row: pd.Series) -> int | None:
    """A company's id as a plain int, or None when it is unusable."""
    try:
        value = row["id"]
        return None if pd.isna(value) else int(value)
    except (KeyError, TypeError, ValueError):
        return None


def _selection_key(base: str, df: pd.DataFrame) -> str:
    """Widget key tied to the current result set.

    ``st.dataframe`` remembers the selected **row position**, not the company. Keep
    one key across a filter change and position 3 of the old list silently becomes
    position 3 of the new one — the card opens a company the user never clicked.
    A key derived from the visible ids resets the selection instead; state left by
    previous result sets is dropped so session state cannot grow without bound.
    """
    ids = pd.to_numeric(df["id"], errors="coerce").dropna().astype("int64") if "id" in df else []
    digest = hashlib.blake2s(
        pd.Series(ids, dtype="int64").to_numpy().tobytes(), digest_size=8
    ).hexdigest()
    key = f"{base}_{digest}"
    for stale in [
        k
        for k in list(st.session_state)
        if isinstance(k, str) and k.startswith(f"{base}_") and k != key
    ]:
        st.session_state.pop(stale, None)
    return key


def selectable_table(df: pd.DataFrame, cols: list[str], key: str) -> None:
    """Table whose first column (checkbox) opens the company's detail card."""
    cols = [c for c in cols if c in df.columns]
    col_config = {c: st.column_config.LinkColumn(c) for c in ("website", "yc_url") if c in cols}
    event = st.dataframe(
        df[cols],
        width="stretch",
        hide_index=True,
        column_config=col_config,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )
    rows = getattr(getattr(event, "selection", None), "rows", None) or []
    if rows:
        pos = rows[0]
        if 0 <= pos < len(df):
            new_id = _row_id(df.iloc[pos])
            if new_id is not None and new_id != selected_id():
                # No st.rerun() here on purpose: ``on_select="rerun"`` already reran us,
                # and the card is drawn further down in this very pass. Re-running again
                # made every row click cost two full renders.
                select_company(new_id)


def card_text(row: pd.Series) -> str:
    """Plain-text version of a company card (for copy/paste into notes or email)."""
    parts = [
        f"{row.get('name', '')} — {row.get('one_liner', '')}",
        f"Industry: {row.get('industry', '')} / {row.get('subindustry', '')}",
        f"Batch: {row.get('batch', '')} | Status: {row.get('status', '')} "
        f"| Team: {row.get('team_size', '')} | Score: {row.get('score', '')}",
        f"Investability: {row.get('investability', '')}",
    ]
    if str(row.get("ai_description", "")).strip():
        parts += ["", f"AI description: {row['ai_description']}"]
    if str(row.get("ai_risks", "")).strip():
        parts += ["", f"Risks: {row['ai_risks']}"]
    links = [
        str(row[c]) for c in LINK_COLUMNS if c in row and str(row.get(c, "")).startswith("http")
    ]
    if links:
        parts += ["", "Links: " + " | ".join(links)]
    return "\n".join(parts)


@st.fragment
def note_section_lazy(row: pd.Series, place: str) -> None:
    """Notes behind a button — the cheap variant used in the 50-card list.

    Rendering the editor for every card costs ~6 widgets each (≈350 per page), which
    is what made the card list slow. Here a single button stands in for it until the
    user actually wants to write something.
    """
    cid = _row_id(row)
    if cid is None:
        return
    opened = f"notes_open_{place}_{cid}"
    if not st.session_state.get(opened):
        if st.button("📝 Notes on this company", key=f"opennotes_{place}_{cid}"):
            st.session_state[opened] = True
            st.rerun(scope="fragment")
        return
    with st.container(border=True):
        _note_form(row, place)


@st.fragment
def note_section(row: pd.Series, place: str) -> None:
    """Collapsed per-company notes. A fragment, so saving doesn't rerun the page."""
    cid = _row_id(row)
    if cid is None:
        return
    with st.expander("📝 Notes on this company"):
        _note_form(row, place)


def _note_form(row: pd.Series, place: str) -> None:
    """The note widgets themselves (favorite / stage / tags / note + save)."""
    cid = _row_id(row)
    if cid is None:
        return
    if saved_recently(cid):
        st.success("Saved ✅ — your changes were written.")
    if not is_owner():
        st.caption(
            "👀 Your personal notes: fully functional, but they live only in this "
            "browser tab — the owner cannot see them and they disappear when you "
            "refresh the page."
        )
    c1, c2 = st.columns([1, 2])
    fav = c1.checkbox("⭐ Favorite", value=bool(row.get("watchlist")), key=f"fav_{place}_{cid}")
    stages = list(user_data.STAGES)
    cur_stage = row.get("my_stage", user_data.DEFAULT_STAGE)
    stage = c2.selectbox(
        "Funnel stage",
        stages,
        index=stages.index(cur_stage) if cur_stage in stages else 0,
        key=f"stage_{place}_{cid}",
    )
    tags = st.text_input(
        "Tags (comma-separated)", value=str(row.get("my_tags", "")), key=f"tags_{place}_{cid}"
    )
    notes = st.text_area(
        "Note", value=str(row.get("my_notes", "")), key=f"notes_{place}_{cid}", height=110
    )
    if st.button("💾 Save", type="primary", key=f"save_{place}_{cid}"):
        try:
            save_one(
                cid,
                {
                    "watchlist": bool(fav),
                    "my_stage": stage,
                    "my_tags": tags,
                    "my_notes": notes,
                },
            )
            mark_saved(cid)
            st.rerun(scope="app")  # refresh stars, counters and the table
        except Exception as exc:
            st.error(f"Could not save: {exc}")


def company_body(row: pd.Series) -> None:
    """Shared company details (used by the detail card and the card list)."""
    sub = f" / {row['subindustry']}" if str(row.get("subindustry", "")).strip() else ""
    st.markdown(
        f"**Industry:** {row.get('industry', '')}{sub}  \n"
        f"**Batch:** {row.get('batch', '')}  \n"
        f"**Status:** {row.get('status', '')} — {row.get('investability', '')}  \n"
        f"**Funnel stage:** {row.get('my_stage', '')}  \n"
        f"**Team:** {row.get('team_size', '')}"
    )
    if str(row.get("my_tags", "")).strip():
        st.markdown(f"**My tags:** {row['my_tags']}")
    if str(row.get("ai_description", "")).strip():
        st.markdown(f"**AI description:** {row['ai_description']}")
    if str(row.get("ai_risks", "")).strip():
        st.markdown(f"**Risks to check:** {row['ai_risks']}")
    links = [
        f"[{c.replace('_url', '').replace('_', ' ').title() or 'Website'}]({row[c]})"
        for c in LINK_COLUMNS
        if c in row and str(row.get(c, "")).startswith("http")
    ]
    if links:
        st.markdown("**Links:** " + " · ".join(links))


def close_card(table_key: str | None) -> None:
    """Close the detail card **and** untick the row that opened it.

    Clearing only ``selected_id`` is not enough: the table widget still holds the
    selection, so the next fragment rerun reads it back and the card reopens — the ✕
    looked like it did nothing. Dropping the widget's state resets the tick as well.
    """
    select_company(None)
    if table_key:
        st.session_state.pop(table_key, None)


def detail_card(df: pd.DataFrame, place: str, table_key: str | None = None) -> None:
    """Full card for the company selected in the table.

    Rendered inside :func:`table_and_card`'s fragment, hence the fragment-scoped
    reruns: closing the card must repaint this block only.
    """
    cid = selected_id()
    if cid is None:
        return
    match = df[df["id"] == cid]
    if match.empty:
        st.info("The selected company does not match the current filters.")
        if st.button("Clear the selection", key=f"clear_sel_{place}"):
            close_card(table_key)
            st.rerun(scope="fragment")
        return
    row = match.iloc[0]

    with st.container(border=True):
        head, copy_col, close = st.columns([6, 1.4, 0.6])
        star = "⭐ " if bool(row.get("watchlist")) else ""
        head.markdown(f"### {star}{row['name']}")
        head.caption(row.get("one_liner", ""))
        with copy_col.popover("📋 Copy", width="stretch"):
            st.caption("Copy the card")
            st.code(card_text(row), language=None)
        if close.button("✕", key=f"close_{place}", help="Close the card"):
            close_card(table_key)
            st.rerun(scope="fragment")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Score", f"{row.get('score', '')}")
        m2.metric("Team", f"{row.get('team_size', '')}")
        m3.metric("Batch", f"{row.get('batch', '')}")
        m4.metric("Status", f"{row.get('status', '')}")

        company_body(row)
        note_section(row, place=f"{place}_detail")


#: Columns shown in the selectable table, in order.
TABLE_COLUMNS = [
    "name",
    "batch",
    "industry",
    "subindustry",
    "status",
    "investability",
    "my_stage",
    "team_size",
    "score",
    "one_liner",
    "website",
    "yc_url",
]


@st.fragment
def table_and_card(
    df: pd.DataFrame,
    key: str,
    place: str,
    cols: list[str] | None = None,
    table_df: pd.DataFrame | None = None,
) -> None:
    """Table + detail card as one fragment — the fast path for "open a company".

    Picking a row is the most-used interaction on the page, so it must not repaint
    everything: inside a fragment Streamlit reruns only this block, skipping the six
    charts of the Overview tab, the 50 expanders below and the bulk notes editor.

    Every table+card pair **must** go through here. ``detail_card`` closes itself with
    ``st.rerun(scope="fragment")``, which raises outside a fragment — one click on the
    card's ✕ used to replace the whole page with the error screen, whose only recovery
    button wipes the session (a visitor's entire set of notes with it).

    ``table_df`` lets the table show a subset (e.g. a top-N) while the card still
    resolves against the full filtered frame.
    """
    rows = df if table_df is None else table_df
    table_key = _selection_key(key, rows)
    selectable_table(rows.reset_index(drop=True), cols or TABLE_COLUMNS, key=table_key)
    detail_card(df, place=place, table_key=table_key)


# --------------------------------------------------------------------------- tabs
def _bar_count(
    df: pd.DataFrame, col: str, title: str, *, top: int | None = None, order=None
) -> None:
    counts = df[col].dropna().value_counts()
    if order is not None:
        counts = counts.reindex(list(order)).dropna()
    elif top:
        counts = counts.head(top)
    if counts.empty:
        return
    fig = px.bar(
        x=counts.values,
        y=counts.index.astype(str),
        orientation="h",
        labels={"x": "Companies", "y": ""},
        title=title,
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=380)
    fig.update_traces(marker_color="#4C9BE8")
    st.plotly_chart(fig, width="stretch")


def year_bar(df: pd.DataFrame):
    """Companies-per-batch-year bar chart, or None when there is nothing to draw.

    The x axis is explicitly **categorical**: years look like numbers, so Plotly
    puts them on a continuous axis and pads it with ticks like 2020.5 — glaringly
    wrong with a single year selected.
    """
    if px is None or "batch_year" not in df.columns:
        return None
    years = pd.to_numeric(df["batch_year"], errors="coerce").dropna().astype(int)
    if years.empty:
        return None
    counts = years.value_counts().sort_index()
    fig = px.bar(
        x=counts.index.astype(str),
        y=counts.values,
        labels={"x": "Batch year", "y": "Companies"},
        title="Companies by batch year",
    )
    fig.update_traces(marker_color="#4C9BE8")
    fig.update_xaxes(type="category")
    return fig


def _pie(df: pd.DataFrame, col: str, title: str) -> None:
    counts = df[col].dropna().value_counts()
    if counts.empty:
        return
    fig = px.pie(names=counts.index.astype(str), values=counts.values, title=title, hole=0.45)
    st.plotly_chart(fig, width="stretch")


def tab_overview(filtered: pd.DataFrame, total: int, all_df: pd.DataFrame) -> None:
    st.caption(f"Showing **{len(filtered)}** of {total} companies")
    if filtered.empty:
        st.info("No company matches the current filters — relax them in the sidebar.")
        return

    fav_total = int(all_df.get("watchlist", pd.Series(dtype=bool)).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies", len(filtered))
    c2.metric(
        "⭐ Favorites",
        int(filtered.get("watchlist", pd.Series(dtype=bool)).sum()),
        help=f"Favorites in total, ignoring filters: {fav_total}",
    )
    c3.metric("Average score", f"{filtered['score'].mean():.0f}" if len(filtered) else "—")
    c4.metric("Industries", filtered["industry"].nunique())

    st.divider()

    if px is None:
        st.info("Install `plotly` to see the charts.")
    else:
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            _bar_count(filtered, "industry", "Companies by industry", top=15)
        with r1c2:
            if "subindustry" in filtered.columns:
                _bar_count(filtered, "subindustry", "Companies by subindustry", top=15)

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            year_fig = year_bar(filtered)
            if year_fig is not None:
                st.plotly_chart(year_fig, width="stretch")
        with r2c2:
            fig = px.histogram(filtered, x="score", nbins=20, title="Score distribution")
            fig.update_traces(marker_color="#7C5CFC")
            st.plotly_chart(fig, width="stretch")

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            _pie(filtered, "status", "Status breakdown (YC)")
        with r3c2:
            if "my_stage" in filtered.columns:
                _bar_count(filtered, "my_stage", "My funnel (stages)", order=user_data.STAGES)

    st.divider()
    st.subheader("🏆 Top by score")
    n = st.slider("How many to show", 5, 50, 10, key="topn")
    top_df = filtered.sort_values("score", ascending=False).head(n).reset_index(drop=True)
    st.markdown("👁 **Open a card** — tick a company in the first column")
    table_and_card(
        filtered,
        key="table_top",
        place="overview",
        cols=["name", "industry", "subindustry", "status", "score", "team_size", "one_liner"],
        table_df=top_df,
    )


def pages_of(df: pd.DataFrame, size: int = PAGE_SIZE) -> int:
    """How many pages ``df`` needs (at least one, even when empty)."""
    return max(1, -(-len(df) // size))


def paginate(df: pd.DataFrame, page: int, size: int = PAGE_SIZE) -> tuple[pd.DataFrame, int, int]:
    """``(rows of this page, first row index, page count)`` — page is clamped."""
    pages = max(1, -(-len(df) // size))
    page = min(max(int(page), 1), pages)
    start = (page - 1) * size
    return df.iloc[start : start + size], start, pages


def _step_page(delta: int, pages: int, key: str = "card_page") -> None:
    """Move the pager by ``delta``, clamped to the pages that exist."""
    page = int(st.session_state.get(key, 1)) + delta
    st.session_state[key] = min(max(page, 1), max(pages, 1))


def _page_number(pages: int, key: str = "card_page") -> int:
    """← / → pager stored in session state (nicer than a +/- number input).

    The step runs as an ``on_click`` **callback**: Streamlit executes it before the
    script reruns, so the buttons are drawn from the page we are actually on.
    Updating the page after drawing them left "Next →" clickable on the last page.

    ``key`` keeps several pagers (cards, notes) independent of each other.
    """
    page = min(max(int(st.session_state.get(key, 1)), 1), pages)
    st.session_state[key] = page
    prev_col, label_col, next_col = st.columns([1, 3, 1])
    prev_col.button(
        "← Back",
        width="stretch",
        disabled=page <= 1,
        key=f"{key}_prev",
        on_click=_step_page,
        args=(-1, pages, key),
    )
    next_col.button(
        "Next →",
        width="stretch",
        disabled=page >= pages,
        key=f"{key}_next",
        on_click=_step_page,
        args=(1, pages, key),
    )
    label_col.markdown(
        f"<div style='text-align:center;padding-top:0.45rem'>Page <b>{page}</b> of {pages}</div>",
        unsafe_allow_html=True,
    )
    return page


def tab_companies(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No company matches the current filters — relax them in the sidebar.")
        return
    st.markdown("👁 **Open a card** — tick a company in the first column")

    table_and_card(filtered, key="table_all", place="companies")

    st.divider()
    st.subheader("Company cards")

    sort_label = st.selectbox("Sort by", list(SORT_OPTIONS), key="card_sort")
    sort_col, ascending = SORT_OPTIONS[sort_label]
    ranked = filtered.sort_values(sort_col, ascending=ascending, na_position="last")

    chunk, start, pages = paginate(ranked, _page_number(pages_of(ranked)))
    st.caption(f"Companies {start + 1}–{start + len(chunk)} of {len(ranked)}")

    for _, row in chunk.iterrows():
        star = "⭐ " if bool(row.get("watchlist")) else ""
        with st.expander(
            f"{star}{row['name']} — {row.get('one_liner', '')}  (score {row.get('score', '')})"
        ):
            company_body(row)
            note_section_lazy(row, place="list")


def compare_labels(df: pd.DataFrame) -> dict[str, int]:
    """Picker label → company ``id``, guaranteed unique.

    A name is not a key: dozens of YC companies share one. Picking "Vera" used to
    select every Vera and index the comparison by name, producing duplicate columns
    the renderer refuses. The batch disambiguates; the id settles the rest.
    """
    if df.empty:
        return {}
    name = df["name"].fillna("—").astype(str)
    batch = df["batch"].fillna("").astype(str) if "batch" in df.columns else ""
    label = name if isinstance(batch, str) else name.where(batch == "", name + " · " + batch)
    ids = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    dup = label.duplicated(keep=False)
    label = label.where(~dup, label + " #" + ids.astype(str))
    return {str(k): int(v) for k, v in zip(label, ids, strict=False) if pd.notna(v)}


def comparison_frame(
    df: pd.DataFrame, labels: dict[str, int], picked: list[str], fields: list[str]
) -> pd.DataFrame:
    """Side-by-side frame: one column per picked company, in the picked order."""
    ids = [labels[p] for p in picked if p in labels]
    rows = df[df["id"].isin(ids)].drop_duplicates(subset="id").set_index("id")
    rows = rows.reindex([i for i in ids if i in rows.index])
    comp = rows[[f for f in fields if f in rows.columns]].T
    comp.columns = [p for p in picked if labels.get(p) in rows.index]
    return comp


def tab_compare(filtered: pd.DataFrame) -> None:
    st.subheader("⚖️ Compare companies")
    st.caption("Pick up to 5 companies — they are compared side by side.")
    labels = compare_labels(filtered)
    picked = st.multiselect("Companies", list(labels), max_selections=5, key="compare_pick")
    if not picked:
        st.info("Pick companies above.")
        return
    rows = filtered[filtered["id"].isin([labels[p] for p in picked])]
    fields = [
        c
        for c in [
            "one_liner",
            "industry",
            "subindustry",
            "status",
            "investability",
            "my_stage",
            "batch",
            "team_size",
            "score",
            "website",
            "yc_url",
            "ai_description",
            "ai_risks",
        ]
        if c in rows.columns
    ]
    comp = comparison_frame(filtered, labels, picked, fields).map(_clean_cell)
    st.dataframe(comp, width="stretch")


ANNOTATION_FIELDS = ("watchlist", "my_stage", "my_tags", "my_notes")


def changed_rows(before: pd.DataFrame, after: pd.DataFrame) -> dict[int, dict]:
    """``{id: values}`` for the rows the user actually edited.

    Comparing what was rendered with what came back keeps a save proportional to the
    edit, not to the size of the screen — and it is what makes a save safe next to a
    second session: untouched companies are never rewritten.
    """
    if after is None or after.empty:
        return {}
    old = {}
    for _, r in before.iterrows():
        rid = _row_id(r)
        if rid is not None:
            old[rid] = {f: r.get(f) for f in ANNOTATION_FIELDS if f in before.columns}

    changes: dict[int, dict] = {}
    for _, r in after.iterrows():
        rid = _row_id(r)
        if rid is None:
            continue
        values = {
            "watchlist": user_data.to_bool(r.get("watchlist")),
            "my_stage": r.get("my_stage", user_data.DEFAULT_STAGE),
            "my_tags": r.get("my_tags", ""),
            "my_notes": r.get("my_notes", ""),
        }
        prev = old.get(rid)
        if prev is None:
            changes[rid] = values
            continue
        same = (
            user_data.to_bool(prev.get("watchlist")) == values["watchlist"]
            and str(prev.get("my_stage") or user_data.DEFAULT_STAGE) == str(values["my_stage"])
            and str(prev.get("my_tags") or "") == str(values["my_tags"] or "")
            and str(prev.get("my_notes") or "") == str(values["my_notes"] or "")
        )
        if not same:
            changes[rid] = values
    return changes


def tab_notes(filtered: pd.DataFrame) -> None:
    st.subheader("📝 Notes, tags and funnel")
    if saved_recently(BULK_FLASH_ID):
        n = st.session_state.get("bulk_saved_count")
        st.success(
            f"Saved ✅ — {n} companies written." if n else "Saved ✅ — your changes were written."
        )
    if filtered.empty:
        st.info("No company matches the current filters.")
        return
    owner = is_owner()

    if owner:
        where = (
            "Google Sheet ✅"
            if use_gsheets() and not st.session_state.get("gsheets_error")
            else "a local file ⚠️ (will not survive a restart when hosted)"
        )
        st.caption(
            f"Bulk editing. Storage: **{where}**. The key is the company id (it survives "
            "renames). For a single company its card is easier."
        )
        if use_gsheets() and st.button("🔄 Reload from the sheet", key="reload_sheet"):
            # The sheet is cached per session; press this after editing it directly
            # in Google Sheets, or once a broken connection is fixed.
            refresh_annotations()
            st.rerun()
    else:
        st.info(
            "👀 **Your personal notes.** Edit and save them freely — they live in this "
            "browser tab, are invisible to the owner, and disappear when you refresh "
            "the page.",
            icon="👀",
        )

    editor_cols = [
        c
        for c in ["id", "name", "watchlist", "my_stage", "my_tags", "my_notes"]
        if c in filtered.columns
    ]
    # Deliberately NOT paginated: measured on the real dataset, paging this editor
    # changed a filter change by 1.06 s -> 1.12 s (i.e. nothing), while it would cost
    # the ability to edit many companies in one pass. The rerun cost lives elsewhere
    # (chart building and widget serialisation) — see AI_USAGE/PROJECT_MEMORY.md.
    edited = st.data_editor(
        filtered[editor_cols].copy(),
        width="stretch",
        hide_index=True,
        disabled=["id", "name"],
        column_config={
            "watchlist": st.column_config.CheckboxColumn("⭐ Favorite"),
            "my_stage": st.column_config.SelectboxColumn("Stage", options=list(user_data.STAGES)),
            "my_tags": st.column_config.TextColumn("Tags (comma-separated)"),
            "my_notes": st.column_config.TextColumn("Notes", width="large"),
        },
        # Keyed by the rows on screen: st.data_editor stores edits by row *position*,
        # so a fixed key would replay them onto whatever a filter change brought in.
        key=_selection_key("annotations_editor", filtered),
    )

    if st.button("💾 Save the notes", type="primary"):
        # Only what the owner actually changed is written. Writing every visible row
        # cost ~20 s of blocking work on the unfiltered view and pushed thousands of
        # empty rows into the store — where they could overwrite a concurrent edit.
        changes = changed_rows(filtered[editor_cols], edited)
        try:
            if not changes:
                st.info("Nothing to save — no changes on this screen.")
            else:
                n = upsert_annotations(changes)
                mark_saved(BULK_FLASH_ID)
                st.session_state["bulk_saved_count"] = n
                st.rerun()
        except Exception as exc:
            st.error(f"Could not save: {exc}")


# --------------------------------------------------------------------------- main
def _render() -> None:
    """The dashboard body. Wrapped by :func:`main` so nothing shows a blank crash."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🛰️ YC Scouter — 2020 to now")

    path = dataset_path()
    if path is None or not path.exists():
        st.warning(
            "No dataset found. Build one: File 1 (Base) first, then File 2 (AI) — they "
            "write `data/yc_dataset_*.parquet`. When hosting, commit those files."
        )
        st.stop()
    st.caption(f"Source: `{path.name}`")

    owner_gate()

    try:
        df, data_notes = prepare_data(load_data(str(path), path.stat().st_mtime))
    except DatasetError as exc:
        st.error(f"⚠️ {exc}")
        st.stop()
    if data_notes and is_owner():
        st.warning("The data needed cleaning up: " + " ".join(data_notes))

    df = user_data.merge_annotations(df, load_annotations())

    secrets_error_banner()
    gsheets_error_banner()
    storage_banner()
    if _owner_key() and is_owner():
        st.sidebar.success("🔓 Full access — notes are being saved.")

    filtered = sidebar_filters(df)

    # Sits on the tab bar's line (flush right) via the .st-key-export_row CSS.
    with st.container(key="export_row"):
        _, right = st.columns([5, 1])
        with right:
            export_panel(filtered, key="global")

    overview, companies, compare, notes = st.tabs(
        ["📊 Overview", "🔎 Companies", "⚖️ Compare", "📝 Notes"]
    )
    with overview:
        tab_overview(filtered, total=len(df), all_df=df)
    with companies:
        tab_companies(filtered)
    with compare:
        tab_compare(filtered)
    with notes:
        tab_notes(filtered)


def main() -> None:
    """Entry point with a safety net.

    Streamlit Cloud redacts exception text, so an unexpected error would show an
    unhelpful blank crash page. We catch it, keep the app usable, and surface the
    real reason (plus a reset button, since bad session state is a common cause).
    """
    st.set_page_config(page_title="YC Scouter", page_icon="🛰️", layout="wide")
    try:
        _render()
    except Exception as exc:  # noqa: BLE001 - last-resort UI guard
        # Streamlit's own control-flow signals must pass through untouched.
        if type(exc).__name__ in {"RerunException", "StopException", "RerunData"}:
            raise
        st.error(f"⚠️ Something went wrong: {type(exc).__name__}: {exc}")
        st.caption(
            "The dashboard is not broken — try resetting the filters and the selected "
            "company. If it keeps happening, send the text below to the developer."
        )
        if st.button("♻️ Reset the state and reload"):
            st.session_state.clear()
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.rerun()
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)), language="text")


if __name__ == "__main__":
    main()
