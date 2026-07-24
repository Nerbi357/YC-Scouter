"""AI enrichment (File 2): a rich description + short risks per company.

Two factual outputs via **Claude** (default) or **Groq**:
- ``ai_description`` — 6-7 sentences (idea, uniqueness, strengths, useful facts),
- ``ai_risks`` — 1-2 short concrete risks.

The one-liner is NOT AI-generated (YC's own ``one_liner`` is used). Nothing
speculative (funding/traction/valuation) is requested — factual only.

Cache is keyed on ``(id, model_id, prompt_version)`` so switching model/prompt is
an explicit, logged re-summarization and old results are never overwritten. The
summarizers are **generators** yielding ``(id, result)``; :func:`add_ai_summaries`
owns the cache and persistence, so a long run is resumable and only NEW keys are
summarized. Tests inject a summarizer, so nothing hits the network.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable, Iterable
from pathlib import Path

import pandas as pd

from . import config

AI_DISABLED = "AI summary disabled (set ANTHROPIC_API_KEY / GROQ_API_KEY to enable)"
MAX_DESC_CHARS = config.MAX_DESC_CHARS
DEFAULT_CACHE_PATH = config.CACHE_DIR / "ai_cache.json"

SYSTEM_PROMPT = (
    "You are a venture analyst. Using ONLY the facts provided about a startup, write "
    "an information-dense brief for an investor. Return a single JSON object with two "
    "string fields:\n"
    '  "description": 6-7 sentences — what the company does, the core idea, what is '
    "uniquely differentiated, notable strengths, and any useful factual detail present "
    "in the input.\n"
    '  "risks": 1-2 short, concrete risks to check before investing.\n'
    "Base everything strictly on the provided text. Do NOT invent facts, numbers, "
    "funding, valuations, traction, or metrics. Return only the JSON object."
)

PROMPT_TEMPLATE = (
    "Company: {name}\n"
    "One-liner: {one_liner}\n"
    "Industry: {industry} / {subindustry}\n"
    "Tags: {tags}\n"
    "Status: {status} | Team size: {team_size} | Batch: {batch} | Stage: {stage}\n"
    "Description: {description}"
)

#: Fingerprint of the current prompt — part of the cache key.
PROMPT_VERSION = config.prompt_version(SYSTEM_PROMPT, PROMPT_TEMPLATE)

#: ``summarizer(records)`` yields ``(id, {"ai_description":..., "ai_risks":...})``.
Summarizer = Callable[[list[dict]], Iterable[tuple[int, dict[str, str]]]]

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


# ------------------------------------------------------------------------- cache
def _load_cache(path: Path) -> dict:
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else {}


def _save_cache(path: Path, cache: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False))
    tmp.replace(path)  # atomic


def _ckey(company_id: int, model: str, prompt_version: str) -> str:
    return f"{company_id}::{model}::{prompt_version}"


# --------------------------------------------------------------------- prompting
def _fields(rec: dict) -> dict:
    tags = rec.get("tags")
    if hasattr(tags, "tolist"):  # numpy array (from parquet)
        tags = tags.tolist()
    if isinstance(tags, (list, tuple)):
        tags = ", ".join(map(str, tags))
    elif tags is None or (isinstance(tags, float) and pd.isna(tags)):
        tags = ""
    return {
        "name": rec.get("name", ""),
        "one_liner": rec.get("one_liner", ""),
        "industry": rec.get("industry", ""),
        "subindustry": rec.get("subindustry", ""),
        "tags": tags,
        "status": rec.get("status", ""),
        "team_size": rec.get("team_size", ""),
        "batch": rec.get("batch", ""),
        "stage": rec.get("stage", ""),
        "description": str(rec.get("long_description", ""))[:MAX_DESC_CHARS],
    }


def _user_prompt(rec: dict) -> str:
    return PROMPT_TEMPLATE.format(**_fields(rec))


def _parse(text: str) -> dict[str, str]:
    m = _JSON_RE.search(text or "")
    data = json.loads(m.group(0)) if m else {}
    return {
        "ai_description": str(data.get("description", "")).strip(),
        "ai_risks": str(data.get("risks", "")).strip(),
    }


def _records_for(df: pd.DataFrame, ids: list[int]) -> list[dict]:
    cols = [
        "id",
        "name",
        "one_liner",
        "long_description",
        "industry",
        "subindustry",
        "tags",
        "status",
        "team_size",
        "batch",
        "stage",
    ]
    sub = df[df["id"].isin(ids)]
    return sub[[c for c in cols if c in sub.columns]].to_dict("records")


# ----------------------------------------------------------------------- mock
def mock_summarizer(records: list[dict]):
    """Offline, deterministic summarizer — NO API call, NO spend.

    Produces readable placeholder text derived from the input fields, useful for
    demos, the notebook smoke test, and previewing layout without a key.
    """
    for rec in records:
        f = _fields(rec)
        desc = (
            f"{f['name']} operates in {f['industry']} ({f['subindustry']}). "
            f"Core idea: {f['one_liner']}. {str(f['description'])[:180]} "
            f"Team of {f['team_size']}, batch {f['batch']}, status {f['status']}. "
            "[MOCK — generated offline, no API call]."
        )
        risks = f"Competition within {f['industry']}; execution and go-to-market risk. [MOCK]"
        yield int(rec["id"]), {"ai_description": desc, "ai_risks": risks}


# ------------------------------------------------------------------- providers
def _claude_one(client, model, rec, *, max_tokens, max_retries):
    last: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _user_prompt(rec)}],
            )
            text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
            usage = getattr(resp, "usage", None)
            tin = getattr(usage, "input_tokens", 0) or 0
            tout = getattr(usage, "output_tokens", 0) or 0
            return _parse(text), (tin, tout)
        except Exception as exc:  # rate limit / overload / bad JSON -> retry
            last = exc
            time.sleep(min(2**attempt, 30))
    return {"ai_description": f"(Claude failed: {last})", "ai_risks": ""}, (0, 0)


def make_claude_summarizer(
    api_key: str | None = None,
    *,
    model: str = config.CLAUDE_MODEL,
    max_tokens: int = config.MAX_TOKENS,
    max_retries: int = 5,
    progress_every: int = 50,
    client: object | None = None,
) -> Summarizer:
    """Synchronous **Claude** summarizer (default provider). Prints a running cost
    estimate from real token usage; never auto-halts."""
    if client is None:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def summarizer(records: list[dict]):
        spent, total = 0.0, len(records)
        for i, rec in enumerate(records, 1):
            res, (tin, tout) = _claude_one(
                client, model, rec, max_tokens=max_tokens, max_retries=max_retries
            )
            spent += config.estimate_cost(tin, tout, model)
            if progress_every and (i % progress_every == 0 or i == total):
                print(f"  AI: {i}/{total} companies — est. ${spent:.2f}", flush=True)
            yield int(rec["id"]), res

    return summarizer


def _groq_one(client, model, rec, *, max_retries):
    last: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _user_prompt(rec)},
                ],
                response_format={"type": "json_object"},
                max_tokens=config.MAX_TOKENS,
                temperature=0,
            )
            text = resp.choices[0].message.content
            usage = getattr(resp, "usage", None)
            tin = getattr(usage, "prompt_tokens", 0) or 0
            tout = getattr(usage, "completion_tokens", 0) or 0
            return _parse(text), (tin, tout)
        except Exception as exc:
            last = exc
            time.sleep(min(2**attempt, 30))
    return {"ai_description": f"(Groq failed: {last})", "ai_risks": ""}, (0, 0)


def make_groq_summarizer(
    api_key: str | None = None,
    *,
    model: str = config.GROQ_MODEL,
    max_retries: int = 5,
    sleep: float = 0.0,
    progress_every: int = 50,
    client: object | None = None,
) -> Summarizer:
    """Free-tier **Groq** summarizer (optional provider). Same generator contract."""
    if client is None:
        from groq import Groq

        client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    def summarizer(records: list[dict]):
        spent, total = 0.0, len(records)
        for i, rec in enumerate(records, 1):
            res, (tin, tout) = _groq_one(client, model, rec, max_retries=max_retries)
            spent += config.estimate_cost(tin, tout, model)
            if progress_every and (i % progress_every == 0 or i == total):
                print(f"  AI (groq): {i}/{total} — est. ${spent:.4f}", flush=True)
            if sleep:
                time.sleep(sleep)
            yield int(rec["id"]), res

    return summarizer


# ------------------------------------------------------------------- top-level
def add_ai_summaries(
    df: pd.DataFrame,
    *,
    cache_path: Path = DEFAULT_CACHE_PATH,
    model: str = config.CLAUDE_MODEL,
    prompt_version: str = PROMPT_VERSION,
    summarizer: Summarizer | None = None,
    save_every: int = 25,
    limit: int | None = None,
) -> pd.DataFrame:
    """Attach ``ai_description``, ``ai_risks``, ``ai_model``, ``ai_prompt_version``.

    Only companies missing the current ``(id, model, prompt_version)`` key are
    summarized; results persist incrementally (resumable). With no summarizer the
    columns show :data:`AI_DISABLED` and no call is made. Old keys are preserved.
    ``limit`` caps how many missing companies are summarized in this call (a cheap
    real smoke test, or chunked runs) — the rest stay for the next run.
    """
    cache = _load_cache(cache_path)
    ids = [int(i) for i in df["id"].tolist()]

    def ck(i: int) -> str:
        return _ckey(i, model, prompt_version)

    missing = [i for i in ids if ck(i) not in cache]
    if limit is not None:
        missing = missing[:limit]
    if missing and summarizer is not None:
        n = 0
        for cid, res in summarizer(_records_for(df, missing)):
            cache[ck(cid)] = {
                "id": cid,
                "model_id": model,
                "prompt_version": prompt_version,
                "ai_description": res.get("ai_description", ""),
                "ai_risks": res.get("ai_risks", ""),
            }
            n += 1
            if cache_path and save_every and n % save_every == 0:
                _save_cache(cache_path, cache)
        if cache_path:
            _save_cache(cache_path, cache)

    out = df.copy()
    out["ai_description"] = [cache.get(ck(i), {}).get("ai_description", AI_DISABLED) for i in ids]
    out["ai_risks"] = [cache.get(ck(i), {}).get("ai_risks", AI_DISABLED) for i in ids]
    out["ai_model"] = [cache[ck(i)]["model_id"] if ck(i) in cache else "" for i in ids]
    out["ai_prompt_version"] = [
        cache[ck(i)]["prompt_version"] if ck(i) in cache else "" for i in ids
    ]
    return out
