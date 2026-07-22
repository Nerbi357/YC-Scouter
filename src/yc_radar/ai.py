"""AI idea/uniqueness/risk summaries via Claude Haiku 4.5 (Batch API).

Design goals:
- **Cheap & re-runnable.** Per-company results are cached to disk; a refresh only
  summarizes companies not already in the cache.
- **Cost-controlled.** Uses the Batch API (−50%) and prompt-caches the shared
  instruction prefix.
- **Safe by default.** With no ``ANTHROPIC_API_KEY`` (and no injected summarizer),
  the AI columns are filled with a clear placeholder and **no API call is made**.

Tests inject a ``summarizer`` callable so nothing hits the network.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_CACHE_PATH = Path("data/processed/ai_cache.json")
AI_DISABLED = "AI summary disabled (set ANTHROPIC_API_KEY to enable)"

# Cost control: cap the description we send (input tokens are the bulk of cost).
MAX_DESC_CHARS = 600

_INSTRUCTION = (
    "You are a venture analyst. Given a startup's name and description, write a "
    "very concise summary for an investor scanning many companies. Return JSON with "
    "two fields: 'summary' (what they do + what makes them unique, ONE sentence) and "
    "'risks' (the top thing to check before investing, one short phrase). Do not "
    "invent facts or financials; base it only on the provided text."
)

_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}, "risks": {"type": "string"}},
    "required": ["summary", "risks"],
    "additionalProperties": False,
}

# summarizer(records, model) -> {slug: {"ai_summary": str, "ai_risk_notes": str}}
Summarizer = Callable[[list[dict], str], dict[str, dict[str, str]]]


def _load_cache(cache_path: Path) -> dict[str, dict[str, str]]:
    cache_path = Path(cache_path)
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    return {}


def _save_cache(cache_path: Path, cache: dict) -> None:
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False))
    tmp.replace(cache_path)  # atomic


def _records_for(df: pd.DataFrame, slugs: list[str]) -> list[dict]:
    sub = df[df["slug"].isin(slugs)]
    return [
        {
            "slug": r["slug"],
            "name": r.get("name", ""),
            "one_liner": r.get("one_liner", ""),
            "long_description": r.get("long_description", ""),
        }
        for _, r in sub.iterrows()
    ]


def _user_prompt(rec: dict) -> str:
    desc = str(rec.get("long_description", ""))[:MAX_DESC_CHARS]
    return f"Company: {rec['name']}\n" f"One-liner: {rec['one_liner']}\n" f"Description: {desc}"


def _batch_summarize(records: list[dict], model: str, api_key: str) -> dict[str, dict[str, str]]:
    """Real Batch-API summarizer (not exercised in tests)."""
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = anthropic.Anthropic(api_key=api_key)
    system = [{"type": "text", "text": _INSTRUCTION, "cache_control": {"type": "ephemeral"}}]
    requests = [
        Request(
            custom_id=rec["slug"],
            params=MessageCreateParamsNonStreaming(
                model=model,
                max_tokens=300,
                system=system,
                messages=[{"role": "user", "content": _user_prompt(rec)}],
                output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            ),
        )
        for rec in records
    ]

    batch = client.messages.batches.create(requests=requests)
    while client.messages.batches.retrieve(batch.id).processing_status != "ended":
        time.sleep(10)

    out: dict[str, dict[str, str]] = {}
    for res in client.messages.batches.results(batch.id):
        if res.result.type != "succeeded":
            continue
        text = next((b.text for b in res.result.message.content if b.type == "text"), "{}")
        data = json.loads(text)
        out[res.custom_id] = {
            "ai_summary": data.get("summary", ""),
            "ai_risk_notes": data.get("risks", ""),
        }
    return out


GROQ_DEFAULT_MODEL = "llama-3.1-8b-instant"


def _groq_one(client: object, model: str, rec: dict, *, max_retries: int = 5) -> dict[str, str]:
    """Summarize one company via a Groq (OpenAI-compatible) chat completion."""
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _INSTRUCTION},
                    {"role": "user", "content": _user_prompt(rec)},
                ],
                response_format={"type": "json_object"},
                max_tokens=400,
                temperature=0.3,
            )
            data = json.loads(resp.choices[0].message.content)
            return {
                "ai_summary": str(data.get("summary", "")).strip(),
                "ai_risk_notes": str(data.get("risks", "")).strip(),
            }
        except Exception as exc:  # rate limits, transient errors, bad JSON -> retry
            last_err = exc
            time.sleep(min(2**attempt, 30))
    return {"ai_summary": f"(Groq summary failed: {last_err})", "ai_risk_notes": ""}


def make_groq_summarizer(
    api_key: str | None = None,
    *,
    model: str = GROQ_DEFAULT_MODEL,
    cache_path: Path | None = None,
    sleep: float = 1.0,
    max_retries: int = 5,
    client: object | None = None,
) -> Summarizer:
    """Build a free-tier **Groq** summarizer to inject into :func:`add_ai_summaries`.

    No Claude key needed — get a free key at console.groq.com. Summarizes
    sequentially (Groq has no batch API), paces requests by ``sleep`` seconds,
    retries with backoff on rate limits, and — if ``cache_path`` is given —
    persists each result immediately so a long run is resumable.
    """
    if client is None:
        from groq import Groq  # lazy import so the dep is optional

        client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    def summarizer(records: list[dict], _model: str = "") -> dict[str, dict[str, str]]:
        persisted = _load_cache(cache_path) if cache_path else {}
        out: dict[str, dict[str, str]] = {}
        for rec in records:
            res = _groq_one(client, model, rec, max_retries=max_retries)
            out[rec["slug"]] = res
            if cache_path:
                persisted[rec["slug"]] = res
                _save_cache(cache_path, persisted)
            if sleep:
                time.sleep(sleep)
        return out

    return summarizer


def _claude_one(
    client: object, model: str, rec: dict, *, max_tokens: int, max_retries: int
) -> dict[str, str]:
    """Summarize one company with a synchronous Claude Messages call."""
    system = [{"type": "text", "text": _INSTRUCTION, "cache_control": {"type": "ephemeral"}}]
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": _user_prompt(rec)}],
                output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            )
            text = next((b.text for b in resp.content if b.type == "text"), "{}")
            data = json.loads(text)
            return {
                "ai_summary": str(data.get("summary", "")).strip(),
                "ai_risk_notes": str(data.get("risks", "")).strip(),
            }
        except Exception as exc:  # rate limit / overload / transient -> retry
            last_err = exc
            time.sleep(min(2**attempt, 30))
    return {"ai_summary": f"(Claude summary failed: {last_err})", "ai_risk_notes": ""}


def make_claude_summarizer(
    api_key: str | None = None,
    *,
    model: str = DEFAULT_MODEL,
    cache_path: Path | None = None,
    max_tokens: int = 300,
    sleep: float = 0.0,
    max_retries: int = 5,
    progress_every: int = 50,
    client: object | None = None,
) -> Summarizer:
    """Build a **synchronous Claude** summarizer (paid but cheap; Haiku 4.5).

    Cheap-by-default: short output, truncated input (:data:`MAX_DESC_CHARS`), and a
    resumable on-disk cache so re-runs never re-pay for done companies. Prints
    progress every ``progress_every`` companies. For the absolute lowest price use
    the Batch API instead (``add_ai_summaries(df, api_key=...)`` with no summarizer).
    """
    if client is None:
        import anthropic  # lazy import so the dep is optional

        client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def summarizer(records: list[dict], _model: str = "") -> dict[str, dict[str, str]]:
        persisted = _load_cache(cache_path) if cache_path else {}
        out: dict[str, dict[str, str]] = {}
        total = len(records)
        for i, rec in enumerate(records, 1):
            out[rec["slug"]] = _claude_one(
                client, model, rec, max_tokens=max_tokens, max_retries=max_retries
            )
            if cache_path:
                persisted[rec["slug"]] = out[rec["slug"]]
                _save_cache(cache_path, persisted)
            if progress_every and (i % progress_every == 0 or i == total):
                print(f"  AI summaries: {i}/{total} companies…", flush=True)
            if sleep:
                time.sleep(sleep)
        return out

    return summarizer


def add_ai_summaries(
    df: pd.DataFrame,
    *,
    cache_path: Path = DEFAULT_CACHE_PATH,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    summarizer: Summarizer | None = None,
) -> pd.DataFrame:
    """Add ``ai_summary`` and ``ai_risk_notes`` columns.

    Only companies missing from the on-disk cache are summarized. If no summarizer
    is injected and no API key is available, the columns are filled with
    :data:`AI_DISABLED` and no API call is made.
    """
    cache = _load_cache(cache_path)
    slugs = df["slug"].tolist()
    missing = [s for s in slugs if s not in cache]
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    if missing:
        if summarizer is not None:
            cache.update(summarizer(_records_for(df, missing), model))
            _save_cache(cache_path, cache)
        elif key:
            cache.update(_batch_summarize(_records_for(df, missing), model, key))
            _save_cache(cache_path, cache)
        # else: no way to summarize -> leave missing, placeholder fills below

    out = df.copy()
    out["ai_summary"] = [cache.get(s, {}).get("ai_summary", AI_DISABLED) for s in slugs]
    out["ai_risk_notes"] = [cache.get(s, {}).get("ai_risk_notes", AI_DISABLED) for s in slugs]
    return out
