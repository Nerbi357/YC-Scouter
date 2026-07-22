"""Headless pipeline runner for CI / server execution (GitHub Actions).

Runs the whole pipeline and writes data/processed/yc_radar.{xlsx,parquet,csv}.
Uses free Groq AI summaries when GROQ_API_KEY is set; otherwise fills a
placeholder (no error, no cost). Designed to run unattended — you can close your
computer and download the artifact later.
"""

from __future__ import annotations

import os
import sys

# make src/ importable whether or not the package was pip-installed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from yc_radar import ai, enrich, export, fetch, normalize, score, user_data  # noqa: E402


def main() -> int:
    print("Fetching YC companies…", flush=True)
    records = fetch.fetch_companies()
    df = normalize.normalize(records)
    print(f"  {len(df)} companies in batches 2024–2026", flush=True)

    df = enrich.add_investability(df)
    df = enrich.add_links(df)
    df = score.score(df)

    claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    cache = "data/processed/ai_cache.json"
    if claude_key:
        print("AI summaries: Claude Haiku 4.5 (paid, cheap)", flush=True)
        summarizer = ai.make_claude_summarizer(claude_key, cache_path=cache)
    elif groq_key:
        print("AI summaries: Groq (free) llama-3.1-8b-instant", flush=True)
        summarizer = ai.make_groq_summarizer(groq_key, cache_path=cache, sleep=1.0)
    else:
        print("AI summaries: disabled (no API key) — placeholder text", flush=True)
        summarizer = None

    df = ai.add_ai_summaries(df, summarizer=summarizer)
    df = user_data.merge_user_data(df)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    paths = export.export(df)
    print(f"Exported {len(df)} companies:", flush=True)
    for kind, path in paths.items():
        print(f"  {kind}: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
