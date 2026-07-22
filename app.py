"""Streamlit dashboard for browsing the YC Startup Radar dataset.

Reads the Parquet snapshot produced by the notebook — it never re-fetches. Run:

    streamlit run app.py

If the dataset doesn't exist yet, it tells you to run the notebook first.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from yc_radar import filters, user_data

# Paths are overridable so the dashboard can read from Google Drive (Colab).
DATASET = Path(os.environ.get("YC_RADAR_DATASET", "data/processed/yc_radar.parquet"))
USER_DATA = Path(os.environ.get("YC_RADAR_USERDATA", "data/user_data.csv"))

LINK_COLUMNS = [
    "website",
    "yc_url",
    "news_url",
    "producthunt_url",
    "hn_url",
    "github_url",
    "wikipedia_url",
]


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


def main() -> None:
    st.set_page_config(page_title="YC Startup Radar", page_icon="🛰️", layout="wide")
    st.title("🛰️ YC Startup Radar — 2024–2026")

    if not DATASET.exists():
        st.warning(
            "No dataset found yet. Run the notebook `notebooks/yc_radar.ipynb` "
            "first to generate `data/processed/yc_radar.parquet`."
        )
        st.stop()

    df = load_data(str(DATASET))
    df = user_data.merge_user_data(df, path=USER_DATA)

    # --- Sidebar filters ---
    st.sidebar.header("Filters")
    query = st.sidebar.text_input("Search (name / idea / tags)")
    industries = st.sidebar.multiselect("Industry", sorted(df["industry"].dropna().unique()))
    statuses = st.sidebar.multiselect("Status", sorted(df["status"].dropna().unique()))
    years = st.sidebar.multiselect(
        "Batch year", sorted(int(y) for y in df["batch_year"].dropna().unique())
    )
    min_score = st.sidebar.slider("Minimum score", 0, 100, 0)
    max_team = int(df["team_size"].fillna(0).max() or 0)
    min_team = st.sidebar.slider("Minimum team size", 0, max_team, 0) if max_team else 0

    filtered = filters.apply_filters(
        df,
        industries=industries or None,
        statuses=statuses or None,
        batch_years=years or None,
        min_team_size=min_team or None,
        min_score=min_score or None,
        query=query or None,
    ).sort_values("score", ascending=False)

    st.caption(f"Showing **{len(filtered)}** of {len(df)} companies")

    # --- Table ---
    table_cols = [
        "name",
        "batch",
        "industry",
        "status",
        "investability",
        "team_size",
        "score",
        "one_liner",
        "website",
        "yc_url",
    ]
    table_cols = [c for c in table_cols if c in filtered.columns]
    col_config = {
        c: st.column_config.LinkColumn(c) for c in ("website", "yc_url") if c in filtered.columns
    }
    st.dataframe(
        filtered[table_cols],
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
    )

    # --- Company detail cards ---
    st.subheader("Company details")
    for _, row in filtered.head(50).iterrows():
        with st.expander(
            f"{row['name']} — {row.get('one_liner', '')}  (score {row.get('score', '')})"
        ):
            st.markdown(
                f"**Industry:** {row.get('industry', '')}  \n"
                f"**Batch:** {row.get('batch', '')}  \n"
                f"**Status:** {row.get('status', '')} — {row.get('investability', '')}  \n"
                f"**Team size:** {row.get('team_size', '')}"
            )
            if str(row.get("ai_summary", "")).strip():
                st.markdown(f"**AI summary:** {row['ai_summary']}")
            if str(row.get("ai_risk_notes", "")).strip():
                st.markdown(f"**Risks to check:** {row['ai_risk_notes']}")
            links = [
                f"[{c.replace('_url', '').replace('_', ' ').title() or 'Website'}]({row[c]})"
                for c in LINK_COLUMNS
                if c in row and str(row.get(c, "")).startswith("http")
            ]
            if links:
                st.markdown("**Open-source links:** " + " · ".join(links))

    # --- Personal annotations (persist across refreshes) ---
    st.subheader("My shortlist & notes")
    st.caption(
        "Edit rating (0–5), watchlist, and notes below, then Save. Stored in "
        "`data/user_data.csv` keyed by slug — survives data refreshes."
    )
    editor_cols = ["slug", "name", "my_rating", "watchlist", "my_notes"]
    editor_df = filtered[[c for c in editor_cols if c in filtered.columns]].copy()
    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        disabled=["slug", "name"],
        column_config={
            "my_rating": st.column_config.NumberColumn("Rating", min_value=0, max_value=5),
            "watchlist": st.column_config.CheckboxColumn("Watchlist"),
            "my_notes": st.column_config.TextColumn("Notes"),
        },
        key="annotations_editor",
    )
    if st.button("💾 Save annotations"):
        existing = user_data.load_user_data(USER_DATA).set_index("slug")
        for _, r in edited.iterrows():
            existing.loc[r["slug"]] = {
                "my_rating": r.get("my_rating"),
                "watchlist": bool(r.get("watchlist")),
                "my_notes": r.get("my_notes", ""),
            }
        user_data.save_user_data(existing.reset_index(), path=USER_DATA)
        st.success(f"Saved annotations for {len(edited)} companies.")


if __name__ == "__main__":
    main()
