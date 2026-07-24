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

- [ ] **T2.2 `notebooks/02_ai_summary.ipynb` (thin)**
  - Provider switch + Drive/download/commit switch; load newest Base + repo AI cache;
    summarize only changed keys; export dated AI files; Russian markdown.
  - Accept: papermill run on fixture with a mock provider produces dated AI files and
    the printed cost estimate.
  - [V] papermill smoke run (mock provider) green.

- [ ] **T2.3 `.github/workflows/build-ai-summary.yml` (Button 2)**
  - `workflow_dispatch`; `ANTHROPIC_API_KEY`/`GROQ_API_KEY` from Secrets; run File 2;
    commit dated AI files + updated cache; strip outputs.
  - Accept: YAML valid; secret wiring correct; provider input.
  - [V] YAML parse; logic reviewed.

**CP-2 review.**

---

## Phase 3 — Dashboard  → CP-3

- [ ] **T3.1 `user_data.py` + `gsheets.py`: key on `id`**
  - Replace `slug` join key with `id`; keep USER_COLUMNS + stages/tags; idempotent merge.
  - Accept: merge by id; existing tests updated; idempotent (no `_x/_y`).
  - [V] tests: merge-by-id, idempotency, defaults.

- [ ] **T3.2 `app.py`: Russian UI + newest-dated loader**
  - Load newest `yc_dataset_ai_*.parquet` via glob; keep tabs/filters/charts/compare/
    export; translate all UI strings to Russian; merge notes by id; owner/viewer.
  - Accept: `streamlit run app.py` renders on a fixture dated file; UI in Russian.
  - [V] import/render smoke; `test_app_helpers` (filters) green.

- [ ] **T3.3 Notes migration slug→id**
  - One-off helper: map existing slug-keyed notes to `id` via a fresh dataset;
    write id-keyed store; keep a backup.
  - Accept: existing notes preserved under id; documented in HOW_TO_UPDATE.
  - [V] test on a small fixture mapping.

**CP-3 review.**

---

## Phase 4 — Docs & final-phase cleanup  → CP-4

- [ ] **T4.1 `docs/HOW_IT_WORKS.md` + `docs/AI_METHODOLOGY.md`**
  - Architecture, data flow, APIs/sites used; prompts + skills + how to replicate the
    AI-agent help.
  - Accept: both complete, accurate to the shipped code.

- [ ] **T4.2 `docs/HOW_TO_UPDATE.md` + `docs/DEPLOY.md` + `README.md`**
  - Maintenance checklist (keys, credits, lockfile regen, model migration one-liner,
    two buttons, Streamlit sleep, notes safety), with concrete steps + a ready
    AI-agent prompt for routine ops; deploy steps; short README + dashboard link +
    "built with Claude Code".
  - Accept: a newcomer can operate the project from docs alone.

- [ ] **T4.3 Prune to final-phase files**
  - Remove stray/working files (`scripts/run_pipeline.py`, old notebooks, obsolete
    tests); confirm the tree matches `SPEC.md §13`.
  - Accept: `git ls-files` == the agreed structure; `pytest`/`ruff`/`black` green.
  - [V] structure diff vs SPEC §13.

**CP-4 review → ready to host.**
