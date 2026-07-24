"""YC Scouter — interactive Streamlit dashboard (Russian UI).

Reads the newest dated Parquet produced by the pipeline (it never re-fetches) and
lets you filter, chart, compare, and annotate companies.

Storage for your personal notes/tags/stage is chosen automatically:

* **Google Sheets** when configured in Streamlit secrets (survives restarts —
  required for hosting on Streamlit Community Cloud, whose disk is ephemeral);
* a local **CSV** otherwise (Colab / local use).

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
    if use_gsheets():
        return gsheets.load(_secrets())
    return user_data.load_user_data(USER_DATA_CSV)


def save_annotations(df: pd.DataFrame) -> None:
    if use_gsheets():
        gsheets.save(_secrets(), df)
    else:
        user_data.save_user_data(df, path=USER_DATA_CSV)


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


# ------------------------------------------------------------------------ sidebar
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

    score_lo, score_hi = st.sidebar.slider("Score", 0, 100, (0, 100))

    max_team = int(df["team_size"].fillna(0).max() or 0)
    if max_team:
        team_lo, team_hi = st.sidebar.slider("Размер команды", 0, max_team, (0, max_team))
    else:
        team_lo, team_hi = 0, None

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
        min_team_size=team_lo or None,
        max_team_size=team_hi,
        min_score=score_lo or None,
        max_score=score_hi if score_hi < 100 else None,
        query=query or None,
    )


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
    st.plotly_chart(fig, use_container_width=True)


def _pie(df: pd.DataFrame, col: str, title: str) -> None:
    counts = df[col].dropna().value_counts()
    if counts.empty:
        return
    fig = px.pie(names=counts.index.astype(str), values=counts.values, title=title, hole=0.45)
    st.plotly_chart(fig, use_container_width=True)


def tab_overview(filtered: pd.DataFrame, total: int) -> None:
    st.caption(f"Показано **{len(filtered)}** из {total} компаний")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Компаний", len(filtered))
    c2.metric("⭐ В избранном", int(filtered.get("watchlist", pd.Series(dtype=bool)).sum()))
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
                st.plotly_chart(fig, use_container_width=True)
        with r2c2:
            fig = px.histogram(filtered, x="score", nbins=20, title="Распределение score")
            fig.update_traces(marker_color="#7C5CFC")
            st.plotly_chart(fig, use_container_width=True)

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            _pie(filtered, "status", "Разбивка по статусам (YC)")
        with r3c2:
            if "my_stage" in filtered.columns:
                _bar_count(filtered, "my_stage", "Моя воронка (стадии)", order=user_data.STAGES)

    st.divider()
    st.subheader("🏆 Топ по score")
    n = st.slider("Сколько показать", 5, 50, 10, key="topn")
    lead_cols = [
        c
        for c in ["name", "industry", "subindustry", "status", "score", "team_size", "one_liner"]
        if c in filtered.columns
    ]
    st.dataframe(
        filtered.sort_values("score", ascending=False).head(n)[lead_cols],
        use_container_width=True,
        hide_index=True,
    )


def tab_companies(filtered: pd.DataFrame) -> None:
    ranked = filtered.sort_values("score", ascending=False)

    d1, d2, _ = st.columns([1, 1, 4])
    d1.download_button(
        "⬇️ CSV",
        _to_csv_bytes(ranked),
        "yc_scouter_filtered.csv",
        "text/csv",
        use_container_width=True,
    )
    d2.download_button(
        "⬇️ Excel",
        _to_excel_bytes(ranked),
        "yc_scouter_filtered.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    table_cols = [
        c
        for c in [
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
        if c in ranked.columns
    ]
    col_config = {
        c: st.column_config.LinkColumn(c) for c in ("website", "yc_url") if c in ranked.columns
    }
    st.dataframe(
        ranked[table_cols], use_container_width=True, hide_index=True, column_config=col_config
    )

    st.subheader("Карточки компаний")
    for _, row in ranked.head(50).iterrows():
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
    st.dataframe(comp, use_container_width=True)


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
            f"Правь rating (0–5), избранное, стадию, теги и заметки — потом «Сохранить». "
            f"Хранилище: **{where}**. Ключ — id (переживает переименования)."
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
        use_container_width=True,
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
        # Visitors get a live, in-session copy they can download — never persisted.
        st.download_button(
            "⬇️ Скачать мои правки (CSV, только у меня)",
            _to_csv_bytes(edited),
            "my_temp_notes.csv",
            "text/csv",
        )
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
        save_annotations(store.reset_index())
        st.success(f"Сохранено для {len(edited)} компаний.")
        st.cache_data.clear()


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

    if is_owner() and not use_gsheets():
        st.info(
            "ℹ️ Заметки сейчас пишутся в локальный файл. На Streamlit Cloud подключи "
            "Google Sheets (см. HOSTING.md), иначе правки не переживут перезапуск.",
            icon="💾",
        )
    if _owner_key() and is_owner():
        st.sidebar.success("🔓 Режим владельца — можно сохранять.")

    df = load_data(str(path), path.stat().st_mtime)
    df = user_data.merge_annotations(df, load_annotations())

    filtered = sidebar_filters(df)

    overview, companies, compare, notes = st.tabs(
        ["📊 Обзор", "🔎 Компании", "⚖️ Сравнение", "📝 Заметки"]
    )
    with overview:
        tab_overview(filtered, total=len(df))
    with companies:
        tab_companies(filtered)
    with compare:
        tab_compare(filtered)
    with notes:
        tab_notes(filtered)


if __name__ == "__main__":
    main()
