"""YC Scouter — interactive Streamlit dashboard (Russian UI).

Reads the newest dated Parquet produced by the pipeline (it never re-fetches) and
lets you filter, chart, compare, and annotate companies.

Storage for your personal notes/tags/stage is chosen automatically:

* **Google Sheets** when configured in Streamlit secrets (survives restarts —
  required for hosting on Streamlit Community Cloud, whose disk is ephemeral);
* a local **CSV** otherwise (Colab / local use).

Performance note: with ~4k companies, anything built eagerly on every rerun
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
import traceback
from pathlib import Path

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
    "Score (по убыванию)": ("score", False),
    "Score (по возрастанию)": ("score", True),
    "Год батча (новые первыми)": ("batch_year", False),
    "Год батча (старые первыми)": ("batch_year", True),
    "Название (А→Я)": ("name", True),
    "Название (Я→А)": ("name", False),
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

  /* Small italic min/max hints under the "От"/"До" inputs. */
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
            "В датасете нет обязательных колонок: " + ", ".join(missing) + ". "
            "Пересоберите данные кнопкой File 1 (Base), затем File 2 (AI)."
        )

    out = df.copy()
    ids = pd.to_numeric(out["id"], errors="coerce")
    bad = ids.isna().sum()
    if bad:
        out = out[ids.notna()]
        ids = ids[ids.notna()]
        notes.append(f"Пропущено строк без корректного id: {bad}.")
    out["id"] = ids.astype("int64")

    dupes = int(out["id"].duplicated().sum())
    if dupes:
        # Widget keys are built from the id — two rows with the same id crash the app.
        out = out.drop_duplicates(subset="id", keep="first")
        notes.append(f"Схлопнуто дублей по id: {dupes}.")

    added = [c for c in OPTIONAL_DEFAULTS if c not in out.columns]
    for col in added:
        out[col] = OPTIONAL_DEFAULTS[col]
    if added:
        notes.append("Добавлены пустыми отсутствующие колонки: " + ", ".join(added) + ".")

    return out.reset_index(drop=True), notes


def _secrets():
    try:
        return st.secrets
    except Exception:
        return {}


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
    """
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
                "🔒 Не задан ключ доступа (`[app] owner_key` в секретах), поэтому "
                "заметки в общей таблице доступны только на чтение. Добавьте ключ — "
                "и сможете сохранять (см. docs/DEPLOY.md)."
            )
        return
    with st.sidebar.expander("🔒 Ключ доступа"):
        entered = st.text_input("Ключ доступа", type="password", key="owner_key_input")
        if st.button("Войти"):
            if check_owner_key(entered):
                st.rerun()
            else:
                st.error("Неверный ключ.")


def storage_banner() -> None:
    """Explain, in plain words, what happens to the notes this visitor makes."""
    if is_owner():
        if use_gsheets() and not st.session_state.get("gsheets_error"):
            st.success(
                "🔓 **Полный доступ.** Ваши заметки сохраняются в постоянное хранилище "
                "(Google Таблица) — они останутся на месте после обновления страницы, "
                "перезапуска приложения и обновления данных.",
                icon="✅",
            )
        elif not use_gsheets():
            st.info(
                "🔓 **Полный доступ.** Заметки сохраняются в локальный файл. "
                "На хостинге подключите Google Таблицу (docs/DEPLOY.md), иначе они "
                "пропадут при перезапуске приложения.",
                icon="💾",
            )
    else:
        st.info(
            "👀 **Режим просмотра.** Смотрите и фильтруйте всё без ограничений. "
            "Заметки, которые вы здесь оставите, видны **только вам** и **исчезнут при "
            "обновлении страницы** — они не попадают в общее хранилище. Чтобы заметки "
            "сохранялись навсегда, введите ключ доступа в панели слева.",
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
            return user_data.empty_user_frame()
        st.session_state[SHEETS_CACHE] = loaded
        st.session_state.pop(SHEETS_BLOCKED, None)
        st.session_state.pop("gsheets_error", None)
        return loaded
    return user_data.load_user_data(USER_DATA_CSV)


def gsheets_error_banner() -> None:
    """Actionable message when the Sheets credentials are rejected."""
    err = st.session_state.get("gsheets_error")
    if not err:
        return
    if "invalid_grant" in err or "account not found" in err:
        st.warning(
            "⚠️ **Google Таблица не подключена** — заметки сейчас сохраняются только "
            "на время сессии.\n\n"
            "Google отклонил ключ сервисного аккаунта: такого аккаунта больше нет либо "
            "ключ устарел. Как починить:\n"
            "1. Google Cloud Console → **IAM & Admin → Service Accounts** — проверьте, "
            "что аккаунт из `client_email` существует (если нет — создайте заново).\n"
            "2. У этого аккаунта → **Keys → Add key → JSON** — скачайте **новый** ключ.\n"
            "3. Streamlit → **Settings → Secrets** — замените `private_key`, "
            "`private_key_id`, `client_email` значениями из нового файла "
            "(`private_key` копируйте целиком, вместе с символами `\\n`).\n"
            "4. Не забудьте открыть доступ к таблице для `client_email` (роль «Редактор»)."
        )
    else:
        st.warning(f"⚠️ Google Таблица недоступна — заметки не сохраняются. Причина: {err}")


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
                "Google Таблица недоступна — сохранение отключено, чтобы не стереть "
                "уже сохранённые заметки. Почините доступ и нажмите «Обновить из таблицы»."
            )
        gsheets.save(_secrets(), df)
        st.session_state[SHEETS_CACHE] = user_data._ensure_columns(df)
    else:
        user_data.save_user_data(df, path=USER_DATA_CSV)


def save_one(row_id: int, values: dict) -> None:
    """Upsert a single company's annotations into the store."""
    store = user_data._ensure_columns(load_annotations()).set_index("id")
    store.loc[int(row_id)] = values
    save_annotations(store.reset_index())


# ------------------------------------------------------------------------- export
def _clean_cell(v: object) -> object:
    if isinstance(v, (list, tuple)):
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
    doing it on every rerun costs seconds of CPU and hundreds of MB on 4k rows."""
    with st.popover("⬇️ Экспорт", width="stretch"):
        st.caption(f"Отфильтровано: **{len(df)}** компаний")
        fmt = st.radio("Формат", list(EXPORT_FORMATS), horizontal=True, key=f"fmt_{key}")
        state_key = f"export_{key}"
        if st.button("Подготовить файл", key=f"prep_{key}", width="stretch"):
            with st.spinner(f"Готовлю {fmt}…"):
                st.session_state[state_key] = {
                    "fmt": fmt,
                    "n": len(df),
                    "data": export_bytes(df, fmt),
                }
        ready = st.session_state.get(state_key)
        if ready:
            ext, mime = EXPORT_FORMATS[ready["fmt"]]
            st.download_button(
                f"⬇️ Скачать {ready['fmt']} ({ready['n']} компаний)",
                ready["data"],
                f"yc_scouter.{ext}",
                mime,
                width="stretch",
                key=f"dl_{key}",
            )
            if ready["n"] != len(df) or ready["fmt"] != fmt:
                st.caption("⚠️ Выбор изменился — нажмите «Подготовить файл» ещё раз.")


# ------------------------------------------------------------------------ sidebar
def keep_valid(selected: object, options: list) -> list:
    """The part of a previous selection that still exists in ``options``."""
    return [s for s in (selected or []) if s in options]


def _int_range(label: str, key: str, series: pd.Series) -> tuple[int | None, int | None]:
    """Two integer inputs (От / До) with the data's own min/max as hints.

    Leaving a field empty removes that bound entirely.
    """
    st.sidebar.markdown(f"**{label}**")
    c1, c2 = st.sidebar.columns(2)
    values = pd.to_numeric(series, errors="coerce").dropna()
    lo_hint = int(values.min()) if len(values) else 0
    hi_hint = int(values.max()) if len(values) else 0

    lo = c1.number_input(
        "От",
        min_value=0,
        value=None,
        step=1,
        format="%d",
        key=f"{key}_lo",
        help="Пусто — без нижней границы",
    )
    c1.markdown(f"<div class='range-hint'>мин. {lo_hint}</div>", unsafe_allow_html=True)
    hi = c2.number_input(
        "До",
        min_value=0,
        value=None,
        step=1,
        format="%d",
        key=f"{key}_hi",
        help="Пусто — без верхней границы",
    )
    c2.markdown(f"<div class='range-hint'>макс. {hi_hint}</div>", unsafe_allow_html=True)
    return (int(lo) if lo is not None else None, int(hi) if hi is not None else None)


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔍 Фильтры")
    st.sidebar.caption("Пустое поле «От» или «До» = без ограничения с этой стороны.")
    query = st.sidebar.text_input("Поиск (имя / идея / теги / заметки)")

    industries = st.sidebar.multiselect("Индустрия", sorted(df["industry"].dropna().unique()))

    subindustries = []
    if "subindustry" in df.columns:
        pool = df[df["industry"].isin(industries)] if industries else df
        sub_opts = sorted(pool["subindustry"].dropna().unique())
        # Picking an industry rewrites these options, and Streamlit drops the whole
        # selection when options change — keep the part that is still valid.
        st.session_state["sub_pick"] = keep_valid(st.session_state.get("sub_pick"), sub_opts)
        subindustries = st.sidebar.multiselect("Подиндустрия", sub_opts, key="sub_pick")

    statuses = st.sidebar.multiselect("Статус (YC)", sorted(df["status"].dropna().unique()))

    investabilities = []
    if "investability" in df.columns:
        investabilities = st.sidebar.multiselect(
            "Investability", sorted(df["investability"].dropna().unique())
        )

    stages = st.sidebar.multiselect("Стадия воронки", list(user_data.STAGES))

    tag_opts = filters.all_tags(df)
    tags = st.sidebar.multiselect("Мои теги / лейблы", tag_opts) if tag_opts else []

    watchlist_only = st.sidebar.toggle("⭐ Только избранные", value=False)

    years = sorted(int(y) for y in df["batch_year"].dropna().unique())
    year_sel = st.sidebar.multiselect("Год батча", years)

    score_lo, score_hi = _int_range("Score (0–100)", "score", df["score"])
    team_lo, team_hi = _int_range("Размер команды", "team", df["team_size"])

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
        f"Индустрия: {row.get('industry', '')} / {row.get('subindustry', '')}",
        f"Батч: {row.get('batch', '')} | Статус: {row.get('status', '')} "
        f"| Команда: {row.get('team_size', '')} | Score: {row.get('score', '')}",
        f"Investability: {row.get('investability', '')}",
    ]
    if str(row.get("ai_description", "")).strip():
        parts += ["", f"AI-описание: {row['ai_description']}"]
    if str(row.get("ai_risks", "")).strip():
        parts += ["", f"Риски: {row['ai_risks']}"]
    links = [
        str(row[c]) for c in LINK_COLUMNS if c in row and str(row.get(c, "")).startswith("http")
    ]
    if links:
        parts += ["", "Ссылки: " + " | ".join(links)]
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
        if st.button("📝 Заметки о компании", key=f"opennotes_{place}_{cid}"):
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
    with st.expander("📝 Заметки о компании"):
        _note_form(row, place)


def _note_form(row: pd.Series, place: str) -> None:
    """The note widgets themselves (favorite / stage / tags / note + save)."""
    cid = _row_id(row)
    if cid is None:
        return
    if not is_owner():
        st.caption(
            "👀 Ваши личные заметки: работают полностью, но живут только в этой "
            "вкладке браузера — они не видны владельцу и пропадут при обновлении "
            "страницы."
        )
    c1, c2 = st.columns([1, 2])
    fav = c1.checkbox("⭐ Избранное", value=bool(row.get("watchlist")), key=f"fav_{place}_{cid}")
    stages = list(user_data.STAGES)
    cur_stage = row.get("my_stage", user_data.DEFAULT_STAGE)
    stage = c2.selectbox(
        "Стадия воронки",
        stages,
        index=stages.index(cur_stage) if cur_stage in stages else 0,
        key=f"stage_{place}_{cid}",
    )
    tags = st.text_input(
        "Теги (через запятую)", value=str(row.get("my_tags", "")), key=f"tags_{place}_{cid}"
    )
    notes = st.text_area(
        "Заметка", value=str(row.get("my_notes", "")), key=f"notes_{place}_{cid}", height=110
    )
    if st.button("💾 Сохранить", type="primary", key=f"save_{place}_{cid}"):
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
            st.rerun(scope="app")  # refresh stars, counters and the table
        except Exception as exc:
            st.error(f"Не удалось сохранить: {exc}")


def company_body(row: pd.Series) -> None:
    """Shared company details (used by the detail card and the card list)."""
    sub = f" / {row['subindustry']}" if str(row.get("subindustry", "")).strip() else ""
    st.markdown(
        f"**Индустрия:** {row.get('industry', '')}{sub}  \n"
        f"**Батч:** {row.get('batch', '')}  \n"
        f"**Статус:** {row.get('status', '')} — {row.get('investability', '')}  \n"
        f"**Стадия воронки:** {row.get('my_stage', '')}  \n"
        f"**Команда:** {row.get('team_size', '')}"
    )
    if str(row.get("my_tags", "")).strip():
        st.markdown(f"**Мои теги:** {row['my_tags']}")
    if str(row.get("ai_description", "")).strip():
        st.markdown(f"**AI-описание:** {row['ai_description']}")
    if str(row.get("ai_risks", "")).strip():
        st.markdown(f"**Риски к проверке:** {row['ai_risks']}")
    links = [
        f"[{c.replace('_url', '').replace('_', ' ').title() or 'Website'}]({row[c]})"
        for c in LINK_COLUMNS
        if c in row and str(row.get(c, "")).startswith("http")
    ]
    if links:
        st.markdown("**Ссылки:** " + " · ".join(links))


def detail_card(df: pd.DataFrame, place: str) -> None:
    """Full card for the company selected in the table.

    Rendered inside :func:`table_and_card`'s fragment, hence the fragment-scoped
    reruns: closing the card must repaint this block only.
    """
    cid = selected_id()
    if cid is None:
        return
    match = df[df["id"] == cid]
    if match.empty:
        st.info("Выбранная компания не проходит текущие фильтры.")
        if st.button("Сбросить выбор", key=f"clear_sel_{place}"):
            select_company(None)
            st.rerun(scope="fragment")
        return
    row = match.iloc[0]

    with st.container(border=True):
        head, copy_col, close = st.columns([6, 1.4, 0.6])
        star = "⭐ " if bool(row.get("watchlist")) else ""
        head.markdown(f"### {star}{row['name']}")
        head.caption(row.get("one_liner", ""))
        with copy_col.popover("📋 Скопировать", width="stretch"):
            st.caption("Скопировать карточку")
            st.code(card_text(row), language=None)
        if close.button("✕", key=f"close_{place}", help="Закрыть карточку"):
            select_company(None)
            st.rerun(scope="fragment")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Score", f"{row.get('score', '')}")
        m2.metric("Команда", f"{row.get('team_size', '')}")
        m3.metric("Батч", f"{row.get('batch', '')}")
        m4.metric("Статус", f"{row.get('status', '')}")

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
def table_and_card(df: pd.DataFrame, key: str, place: str) -> None:
    """Table + detail card as one fragment — the fast path for "open a company".

    Picking a row is the most-used interaction on the page, so it must not repaint
    everything: inside a fragment Streamlit reruns only this block, skipping the six
    charts of "Обзор", the 50 expanders below and the bulk notes editor.
    """
    selectable_table(df.reset_index(drop=True), TABLE_COLUMNS, key=_selection_key(key, df))
    detail_card(df, place=place)


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
        labels={"x": "Компаний", "y": ""},
        title=title,
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=380)
    fig.update_traces(marker_color="#4C9BE8")
    st.plotly_chart(fig, width="stretch")


def _pie(df: pd.DataFrame, col: str, title: str) -> None:
    counts = df[col].dropna().value_counts()
    if counts.empty:
        return
    fig = px.pie(names=counts.index.astype(str), values=counts.values, title=title, hole=0.45)
    st.plotly_chart(fig, width="stretch")


def tab_overview(filtered: pd.DataFrame, total: int, all_df: pd.DataFrame) -> None:
    st.caption(f"Показано **{len(filtered)}** из {total} компаний")
    if filtered.empty:
        st.info("Под текущие фильтры не попала ни одна компания — ослабьте условия слева.")
        return

    fav_total = int(all_df.get("watchlist", pd.Series(dtype=bool)).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Компаний", len(filtered))
    c2.metric(
        "⭐ В избранном",
        int(filtered.get("watchlist", pd.Series(dtype=bool)).sum()),
        help=f"Всего в избранном (без учёта фильтров): {fav_total}",
    )
    c3.metric("Средний score", f"{filtered['score'].mean():.0f}" if len(filtered) else "—")
    c4.metric("Индустрий", filtered["industry"].nunique())

    st.divider()

    if px is None:
        st.info("Установи `plotly`, чтобы видеть графики.")
    else:
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            _bar_count(filtered, "industry", "Компании по индустриям", top=15)
        with r1c2:
            if "subindustry" in filtered.columns:
                _bar_count(filtered, "subindustry", "Компании по подиндустриям", top=15)

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            yr = filtered.dropna(subset=["batch_year"]).copy()
            if len(yr):
                yr["batch_year"] = yr["batch_year"].astype(int)
                counts = yr["batch_year"].value_counts().sort_index()
                fig = px.bar(
                    x=counts.index.astype(str),
                    y=counts.values,
                    labels={"x": "Год батча", "y": "Компаний"},
                    title="Компании по годам батча",
                )
                fig.update_traces(marker_color="#4C9BE8")
                st.plotly_chart(fig, width="stretch")
        with r2c2:
            fig = px.histogram(filtered, x="score", nbins=20, title="Распределение score")
            fig.update_traces(marker_color="#7C5CFC")
            st.plotly_chart(fig, width="stretch")

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            _pie(filtered, "status", "Разбивка по статусам (YC)")
        with r3c2:
            if "my_stage" in filtered.columns:
                _bar_count(filtered, "my_stage", "Моя воронка (стадии)", order=user_data.STAGES)

    st.divider()
    st.subheader("🏆 Топ по score")
    n = st.slider("Сколько показать", 5, 50, 10, key="topn")
    top_df = filtered.sort_values("score", ascending=False).head(n).reset_index(drop=True)
    st.markdown("👁 **Показать карточку** — отметьте компанию в первом столбце")
    selectable_table(
        top_df,
        ["name", "industry", "subindustry", "status", "score", "team_size", "one_liner"],
        key="table_top",
    )
    detail_card(filtered, place="overview")


def _page_number(pages: int) -> int:
    """← / → pager stored in session state (nicer than a +/- number input)."""
    page = int(st.session_state.get("card_page", 1))
    page = min(max(page, 1), pages)
    prev_col, label_col, next_col = st.columns([1, 3, 1])
    if prev_col.button("← Назад", width="stretch", disabled=page <= 1, key="page_prev"):
        page -= 1
    if next_col.button("Вперёд →", width="stretch", disabled=page >= pages, key="page_next"):
        page += 1
    page = min(max(page, 1), pages)
    st.session_state["card_page"] = page
    label_col.markdown(
        f"<div style='text-align:center;padding-top:0.45rem'>Страница <b>{page}</b> из {pages}"
        "</div>",
        unsafe_allow_html=True,
    )
    return page


def tab_companies(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("Под текущие фильтры не попала ни одна компания — ослабьте условия слева.")
        return
    st.markdown("👁 **Показать карточку** — отметьте компанию в первом столбце")

    table_and_card(filtered, key="table_all", place="companies")

    st.divider()
    st.subheader("Карточки компаний")

    sort_label = st.selectbox("Сортировка", list(SORT_OPTIONS), key="card_sort")
    sort_col, ascending = SORT_OPTIONS[sort_label]
    ranked = filtered.sort_values(sort_col, ascending=ascending, na_position="last")

    pages = max(1, -(-len(ranked) // PAGE_SIZE))
    page = _page_number(pages)
    start = (page - 1) * PAGE_SIZE
    chunk = ranked.iloc[start : start + PAGE_SIZE]
    st.caption(f"Компании {start + 1}–{min(start + PAGE_SIZE, len(ranked))} из {len(ranked)}")

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
    st.subheader("⚖️ Сравнение компаний")
    st.caption("Выбери до 5 компаний — сравнение колонками бок о бок.")
    labels = compare_labels(filtered)
    picked = st.multiselect("Компании", list(labels), max_selections=5, key="compare_pick")
    if not picked:
        st.info("Выбери компании выше.")
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


def tab_notes(filtered: pd.DataFrame) -> None:
    st.subheader("📝 Заметки, теги и воронка")
    if filtered.empty:
        st.info("Под текущие фильтры не попала ни одна компания.")
        return
    owner = is_owner()

    if owner:
        where = (
            "Google Таблица ✅"
            if use_gsheets() and not st.session_state.get("gsheets_error")
            else "локальный файл ⚠️ (не переживёт перезапуск на хостинге)"
        )
        st.caption(
            f"Массовое редактирование. Хранилище: **{where}**. Ключ — id компании "
            "(переживает переименования). Для одной компании удобнее её карточка."
        )
        if use_gsheets() and st.button("🔄 Обновить из таблицы", key="reload_sheet"):
            # The sheet is cached per session; press this after editing it directly
            # in Google Sheets, or once a broken connection is fixed.
            refresh_annotations()
            st.rerun()
    else:
        st.info(
            "👀 **Ваши личные заметки.** Редактируйте и сохраняйте как угодно — они "
            "живут в этой вкладке браузера, не видны владельцу и пропадут при "
            "обновлении страницы.",
            icon="👀",
        )

    editor_cols = [
        c
        for c in ["id", "name", "watchlist", "my_stage", "my_tags", "my_notes"]
        if c in filtered.columns
    ]
    edited = st.data_editor(
        filtered[editor_cols].copy(),
        width="stretch",
        hide_index=True,
        disabled=["id", "name"],
        column_config={
            "watchlist": st.column_config.CheckboxColumn("⭐ Избранное"),
            "my_stage": st.column_config.SelectboxColumn("Стадия", options=list(user_data.STAGES)),
            "my_tags": st.column_config.TextColumn("Теги (через запятую)"),
            "my_notes": st.column_config.TextColumn("Заметки", width="large"),
        },
        key="annotations_editor",
    )

    if st.button("💾 Сохранить заметки", type="primary"):
        store = user_data._ensure_columns(load_annotations()).set_index("id")
        for _, r in edited.iterrows():
            rid = _row_id(r)
            if rid is None:
                continue
            store.loc[rid] = {
                "watchlist": user_data.to_bool(r.get("watchlist")),
                "my_stage": r.get("my_stage", user_data.DEFAULT_STAGE),
                "my_tags": r.get("my_tags", ""),
                "my_notes": r.get("my_notes", ""),
            }
        try:
            save_annotations(store.reset_index())
            st.success(f"Сохранено для {len(edited)} компаний.")
            st.rerun()
        except Exception as exc:
            st.error(f"Не удалось сохранить: {exc}")


# --------------------------------------------------------------------------- main
def _render() -> None:
    """The dashboard body. Wrapped by :func:`main` so nothing shows a blank crash."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🛰️ YC Scouter — 2020–настоящее")

    path = dataset_path()
    if path is None or not path.exists():
        st.warning(
            "Датасет не найден. Собери его: сначала File 1 (Base), затем File 2 (AI) — "
            "они кладут `data/yc_dataset_*.parquet`. На хостинге закоммить файлы в репозиторий."
        )
        st.stop()
    st.caption(f"Источник: `{path.name}`")

    owner_gate()

    try:
        df, data_notes = prepare_data(load_data(str(path), path.stat().st_mtime))
    except DatasetError as exc:
        st.error(f"⚠️ {exc}")
        st.stop()
    if data_notes and is_owner():
        st.warning("Данные пришлось подчистить: " + " ".join(data_notes))

    df = user_data.merge_annotations(df, load_annotations())

    gsheets_error_banner()
    storage_banner()
    if _owner_key() and is_owner():
        st.sidebar.success("🔓 Полный доступ — заметки сохраняются.")

    filtered = sidebar_filters(df)

    # Sits on the tab bar's line (flush right) via the .st-key-export_row CSS.
    with st.container(key="export_row"):
        _, right = st.columns([5, 1])
        with right:
            export_panel(filtered, key="global")

    overview, companies, compare, notes = st.tabs(
        ["📊 Обзор", "🔎 Компании", "⚖️ Сравнение", "📝 Заметки"]
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
        st.error(f"⚠️ Что-то пошло не так: {type(exc).__name__}: {exc}")
        st.caption(
            "Дашборд не сломан — попробуйте сбросить фильтры и выбор компании. "
            "Если ошибка повторяется, отправьте текст ниже разработчику."
        )
        if st.button("♻️ Сбросить состояние и перезагрузить"):
            st.session_state.clear()
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.rerun()
        with st.expander("Технические подробности"):
            st.code("".join(traceback.format_exception(exc)), language="text")


if __name__ == "__main__":
    main()
