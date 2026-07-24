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

import io
import os
import re
import sys
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


def _secrets():
    try:
        return st.secrets
    except Exception:
        return {}


def use_gsheets() -> bool:
    return gsheets is not None and gsheets.is_configured(_secrets())


def _owner_key():
    """The owner password from secrets (``[app] owner_key``), or None."""
    s = _secrets()
    try:
        app = s.get("app") if hasattr(s, "get") else None
        return app.get("owner_key") if app else None
    except Exception:
        return None


def is_owner() -> bool:
    """True for the owner. With no owner_key configured (local/Colab), always
    True — single-user mode. On a shared deployment, only unlocked sessions."""
    if not _owner_key():
        return True
    return bool(st.session_state.get("is_owner", False))


def owner_gate() -> None:
    """Sidebar unlock: turns a visitor session into the owner when an
    ``owner_key`` is configured and entered correctly."""
    key = _owner_key()
    if not key or st.session_state.get("is_owner"):
        return
    with st.sidebar.expander("🔒 Режим владельца"):
        entered = st.text_input("Ключ владельца", type="password", key="owner_key_input")
        if st.button("Разблокировать сохранение"):
            if entered == key:
                st.session_state["is_owner"] = True
                st.rerun()
            else:
                st.error("Неверный ключ.")


def load_annotations() -> pd.DataFrame:
    """Load notes from the configured backend, degrading gracefully on failure.

    A Sheets problem (not shared with the service account, revoked key, API quota)
    must never take the whole dashboard down — we warn and fall back to empty.
    """
    if use_gsheets():
        try:
            return gsheets.load(_secrets())
        except Exception as exc:  # pragma: no cover - network/credentials
            st.session_state["gsheets_error"] = str(exc)
            return user_data.empty_user_frame()
    return user_data.load_user_data(USER_DATA_CSV)


def save_annotations(df: pd.DataFrame) -> None:
    if use_gsheets():
        gsheets.save(_secrets(), df)
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


def export_controls(df: pd.DataFrame, key: str) -> None:
    """On-demand export. Building a 4k-row workbook on every rerun exhausts the
    free-tier limits, so the files are produced only when explicitly requested."""
    state_key = f"export_{key}"
    if st.button("⬇️ Подготовить файлы для скачивания", key=f"btn_{state_key}"):
        with st.spinner("Готовлю CSV и Excel…"):
            st.session_state[state_key] = {
                "n": len(df),
                "csv": _to_csv_bytes(df),
                "xlsx": _to_excel_bytes(df),
            }
    ready = st.session_state.get(state_key)
    if ready:
        c1, c2 = st.columns(2)
        c1.download_button(
            f"⬇️ CSV ({ready['n']} компаний)",
            ready["csv"],
            "yc_scouter.csv",
            "text/csv",
            width="stretch",
            key=f"dl_csv_{key}",
        )
        c2.download_button(
            f"⬇️ Excel ({ready['n']} компаний)",
            ready["xlsx"],
            "yc_scouter.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
            key=f"dl_xlsx_{key}",
        )
        if ready["n"] != len(df):
            st.caption("⚠️ Фильтры изменились — нажми «Подготовить» снова для актуальных данных.")


# ------------------------------------------------------------------------ sidebar
def _int_range(label: str, key: str, *, help_to: str) -> tuple[int | None, int | None]:
    """Two integer inputs (from / to). Empty means "no bound"."""
    st.sidebar.markdown(f"**{label}**")
    c1, c2 = st.sidebar.columns(2)
    lo = c1.number_input("от", min_value=0, value=None, step=1, format="%d", key=f"{key}_lo")
    hi = c2.number_input(
        "до", min_value=0, value=None, step=1, format="%d", key=f"{key}_hi", help=help_to
    )
    return (int(lo) if lo is not None else None, int(hi) if hi is not None else None)


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔍 Фильтры")
    query = st.sidebar.text_input("Поиск (имя / идея / теги / заметки)")

    industries = st.sidebar.multiselect("Индустрия", sorted(df["industry"].dropna().unique()))

    subindustries = []
    if "subindustry" in df.columns:
        pool = df[df["industry"].isin(industries)] if industries else df
        subindustries = st.sidebar.multiselect(
            "Подиндустрия", sorted(pool["subindustry"].dropna().unique())
        )

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

    score_lo, score_hi = _int_range("Score (0–100)", "score", help_to="Пусто = без верхней границы")
    team_lo, team_hi = _int_range("Размер команды", "team", help_to="Пусто = без верхней границы")

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


def selectable_table(df: pd.DataFrame, cols: list[str], key: str) -> None:
    """Render a table whose row click opens the company's detail card."""
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
            new_id = int(df.iloc[pos]["id"])
            if new_id != selected_id():
                select_company(new_id)
                st.rerun()


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


def detail_card(df: pd.DataFrame, place: str) -> None:
    """Full card for the selected company, with inline note editing (owner only)."""
    cid = selected_id()
    if cid is None:
        return
    match = df[df["id"] == cid]
    if match.empty:
        st.info("Выбранная компания не проходит текущие фильтры.")
        if st.button("Сбросить выбор", key=f"clear_sel_{place}"):
            select_company(None)
            st.rerun()
        return
    row = match.iloc[0]

    with st.container(border=True):
        head, close = st.columns([6, 1])
        star = "⭐ " if bool(row.get("watchlist")) else ""
        head.markdown(f"### {star}{row['name']}")
        head.caption(row.get("one_liner", ""))
        if close.button("✕", key=f"close_{place}", help="Закрыть карточку"):
            select_company(None)
            st.rerun()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Score", f"{row.get('score', '')}")
        m2.metric("Команда", f"{row.get('team_size', '')}")
        m3.metric("Батч", f"{row.get('batch', '')}")
        m4.metric("Статус", f"{row.get('status', '')}")

        sub = f" / {row['subindustry']}" if str(row.get("subindustry", "")).strip() else ""
        st.markdown(
            f"**Индустрия:** {row.get('industry', '')}{sub}  \n"
            f"**Investability:** {row.get('investability', '')}"
        )
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

        with st.expander("📋 Скопировать карточку"):
            st.code(card_text(row), language=None)

        _note_editor(row, place)


@st.fragment
def _note_editor(row: pd.Series, place: str) -> None:
    """Notes for one company, inside a fragment so saving doesn't rerun the page."""
    cid = int(row["id"])
    st.markdown("**📝 Мои заметки**")
    if not is_owner():
        st.caption("👀 Режим просмотра — сохранять может только владелец.")
        return

    c1, c2, c3 = st.columns([1, 1, 2])
    fav = c1.checkbox("⭐ Избранное", value=bool(row.get("watchlist")), key=f"fav_{place}_{cid}")
    rating = c2.number_input(
        "Рейтинг 0–5",
        min_value=0,
        max_value=5,
        step=1,
        format="%d",
        value=int(row["my_rating"]) if pd.notna(row.get("my_rating")) else None,
        key=f"rate_{place}_{cid}",
    )
    stages = list(user_data.STAGES)
    cur_stage = row.get("my_stage", user_data.DEFAULT_STAGE)
    stage = c3.selectbox(
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
                    "my_rating": rating,
                    "watchlist": bool(fav),
                    "my_stage": stage,
                    "my_tags": tags,
                    "my_notes": notes,
                },
            )
            st.cache_data.clear()
            st.success("Сохранено.")
        except Exception as exc:
            st.error(f"Не удалось сохранить: {exc}")


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

    fav_total = int(all_df.get("watchlist", pd.Series(dtype=bool)).sum())
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Компаний", len(filtered))
    c2.metric(
        "⭐ В избранном",
        int(filtered.get("watchlist", pd.Series(dtype=bool)).sum()),
        help=f"Всего в избранном (без фильтров): {fav_total}",
    )
    c3.metric("Средний score", f"{filtered['score'].mean():.0f}" if len(filtered) else "—")
    c4.metric("Индустрий", filtered["industry"].nunique())
    invested = int((filtered.get("my_stage", pd.Series(dtype=str)) == "Invested").sum())
    c5.metric("Проинвестировано", invested)

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
    st.caption("Кликни по строке — откроется карточка компании.")
    n = st.slider("Сколько показать", 5, 50, 10, key="topn")
    top_df = filtered.sort_values("score", ascending=False).head(n).reset_index(drop=True)
    selectable_table(
        top_df,
        ["name", "industry", "subindustry", "status", "score", "team_size", "one_liner"],
        key="table_top",
    )
    detail_card(filtered, place="overview")


def tab_companies(filtered: pd.DataFrame) -> None:
    st.caption("Кликни по строке таблицы — откроется карточка компании.")

    names = filtered["name"].tolist()
    picked = st.selectbox(
        "🔎 Открыть компанию по названию",
        ["—"] + names,
        index=0,
        key="company_picker",
    )
    if picked and picked != "—":
        row = filtered[filtered["name"] == picked]
        if not row.empty and int(row.iloc[0]["id"]) != selected_id():
            select_company(int(row.iloc[0]["id"]))
            st.rerun()

    selectable_table(
        filtered.reset_index(drop=True),
        [
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
        ],
        key="table_all",
    )
    detail_card(filtered, place="companies")

    with st.expander("⬇️ Экспорт отфильтрованного"):
        export_controls(filtered, key="companies")

    st.divider()
    st.subheader("Карточки компаний")

    c1, c2 = st.columns([2, 1])
    sort_label = c1.selectbox("Сортировка", list(SORT_OPTIONS), key="card_sort")
    sort_col, ascending = SORT_OPTIONS[sort_label]
    ranked = filtered.sort_values(sort_col, ascending=ascending, na_position="last")

    pages = max(1, -(-len(ranked) // PAGE_SIZE))
    page = c2.number_input(
        f"Страница (всего {pages})", min_value=1, max_value=pages, value=1, step=1, key="card_page"
    )
    start = (int(page) - 1) * PAGE_SIZE
    chunk = ranked.iloc[start : start + PAGE_SIZE]
    st.caption(f"Компании {start + 1}–{min(start + PAGE_SIZE, len(ranked))} из {len(ranked)}")

    for _, row in chunk.iterrows():
        sub = f" / {row['subindustry']}" if str(row.get("subindustry", "")).strip() else ""
        star = "⭐ " if bool(row.get("watchlist")) else ""
        with st.expander(
            f"{star}{row['name']} — {row.get('one_liner', '')}  (score {row.get('score', '')})"
        ):
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
            if st.button("📝 Открыть карточку и заметки", key=f"open_{int(row['id'])}"):
                select_company(int(row["id"]))
                st.rerun()


def tab_compare(filtered: pd.DataFrame) -> None:
    st.subheader("⚖️ Сравнение компаний")
    st.caption("Выбери до 5 компаний — сравнение колонками бок о бок.")
    names = st.multiselect(
        "Компании", filtered["name"].tolist(), max_selections=5, key="compare_pick"
    )
    if not names:
        st.info("Выбери компании выше.")
        return
    rows = filtered[filtered["name"].isin(names)]
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
    comp = rows.set_index("name")[fields].T
    comp = comp.map(_clean_cell)
    st.dataframe(comp, width="stretch")


def tab_notes(filtered: pd.DataFrame) -> None:
    st.subheader("📝 Заметки, теги и воронка")
    owner = is_owner()

    if owner:
        where = (
            "Google Sheets ✅"
            if use_gsheets()
            else "локальный CSV ⚠️ (не переживёт перезапуск на хостинге)"
        )
        st.caption(
            f"Массовое редактирование. Хранилище: **{where}**. Ключ — id "
            "(переживает переименования). Для одной компании удобнее её карточка."
        )
    else:
        st.info(
            "👀 **Режим просмотра.** Можешь править таблицу для себя, но изменения "
            "**временные**: они не влияют на заметки владельца и исчезнут после "
            "обновления страницы. Сохранять может только владелец.",
            icon="👀",
        )

    editor_cols = [
        c
        for c in ["id", "name", "my_rating", "watchlist", "my_stage", "my_tags", "my_notes"]
        if c in filtered.columns
    ]
    edited = st.data_editor(
        filtered[editor_cols].copy(),
        width="stretch",
        hide_index=True,
        disabled=["id", "name"],
        column_config={
            "my_rating": st.column_config.NumberColumn("Рейтинг", min_value=0, max_value=5),
            "watchlist": st.column_config.CheckboxColumn("⭐ Избранное"),
            "my_stage": st.column_config.SelectboxColumn("Стадия", options=list(user_data.STAGES)),
            "my_tags": st.column_config.TextColumn("Теги (через запятую)"),
            "my_notes": st.column_config.TextColumn("Заметки", width="large"),
        },
        key="annotations_editor",
    )

    if not owner:
        with st.expander("⬇️ Скачать мои временные правки"):
            export_controls(edited, key="visitor_notes")
        return

    if st.button("💾 Сохранить заметки", type="primary"):
        store = user_data._ensure_columns(load_annotations()).set_index("id")
        for _, r in edited.iterrows():
            store.loc[int(r["id"])] = {
                "my_rating": r.get("my_rating"),
                "watchlist": bool(r.get("watchlist")),
                "my_stage": r.get("my_stage", user_data.DEFAULT_STAGE),
                "my_tags": r.get("my_tags", ""),
                "my_notes": r.get("my_notes", ""),
            }
        try:
            save_annotations(store.reset_index())
            st.success(f"Сохранено для {len(edited)} компаний.")
            st.cache_data.clear()
        except Exception as exc:
            st.error(f"Не удалось сохранить: {exc}")


# --------------------------------------------------------------------------- main
def main() -> None:
    st.set_page_config(page_title="YC Scouter", page_icon="🛰️", layout="wide")
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

    df = load_data(str(path), path.stat().st_mtime)
    df = user_data.merge_annotations(df, load_annotations())

    if err := st.session_state.pop("gsheets_error", None):
        st.error(
            f"Не удалось прочитать Google Sheets — заметки временно недоступны. {err}",
            icon="⚠️",
        )
    elif is_owner() and not use_gsheets():
        st.info(
            "ℹ️ Заметки сейчас пишутся в локальный файл. На Streamlit Cloud подключи "
            "Google Sheets (см. docs/DEPLOY.md), иначе правки не переживут перезапуск.",
            icon="💾",
        )
    if _owner_key() and is_owner():
        st.sidebar.success("🔓 Режим владельца — можно сохранять.")

    filtered = sidebar_filters(df)

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


if __name__ == "__main__":
    main()
