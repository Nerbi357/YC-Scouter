# Implementation Plan — YC Scouter

Derived from `SPEC.md`. This is the **working-phase** build plan that lands the
**final-phase** target. Work is sliced **vertically** (each task leaves the repo in
a working, testable state) and grouped into phases with a human **checkpoint**
between them.

## What we reuse vs. change (from the existing `yc_radar`)

| Existing module | Action |
|---|---|
| `fetch.py` | **Reuse** (drop the mtime-cache reliance; File 1 re-scrapes each run). |
| `normalize.py` | **Change**: add `id`, dedupe by `id` + stable sort, years = 2020→current. |
| `enrich.py`, `score.py` | **Reuse** as-is (links keyed by slug are fine). |
| `export.py` | **Change**: dated filename builder `yc_dataset_<stage>_<YYYY-MM-DD>`. |
| `ai.py` | **Rewrite**: 2 outputs (`ai_description`+`ai_risks`), cache key `(id,model_id,prompt_version)`, provider switch, running cost print, no hard cap. |
| `filters.py` | **Reuse** (already extended). |
| `user_data.py`, `gsheets.py` | **Change**: key on `id` instead of `slug`. |
| `app.py` | **Change**: Russian UI, load newest dated file via glob, notes by `id`. |
| `notebooks/*` | **Replace** with `01_dataset_base.ipynb` + `02_ai_summary.ipynb` (thin). |
| package name | **Rename** `yc_radar` → `yc_scouter`. |
| `requirements.txt` | **Replace** with `requirements.in` (source) → compiled to a pinned + hashed `requirements.txt`. |
| `.github/workflows/` | **Replace** with `build-dataset.yml` + `build-ai-summary.yml` (manual). |
| `scripts/run_pipeline.py` | **Remove** (papermill runs the real notebook instead). |
| docs | **Add** `docs/HOW_IT_WORKS.md`, `AI_METHODOLOGY.md`, `HOW_TO_UPDATE.md`, `DEPLOY.md`. |

## Dependency graph

```
Phase 0 Foundation
  T0.1 rename yc_radar→yc_scouter ─┐
  T0.2 config.py (constants)       ├─→ everything downstream
  T0.3 lockfile + python + pyproject┘
        │
Phase 1 Data (File 1)                     Phase 2 AI (File 2)
  T1.1 normalize(id, 2020→now) ──┐          T2.1 ai.py rewrite (needs T0.2, T1.1)
  T1.2 export dated names        ├─→ T1.4    T2.2 02_ai_summary.ipynb (needs T2.1,T1.4)
  T1.3 fetch reuse/tidy          │  01 nb    T2.3 build-ai-summary.yml (needs T2.2)
  T1.4 01_dataset_base.ipynb ────┘
  T1.5 build-dataset.yml (needs T1.4)
        │
Phase 3 Dashboard                          Phase 4 Docs & final-phase cleanup
  T3.1 user_data/gsheets by id              T4.1 HOW_IT_WORKS + AI_METHODOLOGY
  T3.2 app.py Russian + glob latest         T4.2 HOW_TO_UPDATE + DEPLOY + README
  T3.3 notes migration slug→id              T4.3 prune stray files (final phase)
```

## Checkpoints (human review gates)

- **CP-0** after Phase 0: package renamed, tests green, env pinned.
- **CP-1** after Phase 1: File 1 builds a dated Base dataset (2020→now) locally.
- **CP-2** after Phase 2: File 2 adds `ai_description`+`ai_risks`, cost estimate
  prints, incremental cache works (mocked in tests; a small real smoke run is the
  user's call given spend).
- **CP-3** after Phase 3: dashboard runs on the newest dated file, Russian UI,
  notes keyed by `id` survive a rebuild.
- **CP-4** after Phase 4: only final-phase files remain; docs complete; public repo
  ready to host.

## Verification (every task)

`ruff check` + `black --check` + `pytest -q` stay green; network/LLM stay mocked in
tests (no spend). Each task commits atomically on the working branch.

## Notes on migration

- Existing committed `yc_radar.parquet` (2024–2026) is **superseded** by File 1's
  full re-scrape; kept only until the first new Base build.
- Old `ai_cache.json` (slug-keyed, old 2-field prompt) is **incompatible** with the
  new `(id, model_id, prompt_version)` cache → a fresh cache is started; existing
  companies are re-summarized once (in the ~$8.5 estimate).
- Existing personal notes (slug-keyed) → **migrated** to `id` via a slug→id map
  from a fresh dataset (T3.3), best-effort, so no notes are lost.

## Open risks tracked into build

- Confirm yc-oss `id` present & stable, and `license` permits committing snapshots
  (we don't commit raw snapshots now, so lower stakes) — verified during T1.1.
- Groq default is a config option only; Claude is the default (T2.1).
