"""Tests for AI summaries. No real API calls — summarizer is injected/mocked."""

import json

import pandas as pd

from yc_radar import ai


def _df():
    return pd.DataFrame(
        [
            {"slug": "a", "name": "A", "one_liner": "x", "long_description": "desc a"},
            {"slug": "b", "name": "B", "one_liner": "y", "long_description": "desc b"},
        ]
    )


def test_cache_hit_skips_summarizer(tmp_path):
    cache = tmp_path / "ai_cache.json"
    cache.write_text(
        json.dumps(
            {
                "a": {"ai_summary": "sa", "ai_risk_notes": "ra"},
                "b": {"ai_summary": "sb", "ai_risk_notes": "rb"},
            }
        )
    )

    def boom(records, model):
        raise AssertionError("summarizer must not be called on full cache hit")

    out = ai.add_ai_summaries(_df(), cache_path=cache, summarizer=boom)
    assert out.set_index("slug")["ai_summary"].to_dict() == {"a": "sa", "b": "sb"}


def test_no_key_no_cache_yields_placeholder(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cache = tmp_path / "ai_cache.json"
    out = ai.add_ai_summaries(_df(), cache_path=cache, summarizer=None, api_key=None)
    assert (out["ai_summary"] == ai.AI_DISABLED).all()
    assert (out["ai_risk_notes"] == ai.AI_DISABLED).all()


def test_summarizer_runs_for_missing_only_and_writes_cache(tmp_path):
    cache = tmp_path / "ai_cache.json"
    cache.write_text(json.dumps({"a": {"ai_summary": "sa", "ai_risk_notes": "ra"}}))
    seen = {}

    def fake(records, model):
        seen["slugs"] = [r["slug"] for r in records]
        return {r["slug"]: {"ai_summary": "new", "ai_risk_notes": "risk"} for r in records}

    out = ai.add_ai_summaries(_df(), cache_path=cache, summarizer=fake)

    assert seen["slugs"] == ["b"]  # only the uncached company
    assert out.set_index("slug")["ai_summary"].to_dict() == {"a": "sa", "b": "new"}
    # cache persisted with both
    persisted = json.loads(cache.read_text())
    assert set(persisted) == {"a", "b"}
