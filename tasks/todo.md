# TODO — YC Scouter

Vertical tasks with acceptance criteria + verification. Sliced from `SPEC.md` /
`tasks/plan.md`. Check off as completed. `[V]` = how to verify.

---

## Phase 0 — Foundation  → CP-0

- [x] **T0.1 Rename package `yc_radar` → `yc_scouter`** ✅
  - Moved `src/yc_radar/` → `src/yc_scouter/`; updated all imports (src, tests, app);
    pyproject name → `yc-scouter`; package docstring/version bumped (0.2.0).
  - [V] no `yc_radar` in *.py/*.toml; `pytest -q` green (53); ruff/black clean.

- [x] **T0.2 Add `src/yc_scouter/config.py` (single source of truth)** ✅
  - Constants + helpers: providers/models, `MAX_DESC_CHARS=2200`, `MAX_TOKENS=430`,
    `AI_BUDGET_TARGET_USD=9.0` (estimate only), `PRICES`, `estimate_cost`, `DATA_DIR`/
    `CACHE_DIR`, `dated_path`, `latest_dated`, `today_iso`, `target_years(2020..now)`,
    `prompt_version` = sha256(SYSTEM+TEMPLATE)[:12].
  - [V] `tests/test_config.py` (7 tests) green.

- [x] **T0.3 Pin environment: `requirements.in` → hashed `requirements.txt` + `.python-version` + `pyproject`** ✅
  - `requirements.in` (source) compiled via `uv pip compile --generate-hashes` to a
    pinned + fully-hashed `requirements.txt` (112 pkgs, 1735 hashes); `.python-version`
    = 3.11. `requirements.txt` doubles as the Streamlit Cloud install file.
  - [V] `uv pip install -r requirements.txt --require-hashes --dry-run` resolves clean;
    `pytest -q` green.

**CP-0 review.**

---

## Phase 1 — Data pipeline (File 1)  → CP-1

- [x] **T1.1 `normalize.py`: add `id`, dedupe by `id` + stable sort, years 2020→current** ✅
  - `id` first in `CORE_COLUMNS` (Int64); default years = `config.target_years()`
    (2020..now); `sort_values("id", stable)` → `drop_duplicates("id")` → year filter.
    Fixture updated (true id-dupe on 101; added a Winter-2020 company).
  - [V] tests: id present+int, dedupe-by-id, stable ascending order, 2020 kept, 2012
    dropped. Full suite 61 green; ruff/black clean.

- [x] **T1.2 `export.py`: dated filename builder** ✅
  - `export(df, *, stage, date, out_dir)` → `yc_dataset_<stage>_<YYYY-MM-DD>.{parquet,xlsx}`
    (dropped CSV; 2 files per stage); Russian tab title ("Данные YC" / "YC + AI");
    freeze panes + autofilter + hyperlinks + illegal-char cleaning retained.
  - [V] `tests/test_export.py` (6): dated names, ai naming, parquet round-trip,
    styled+Russian-title xlsx, control-char strip, list stringify. Suite green.

- [x] **T1.3 `fetch.py`: tidy for full re-scrape** ✅
  - Removed the 24h mtime-cache reliance; `fetch_companies()` downloads **fresh every
    run** by default; `cache_path` writes an optional copy; `use_cache=True` reuses it
    (dev/offline only). Clear RuntimeError on network failure.
  - [V] tests: downloads+writes, default-ignores-stale-cache, use_cache reuse, error.

- [x] **T1.4 `notebooks/01_dataset_base.ipynb` (thin)** ✅
  - Added `pipeline.build_base()` in `src/` so the notebook is 5 cells: params
    (papermill) → bootstrap import → `build_base` → output switch
    (`download`/`drive`/`commit`). English notebook (per language policy).
  - [V] `tests/test_pipeline.py` (3) + `tests/test_notebook_smoke.py` (papermill
    execute on the fixture, `importorskip`) produce the two dated Base files. Suite 66.

- [x] **T1.5 `.github/workflows/build-dataset.yml` (Button 1)** ✅
  - `workflow_dispatch` only; installs `requirements.txt --require-hashes` + `-e .`;
    registers the kernel; runs File 1 via papermill (`output=commit`); commits the
    dated Base files (guarded no-op when unchanged). No secrets. Removed the obsolete
    `build-radar.yml`.
  - [V] YAML parses; trigger = workflow_dispatch; `permissions: contents: write`.

**CP-1 review.**

---

## Phase 2 — AI enrichment (File 2)  → CP-2

- [x] **T2.1 Rewrite `ai.py`** ✅
  - Two outputs `ai_description` (6–7 sentences) + `ai_risks` (1–2 short); generator
    summarizers for Claude (default) + Groq; cache keyed `(id, model_id, prompt_version)`
    with those stored as separate columns; running cost estimate printed from real
    usage (no hard cap); resumable/incremental cache owned by `add_ai_summaries`; input
    truncated to `MAX_DESC_CHARS`, `max_tokens=MAX_TOKENS`; one-liner from YC (not AI).
  - [V] `tests/test_ai.py` (8): missing-only, full-cache skip, placeholder,
    prompt-version-change re-summarize + old preserved, Claude parse+cost print,
    truncation, Groq parse, failure message — all mocked, no spend.

- [x] **T2.2 `notebooks/02_ai_summary.ipynb` (thin)** ✅
  - Added `pipeline.build_ai()` (loads newest Base + cache, summarizes only new keys,
    dated AI export) and `ai.mock_summarizer` (offline, no spend). Notebook: params
    (provider `claude`/`groq`/`mock`, output switch) → bootstrap → `build_ai` → deliver.
  - [V] `test_pipeline.py` build_ai (mock / disk-load / no-key placeholder) +
    `test_notebook_smoke.py` File 2 papermill smoke (mock). Demoed 3 companies, 0 spend.

- [x] **T2.3 `.github/workflows/build-ai-summary.yml` (Button 2)** ✅
  - Separate `workflow_dispatch` with a `provider` choice input (claude/groq);
    `ANTHROPIC_API_KEY`/`GROQ_API_KEY` from Secrets; papermill runs File 2; commits the
    dated AI files + `data/cache/ai_cache.json` (guarded when unchanged).
  - [V] YAML parses; `provider` input + secret env wiring present.

**CP-2 review.**

---

## Phase 3 — Dashboard  → CP-3

- [x] **T3.1 `user_data.py` + `gsheets.py`: key on `id`** ✅
  - `USER_COLUMNS` now starts with `id` (immutable key, survives slug renames);
    `_ensure_columns` coerces `id`→Int64; merge/idempotency join on `id`; gsheets picks
    up the new schema generically.
  - [V] `tests/test_user_data.py` (6) rewritten to id-keyed roundtrip/refresh/idempotency
    + `tests/test_gsheets.py` green.

- [x] **T3.2 `app.py`: Russian UI + newest-dated loader** ✅
  - `dataset_path()` picks the newest `yc_dataset_ai_*` (else `_base_`) via
    `config.latest_dated` (env `YC_SCOUTER_DATASET` overrides); AI columns renamed to
    `ai_description`/`ai_risks`; notes editor keyed on `id`; title → "YC Scouter"; kept
    tabs/filters/charts/compare/export + owner/viewer. Russian UI retained.
  - [V] `tests/test_app.py` (3): env override, newest-AI selection, merged frame has
    ai_* + notes cols; `import app` clean; pytest pythonpath adds repo root.

- [x] **T3.3 Notes migration slug→id** ✅
  - `user_data.migrate_slug_to_id(old, dataset, out_path, backup)`: maps legacy
    slug-keyed CSV to id via a Base/AI parquet's slug→id map, drops unmapped rows,
    backs up the old file to `*.slug.bak`, writes the id-keyed store. (Documented in
    HOW_TO_UPDATE in T4.2.)
  - [V] `test_migrate_slug_to_id`: acme-ai→101, orphan dropped, reloadable by id.

**CP-3 review.**

---

## Phase 4 — Docs & final-phase cleanup  → CP-4

- [x] **T4.1 `docs/HOW_IT_WORKS.md` + `docs/AI_METHODOLOGY.md`** ✅
  - HOW_IT_WORKS: architecture, package map, data source/fields, repro model, update
    flow, dashboard, testing. AI_METHODOLOGY: the File 2 prompts + params/cache, and
    the spec→plan→build/TDD agent-skills workflow with a replicate-me prompt.

- [x] **T4.2 `docs/HOW_TO_UPDATE.md` + `docs/DEPLOY.md` + `README.md`** ✅
  - HOW_TO_UPDATE: routine two-button refresh + a watch-list table (credits, model
    retirement, key rotation, lockfile regen, source drift, sleep, notes) with steps
    and ready AI-agent maintenance prompts. DEPLOY: Streamlit Cloud + Google Sheets +
    owner-lock sharing. Short README with dashboard-link placeholder + "built with
    Claude Code". Added `.streamlit/config.toml`; refreshed `.env.example`.

- [x] **T4.3 Prune to final-phase files** ✅
  - Removed old notebooks (`yc_radar*.ipynb`), `scripts/run_pipeline.py`, `HOSTING.md`,
    `PROJECT_HANDOFF.md`, the old `data/processed/*` (incl. `yc_radar.parquet`).
    Rewrote `.gitignore` (track dated datasets + AI cache; ignore local notes/scratch);
    added `data/.gitkeep` + `data/cache/.gitkeep`; updated `session_start.sh`. Kept
    (flagged for the user): `SPEC.md`, `tasks/`, `scripts/session_start.sh`, `.claude/`.


**CP-4 review → ready to host.**
