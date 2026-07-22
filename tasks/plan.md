# Implementation Plan: YC Startup Radar (2024–2026)

## Overview
Build a Jupyter-notebook pipeline that fetches Y Combinator companies from batches
2024–2026 (via the public `yc-oss/api` JSON), normalizes them into a typed table,
enriches them with open-source deep-dive links, a configurable interestingness
score, an investability heuristic, and AI idea/uniqueness/risk summaries
(Haiku 4.5, Batch API, disk-cached), then exports **Parquet + Excel + CSV** and
serves a **Streamlit** dashboard for interactive review. Personal ratings/notes
persist across data refreshes. Full spec: `SPEC.md`.

## Architecture Decisions
- **Logic in `src/yc_radar/`, thin notebook.** Every non-trivial function lives in
  the package so it's unit-testable; the notebook only orchestrates + shows charts.
- **Single dataset, two views.** The notebook writes `data/processed/yc_radar.parquet`
  (+ `.xlsx`/`.csv`); Streamlit *reads* that file — it never re-fetches.
- **Walking skeleton first.** Slice 1 is a minimal fetch→normalize→export path that
  produces a real (if sparse) Excel; each later task adds one enrichment dimension
  end-to-end so the system is always runnable.
- **Network is mocked in tests.** No unit test hits the live API; fixtures hold
  sample payloads. This keeps the suite fast and offline.
- **AI cost controlled.** Haiku 4.5 via the Batch API (−50%), prompt-cached prefix,
  and a per-company on-disk cache (`ai_cache.json`) so refreshes only pay for new
  companies. Missing `ANTHROPIC_API_KEY` → AI step skipped gracefully, not fatal.
- **Open sources only.** Deep-dive links point at freely accessible pages
  (website, YC, Google News, Product Hunt, Hacker News, GitHub, Wikipedia). No
  Crunchbase/LinkedIn. Never fabricate funding/cap-table numbers.

## Task List

### Phase 1 — Foundation & walking skeleton
- [ ] Task 1: Project scaffold (config, package, data dirs)
- [ ] Task 2: `fetch.py` — download + cache YC dataset
- [ ] Task 3: `normalize.py` — typed DataFrame, batch-year filter, dedup
- [ ] Task 4: `export.py` (minimal) — write Parquet/CSV/XLSX
- [ ] Task 5: Notebook skeleton — fetch → normalize → export end-to-end

### Checkpoint: Foundation
- [ ] `pytest` green; `ruff`/`black` clean
- [ ] Notebook runs headless and produces `data/processed/yc_radar.xlsx` with core columns
- [ ] Review with human before Phase 2

### Phase 2 — Enrichment slices (each flows through to the export)
- [ ] Task 6: Investability heuristic + status/stage columns
- [ ] Task 7: Open-source deep-dive links
- [ ] Task 8: `score.py` — configurable interestingness score
- [ ] Task 9: `ai.py` — Haiku 4.5 Batch summaries with disk cache

### Checkpoint: Enrichment
- [ ] Enriched dataset has industry, idea summary, status, investability, score, links
- [ ] AI step is cached + skips cleanly with no API key
- [ ] `pytest` green; review with human before Phase 3

### Phase 3 — Views, persistence, polish
- [ ] Task 10: Streamlit `app.py` — filters, search, sortable table, company cards
- [ ] Task 11: Personal `user_data.csv` persistence (rating/watchlist/notes)
- [ ] Task 12: Analytics section in the notebook (distribution charts)
- [ ] Task 13: Docs + SessionStart hook + green lint/test gate

### Checkpoint: Complete
- [ ] All SPEC.md §11 success criteria met
- [ ] Ready for `/test` → `/review` → `/ship`

---

## Tasks (detail)

### Task 1: Project scaffold
**Description:** Create the Python project skeleton so every later task has a home:
dependencies, tooling config, package layout, data directories, and env template.

**Acceptance criteria:**
- [ ] `requirements.txt` pins: httpx, pandas, pyarrow, openpyxl, matplotlib/plotly, streamlit, python-dotenv, anthropic, pytest, pytest-cov, ruff, black
- [ ] `pyproject.toml` configures ruff, black, pytest; `src/yc_radar/__init__.py` importable
- [ ] `.gitignore` excludes `.env`, `data/raw/`, `data/processed/`, `data/user_data.csv`, `__pycache__`; `.env.example` documents `ANTHROPIC_API_KEY`
- [ ] `data/raw/.gitkeep` and `data/processed/.gitkeep` present

**Verification:**
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `python -c "import yc_radar"` works; `ruff check src` and `black --check src` pass

**Dependencies:** None
**Files likely touched:** `requirements.txt`, `pyproject.toml`, `src/yc_radar/__init__.py`, `.gitignore`, `.env.example`, `data/**/.gitkeep`
**Estimated scope:** S

### Task 2: `fetch.py` — download + cache YC dataset
**Description:** Fetch the public `yc-oss/api` companies JSON and cache it under
`data/raw/`, re-using the cache when fresh; return raw records.

**Acceptance criteria:**
- [ ] `fetch_companies(force_refresh=False)` returns a list of company dicts
- [ ] Response cached to `data/raw/yc_companies.json`; cache reused unless stale/forced
- [ ] Network failures raise a clear error; timeouts handled

**Verification:**
- [ ] `pytest tests/test_fetch.py` — HTTP mocked, asserts cache write + reuse
- [ ] Manual: one real run populates `data/raw/yc_companies.json`

**Dependencies:** Task 1
**Files likely touched:** `src/yc_radar/fetch.py`, `tests/test_fetch.py`
**Estimated scope:** S

### Task 3: `normalize.py` — typed DataFrame, batch-year filter, dedup
**Description:** Turn raw records into a clean typed `pandas.DataFrame`, parse the
`batch` field into `batch_year`, filter to 2024–2026, and dedup by `slug`.

**Acceptance criteria:**
- [ ] `normalize(records)` returns a DataFrame with core columns (name, slug, batch, batch_year, industry, subindustry, tags, one_liner, long_description, status, stage, team_size, location, region, is_hiring, top_company, website, yc_url)
- [ ] `batch_year` parsed correctly across YC formats (W24/S24/Fall 2024/2025/2026…)
- [ ] Rows filtered to years {2024,2025,2026} and deduped by slug

**Verification:**
- [ ] `pytest tests/test_normalize.py` — fixture payload; asserts filtering, parsing, dedup, dtypes
- [ ] Manual: normalized DF has only 2024–2026 rows

**Dependencies:** Task 2
**Files likely touched:** `src/yc_radar/normalize.py`, `tests/test_normalize.py`, `tests/fixtures/companies_sample.json`
**Estimated scope:** M

### Task 4: `export.py` (minimal) — Parquet/CSV/XLSX
**Description:** Write the DataFrame to `data/processed/` in three formats, with a
lightly styled Excel (frozen header, autofilter, clickable link columns).

**Acceptance criteria:**
- [ ] `export(df)` writes `yc_radar.parquet`, `.csv`, `.xlsx`
- [ ] Excel has a frozen header row + autofilter; URL columns render as hyperlinks
- [ ] Round-trip: reading the Parquet back yields the same row count

**Verification:**
- [ ] `pytest tests/test_export.py` — writes to a tmp dir, asserts files + round-trip
- [ ] Manual: open `yc_radar.xlsx`, confirm filterable

**Dependencies:** Task 3
**Files likely touched:** `src/yc_radar/export.py`, `tests/test_export.py`
**Estimated scope:** S

### Task 5: Notebook skeleton — end-to-end
**Description:** Create `notebooks/yc_radar.ipynb` that wires fetch → normalize →
export and runs headless to produce the output files.

**Acceptance criteria:**
- [ ] Notebook cells call the `src/yc_radar` functions in order and export
- [ ] `jupyter nbconvert --to notebook --execute` completes without error
- [ ] Produces `data/processed/yc_radar.xlsx` with the core columns

**Verification:**
- [ ] `nbconvert --execute` exits 0 (against cached data)
- [ ] Manual: output Excel exists with 2024–2026 companies

**Dependencies:** Tasks 2–4
**Files likely touched:** `notebooks/yc_radar.ipynb`
**Estimated scope:** S

### Task 6: Investability heuristic + status/stage
**Description:** Add an `investability` column derived from `status` (Public =
market-buyable; Acquired = no; Active/private = accredited/SPV only; Inactive = n/a).

**Acceptance criteria:**
- [ ] `add_investability(df)` returns df with an `investability` category column
- [ ] Mapping matches SPEC §3 and is documented in a docstring
- [ ] Column appears in the exported Excel/Streamlit

**Verification:**
- [ ] `pytest tests/test_enrich.py::test_investability` — asserts each status maps correctly
- [ ] Manual: spot-check a Public and an Acquired company

**Dependencies:** Task 3
**Files likely touched:** `src/yc_radar/enrich.py`, `tests/test_enrich.py`
**Estimated scope:** S

### Task 7: Open-source deep-dive links
**Description:** Generate per-company URLs to freely accessible pages only:
website, YC profile, Google News, Product Hunt, Hacker News (Algolia), GitHub,
Wikipedia. No scraping — just URL construction. No closed/paywalled sources.

**Acceptance criteria:**
- [ ] `add_links(df)` adds `news_url`, `producthunt_url`, `hn_url`, `github_url`, `wikipedia_url` (plus existing website/yc_url)
- [ ] Company names are URL-encoded; missing website → no crash, empty where N/A
- [ ] No Crunchbase/LinkedIn/paywalled URLs anywhere

**Verification:**
- [ ] `pytest tests/test_enrich.py::test_links` — asserts encoding, missing-field handling, no forbidden domains
- [ ] Manual: click 2–3 links in the Excel export

**Dependencies:** Task 3
**Files likely touched:** `src/yc_radar/enrich.py`, `tests/test_enrich.py`
**Estimated scope:** M

### Task 8: `score.py` — configurable interestingness score
**Description:** Compute a weighted 0–100 score from signals (top_company, recency of
batch, is_hiring, team_size band, has-description, tag matches), with weights in a
config dict so the user can retune.

**Acceptance criteria:**
- [ ] `score(df, weights=DEFAULT_WEIGHTS)` adds a numeric `score` column in [0,100]
- [ ] Weights are a documented, overridable dict; deterministic output
- [ ] Higher-signal companies rank above lower-signal ones on a fixture

**Verification:**
- [ ] `pytest tests/test_score.py` — asserts range, determinism, monotonic ordering on crafted rows
- [ ] Manual: sort Excel by score, sanity-check top 10

**Dependencies:** Tasks 3, 6
**Files likely touched:** `src/yc_radar/score.py`, `tests/test_score.py`
**Estimated scope:** M

### Task 9: `ai.py` — Haiku 4.5 Batch summaries with disk cache
**Description:** Summarize `long_description` into `ai_summary` + `ai_risk_notes`
using `claude-haiku-4-5` via the **Batch API**, prompt-caching the shared
instruction prefix and caching per-company results to `data/processed/ai_cache.json`.
Skip cleanly if `ANTHROPIC_API_KEY` is unset.

**Acceptance criteria:**
- [ ] `add_ai_summaries(df)` adds `ai_summary` and `ai_risk_notes`; only new (uncached) companies are sent
- [ ] Uses `claude-haiku-4-5` + Batch API; prefix prompt-cached; results persisted to `ai_cache.json`
- [ ] No `ANTHROPIC_API_KEY` → columns filled with a clear "AI disabled" placeholder, no exception

**Verification:**
- [ ] `pytest tests/test_ai.py` — Anthropic client/batch mocked; asserts cache hit skips API, key-missing path, cache write
- [ ] Manual: small real run (few companies) produces sane summaries

**Dependencies:** Task 3
**Files likely touched:** `src/yc_radar/ai.py`, `tests/test_ai.py`
**Estimated scope:** M

### Task 10: Streamlit `app.py`
**Description:** A dashboard that reads `data/processed/yc_radar.parquet` and offers
sidebar filters (industry, batch, status, team-size, score slider), full-text
search, a sortable table, and a per-company card with the open-source links.

**Acceptance criteria:**
- [ ] `streamlit run app.py` loads the exported dataset and renders the table
- [ ] Filters + search narrow the rows; score slider works; links are clickable
- [ ] Handles "dataset not yet generated" with a friendly message

**Verification:**
- [ ] `pytest tests/test_app_helpers.py` — pure filter/search helpers tested headless
- [ ] Manual: run the app, apply a filter, open a company card

**Dependencies:** Tasks 4, 6–9
**Files likely touched:** `app.py`, `src/yc_radar/filters.py`, `tests/test_app_helpers.py`
**Estimated scope:** M

### Task 11: Personal `user_data.csv` persistence
**Description:** Store `my_rating` / `watchlist` / `my_notes` keyed by `slug` in
`data/user_data.csv`; merge it into the export and let Streamlit edit + save it so
annotations survive data refreshes.

**Acceptance criteria:**
- [ ] `merge_user_data(df)` left-joins user columns by slug; missing file → empty columns, no crash
- [ ] Streamlit can edit rating/watchlist/notes and write back to `user_data.csv`
- [ ] Re-running the pipeline preserves existing annotations

**Verification:**
- [ ] `pytest tests/test_user_data.py` — merge with/without file, refresh preserves values
- [ ] Manual: set a rating, re-run notebook, confirm it survives

**Dependencies:** Tasks 4, 10
**Files likely touched:** `src/yc_radar/user_data.py`, `app.py`, `tests/test_user_data.py`
**Estimated scope:** S

### Task 12: Analytics section in the notebook
**Description:** Add a notebook section with distribution charts: companies by
industry, by batch, by status, and by region/geography.

**Acceptance criteria:**
- [ ] Notebook renders ≥4 charts (industry, batch, status, geography)
- [ ] Charts execute headless via nbconvert without error
- [ ] Brief written takeaways under each chart

**Verification:**
- [ ] `nbconvert --execute` exits 0 with charts rendered
- [ ] Manual: charts are readable and correct vs the table

**Dependencies:** Tasks 5, 8
**Files likely touched:** `notebooks/yc_radar.ipynb`
**Estimated scope:** S

### Task 13: Docs + SessionStart hook + green gate
**Description:** README run instructions (setup, run notebook, run Streamlit, enable
AI), a SessionStart hook so web sessions can run tests/lint, and a final clean
lint/test pass.

**Acceptance criteria:**
- [ ] `README.md` documents setup, the two commands, and how AI enrichment/keys work
- [ ] SessionStart hook installs deps / runs `pytest` + `ruff` in web sessions
- [ ] `pytest --cov=src/yc_radar` ≥ 80%; `ruff`/`black` clean

**Verification:**
- [ ] Coverage report ≥ 80% on `src/yc_radar/`
- [ ] `ruff check` and `black --check` pass

**Dependencies:** Tasks 1–12
**Files likely touched:** `README.md`, `.claude/hooks/` (or repo hook), `pyproject.toml`
**Estimated scope:** S

---

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| `yc-oss/api` schema/field names differ from assumed | Med | Task 3 keeps a defensive field map + fixture from a real payload; verify fields on first fetch |
| YC batch naming for 2026 not yet in dataset | Low | `batch_year` parser tolerant; filter is year-based, absent years just yield fewer rows |
| Anthropic Batch API shape/latency | Med | Mock in tests; small real smoke run; disk cache means one-time cost |
| Company-name → GitHub/Wikipedia link false positives | Low | Links are search/candidate URLs, labeled "candidate"; never presented as authoritative |
| Streamlit write-back races on `user_data.csv` | Low | Single-user tool; write atomically (tmp + rename) |

## Open Questions
- None blocking. (Real `yc-oss/api` field names get confirmed on the first fetch in Task 2/3; the fixture is captured from that.)
