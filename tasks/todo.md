# TODO — YC Startup Radar

Task detail + acceptance criteria live in `tasks/plan.md`. Check off as completed.

## Phase 1 — Foundation & walking skeleton
- [x] Task 1 (S): Project scaffold — deps, ruff/black/pytest config, package, data dirs, `.env.example`
- [x] Task 2 (S): `fetch.py` — download + cache `yc-oss/api` JSON
- [x] Task 3 (M): `normalize.py` — typed DataFrame, batch-year parse, filter 2024–2026, dedup
- [x] Task 4 (S): `export.py` (minimal) — Parquet/CSV/styled XLSX
- [x] Task 5 (S): Notebook skeleton — fetch → normalize → export end-to-end

### ✅ Checkpoint: Foundation
- [ ] `pytest` green; `ruff`/`black` clean
- [ ] Notebook runs headless → `data/processed/yc_radar.xlsx` with core columns
- [ ] Human review before Phase 2

## Phase 2 — Enrichment slices
- [x] Task 6 (S): Investability heuristic + status/stage
- [x] Task 7 (M): Open-source deep-dive links (website, YC, News, Product Hunt, HN, GitHub, Wikipedia)
- [ ] Task 8 (M): `score.py` — configurable interestingness score
- [ ] Task 9 (M): `ai.py` — Haiku 4.5 Batch summaries + disk cache

### ✅ Checkpoint: Enrichment
- [ ] Enriched dataset: industry, idea summary, status, investability, score, links
- [ ] AI cached + skips cleanly with no API key
- [ ] `pytest` green; human review before Phase 3

## Phase 3 — Views, persistence, polish
- [ ] Task 10 (M): Streamlit `app.py` — filters, search, sortable table, company cards
- [ ] Task 11 (S): Personal `user_data.csv` persistence (rating/watchlist/notes)
- [ ] Task 12 (S): Analytics charts in the notebook
- [ ] Task 13 (S): Docs + SessionStart hook + green lint/test gate

### ✅ Checkpoint: Complete
- [ ] All SPEC.md §11 success criteria met
- [ ] Ready for `/test` → `/review` → `/ship`
