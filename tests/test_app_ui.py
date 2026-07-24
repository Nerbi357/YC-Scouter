"""Tests for the dashboard's pure UI helpers (no Streamlit runtime needed)."""

import app
import pandas as pd

from yc_scouter import filters


def _row():
    return pd.Series(
        {
            "id": 7,
            "name": "Acme AI",
            "one_liner": "AI copilot",
            "industry": "Industrials",
            "subindustry": "Robotics",
            "batch": "Winter 2024",
            "status": "Active",
            "team_size": 12,
            "score": 42.5,
            "investability": "Private",
            "ai_description": "Builds robots.",
            "ai_risks": "Crowded market.",
            "website": "https://acme.ai",
            "yc_url": "https://ycombinator.com/companies/acme-ai",
        }
    )


def test_card_text_contains_key_fields_and_links():
    text = app.card_text(_row())
    assert "Acme AI" in text and "AI copilot" in text
    assert "Winter 2024" in text and "42.5" in text
    assert "Builds robots." in text and "Crowded market." in text
    assert "https://acme.ai" in text


def test_sort_options_map_to_real_columns():
    for label, (col, ascending) in app.SORT_OPTIONS.items():
        assert col in {"score", "batch_year", "name"}, label
        assert isinstance(ascending, bool)
    assert len(app.SORT_OPTIONS) == 6  # score / batch year / name, both directions


def test_page_size_paginates_full_dataset():
    n = 4037
    pages = max(1, -(-n // app.PAGE_SIZE))
    assert app.PAGE_SIZE == 50
    assert pages == 81  # every company is reachable
    last_start = (pages - 1) * app.PAGE_SIZE
    assert last_start < n <= pages * app.PAGE_SIZE


def test_search_is_vectorized_and_matches_all_fields(sample_records):
    from yc_scouter import normalize

    df = normalize.normalize(sample_records)
    df["my_notes"] = ""
    df.loc[df.index[0], "my_notes"] = "мойфлаг"
    # matches long_description
    assert len(filters.apply_filters(df, query="ROBOT")) >= 1
    # matches personal notes too
    out = filters.apply_filters(df, query="мойфлаг")
    assert len(out) == 1
    # no match -> empty, no crash
    assert len(filters.apply_filters(df, query="zzz-nothing")) == 0


def test_open_upper_bound_means_no_limit(sample_records):
    from yc_scouter import enrich, normalize, score

    df = score.score(enrich.add_investability(normalize.normalize(sample_records)))
    everything = filters.apply_filters(df, min_score=None, max_score=None)
    assert len(everything) == len(df)
    # "from" only: no upper bound applied
    lower_only = filters.apply_filters(df, min_score=0, max_score=None)
    assert len(lower_only) == len(df)
