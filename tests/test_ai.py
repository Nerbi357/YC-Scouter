"""Tests for AI summaries. No real API calls — the summarizer is injected/mocked."""

import json
from types import SimpleNamespace

import pandas as pd

from yc_scouter import ai, config

MODEL = config.CLAUDE_MODEL
PV = ai.PROMPT_VERSION


def _df():
    return pd.DataFrame(
        [
            {"id": 1, "name": "A", "one_liner": "x", "long_description": "desc a", "tags": ["ai"]},
            {"id": 2, "name": "B", "one_liner": "y", "long_description": "desc b", "tags": []},
        ]
    )


def _ck(i):
    return f"{i}::{MODEL}::{PV}"


def _mock_summarizer(records):
    for r in records:
        yield int(r["id"]), {"ai_description": f"desc-{r['id']}", "ai_risks": f"risk-{r['id']}"}


def test_runs_for_missing_only_and_writes_cache(tmp_path):
    cache = tmp_path / "ai_cache.json"
    cache.write_text(
        json.dumps(
            {
                _ck(1): {
                    "id": 1,
                    "model_id": MODEL,
                    "prompt_version": PV,
                    "ai_description": "cached-1",
                    "ai_risks": "r1",
                }
            }
        )
    )
    seen = {}

    def summ(records):
        seen["ids"] = [r["id"] for r in records]
        yield from _mock_summarizer(records)

    out = ai.add_ai_summaries(_df(), cache_path=cache, summarizer=summ)

    assert seen["ids"] == [2]  # only the uncached company
    d = out.set_index("id")["ai_description"].to_dict()
    assert d[1] == "cached-1" and d[2] == "desc-2"
    assert out.set_index("id")["ai_model"].to_dict()[2] == MODEL
    assert out.set_index("id")["ai_prompt_version"].to_dict()[2] == PV
    # both persisted under composite keys
    persisted = json.loads(cache.read_text())
    assert set(persisted) == {_ck(1), _ck(2)}


def test_full_cache_hit_skips_summarizer(tmp_path):
    cache = tmp_path / "ai_cache.json"
    cache.write_text(
        json.dumps(
            {
                _ck(1): {
                    "id": 1,
                    "model_id": MODEL,
                    "prompt_version": PV,
                    "ai_description": "d1",
                    "ai_risks": "r1",
                },
                _ck(2): {
                    "id": 2,
                    "model_id": MODEL,
                    "prompt_version": PV,
                    "ai_description": "d2",
                    "ai_risks": "r2",
                },
            }
        )
    )

    def boom(records):
        raise AssertionError("must not summarize on full cache hit")

    out = ai.add_ai_summaries(_df(), cache_path=cache, summarizer=boom)
    assert out.set_index("id")["ai_description"].to_dict() == {1: "d1", 2: "d2"}


def test_no_summarizer_yields_placeholder(tmp_path):
    out = ai.add_ai_summaries(_df(), cache_path=tmp_path / "c.json", summarizer=None)
    assert (out["ai_description"] == ai.AI_DISABLED).all()
    assert (out["ai_risks"] == ai.AI_DISABLED).all()
    assert (out["ai_model"] == "").all()


def test_prompt_version_change_resummarizes_and_preserves_old(tmp_path):
    cache = tmp_path / "ai_cache.json"
    # first run under PV
    ai.add_ai_summaries(_df(), cache_path=cache, summarizer=_mock_summarizer)
    # second run under a DIFFERENT prompt version
    new_pv = "deadbeef1234"
    called = {}

    def summ(records):
        called["ids"] = [r["id"] for r in records]
        for r in records:
            yield int(r["id"]), {"ai_description": "new", "ai_risks": "new"}

    out = ai.add_ai_summaries(_df(), cache_path=cache, prompt_version=new_pv, summarizer=summ)
    assert called["ids"] == [1, 2]  # all re-summarized under the new version
    assert (out["ai_description"] == "new").all()
    # old-version entries are still in the cache (never overwritten)
    persisted = json.loads(cache.read_text())
    assert _ck(1) in persisted and f"1::{MODEL}::{new_pv}" in persisted


def test_claude_summarizer_parses_and_counts_cost(capsys):
    def fake_create(**kw):
        payload = json.dumps({"description": "does X, unique Y", "risks": "check Z"})
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=payload)],
            usage=SimpleNamespace(input_tokens=800, output_tokens=250),
        )

    client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    summ = ai.make_claude_summarizer(client=client, progress_every=1)
    results = list(summ([{"id": 7, "name": "A", "one_liner": "o", "long_description": "d"}]))

    assert results == [(7, {"ai_description": "does X, unique Y", "ai_risks": "check Z"})]
    # cost line printed (est. from usage: 800*$1/1M + 250*$5/1M ≈ $0.002)
    assert "est. $" in capsys.readouterr().out


def test_claude_summarizer_truncates_long_description():
    seen = {}

    def fake_create(**kw):
        seen["prompt"] = kw["messages"][0]["content"]
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text=json.dumps({"description": "s", "risks": "r"}))
            ],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )

    client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    summ = ai.make_claude_summarizer(client=client, progress_every=0)
    list(summ([{"id": 1, "name": "A", "one_liner": "o", "long_description": "x" * 5000}]))
    assert ("x" * ai.MAX_DESC_CHARS) in seen["prompt"]
    assert ("x" * (ai.MAX_DESC_CHARS + 1)) not in seen["prompt"]


def test_groq_summarizer_parses(tmp_path):
    def fake_create(**kw):
        payload = json.dumps({"description": "G desc", "risks": "G risk"})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=payload))],
            usage=SimpleNamespace(prompt_tokens=700, completion_tokens=200),
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    summ = ai.make_groq_summarizer(client=client, progress_every=0, model=config.GROQ_MODEL)
    out = ai.add_ai_summaries(
        _df(), cache_path=tmp_path / "c.json", model=config.GROQ_MODEL, summarizer=summ
    )
    assert (out["ai_description"] == "G desc").all()


def test_provider_failure_yields_message():
    def boom(**kw):
        raise RuntimeError("rate limited")

    client = SimpleNamespace(messages=SimpleNamespace(create=boom))
    summ = ai.make_claude_summarizer(client=client, progress_every=0, max_retries=2)
    results = list(summ([{"id": 1, "name": "A", "one_liner": "", "long_description": ""}]))
    assert "failed" in results[0][1]["ai_description"].lower()
