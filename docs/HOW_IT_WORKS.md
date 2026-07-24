# How YC Scouter works

This document explains the project from a code/implementation point of view: the
architecture, the data flow, which external services and sites it uses, and the
notable design decisions.

## Big picture

Two notebooks produce **dated datasets**; a Streamlit dashboard reads the newest
one. All real logic lives in one package (`src/yc_scouter/`) so the notebooks stay
thin and behave identically in Colab, in GitHub Actions, and locally.

```
File 1 (01_dataset_base.ipynb)          File 2 (02_ai_summary.ipynb)
  fetch yc-oss all.json                   load newest Base parquet
  -> normalize (id, 2020..now)            -> summarize NEW (id,model,prompt) keys
  -> enrich (investability + links)          via Claude (default) or Groq
  -> score                                -> write yc_dataset_ai_<date>.{parquet,xlsx}
  -> write yc_dataset_base_<date>.*                    |
                     \___________  data/  ____________/
                                     |
                          app.py (Streamlit, Russian UI)
                          reads the newest dated parquet
```

## The package (`src/yc_scouter/`)

| Module | Responsibility |
|---|---|
| `config.py` | Single source of truth: model ids, token budget (`MAX_DESC_CHARS`, `MAX_TOKENS`), price table + `estimate_cost`, `DATA_DIR`/`CACHE_DIR`, `dated_path`/`latest_dated`, `target_years(2020..now)`, `prompt_version`. |
| `fetch.py` | Download `yc-oss/api` `all.json` (fresh every run; optional dev cache). |
| `normalize.py` | Raw records → typed DataFrame; parse `batch_year`; filter 2020→current; **dedupe by `id`** with a stable sort (deterministic order). |
| `enrich.py` | `investability` heuristic (status-derived) + OPEN-source deep-dive links. |
| `score.py` | Configurable interestingness `score` (0–100). |
| `ai.py` | `ai_description` + `ai_risks` via Claude/Groq; cache keyed `(id, model_id, prompt_version)`; running cost estimate. |
| `export.py` | Dated Parquet + styled XLSX (`yc_dataset_<stage>_<YYYY-MM-DD>.*`). |
| `filters.py` | Pure filter/search helpers for the dashboard. |
| `user_data.py` | Personal notes (rating/favorite/tags/stage/notes) keyed by **`id`**; CSV + merge helpers; slug→id migration. |
| `gsheets.py` | Google Sheets backend for notes (hosted persistence). |
| `pipeline.py` | `build_base()` and `build_ai()` — the thin API the notebooks call. |

## Data source & fields

- **`yc-oss/api`** (`https://yc-oss.github.io/api/companies/all.json`) — a
  community JSON export of the official YC directory, rebuilt daily. ~29 fields per
  company. We use: `id` (immutable key), `slug` (links only), `name`, `website`,
  `batch`, `status`, `industry`, `subindustry`, `tags`, `one_liner`,
  `long_description`, `team_size`, `stage`, `regions`, `url`.
- **Not available, never fabricated:** founders/contacts, cap tables, funding,
  valuations. Missing → empty cell + an open link.

## Deep-dive links (open sources only)

`enrich.add_links` builds URLs (no scraping) to freely accessible pages: the
company website, its YC profile, Google News, Product Hunt, Hacker News, GitHub,
Wikipedia. No Crunchbase/LinkedIn/paywalled links.

## Reproducibility model

Reproducibility is about **code logic, not data**: the environment is pinned
(`requirements.txt` hashed lock + `.python-version` 3.11), and the notebooks import
the same package everywhere. Data legitimately differs between runs (the source is
rebuilt daily; File 1 re-scrapes each run). There is no raw-snapshot/manifest
machinery.

## Update flow (button-only)

Two manual GitHub Actions (`workflow_dispatch`): **Button 1** rebuilds the Base
(no keys), **Button 2** adds AI (keys from Secrets). Each commits its dated files;
the dashboard redeploys on the commit. Personal notes live in an external store
keyed by `id`, so a refresh never deletes them. See `docs/HOW_TO_UPDATE.md`.

## Dashboard

`app.py` (Streamlit, Russian UI) reads the newest `yc_dataset_ai_*` (else
`_base_`) via `config.latest_dated` (env `YC_SCOUTER_DATASET` overrides). Four tabs
(Overview/Companies/Compare/Notes), rich filters, Plotly charts, CSV/Excel export
of the filtered view, and an owner/viewer model so a shared link lets visitors
explore with temporary-only edits. See `docs/DEPLOY.md`.

## Testing

`pytest` with the network and the LLM fully mocked (no spend). Notebook smokes run
the real `.ipynb` via papermill on a fixture; the dashboard is checked with
Streamlit `AppTest`. `ruff` + `black` gate style.
