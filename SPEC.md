# Spec: YC Scouter

A personal, reproducible toolkit + hosted dashboard to scout and analyze
Y Combinator companies from **2020 to the current year**. It is a significant
rework of the earlier "YC Startup Radar" project: same spirit (collect open YC
data, enrich, summarize with an LLM, review in a dashboard), but re-scoped for a
wider batch range, a two-notebook pipeline, strict cost control, button-only
updates, and a clean final-phase file layout.

> **Language policy:** the whole project is in **English** — code, comments,
> notebooks, docs, and company data. The **only** exceptions are (a) this planning
> chat and (b) the **dashboard UI** (labels, filters, buttons, tabs) which is in
> **Russian**. Company names and AI-generated descriptions stay in English.

---

## 0. Project Phases (shared vocabulary)

- **Working phase** — anything goes: scratch files, worktrees, experiments,
  temporary scripts. The goal is to reach the final state; clutter is fine here.
- **Final phase** — only the agreed files remain. The maintainer's entire routine
  is: press two buttons every few months to rebuild data. Everything else works on
  its own; there are no stray/service files.

This spec defines the **final-phase** target. The working phase may add whatever it
needs to get there.

---

## 1. Objective & User

**Who:** a single maintainer (personal use) scouting YC startups since 2020 to
build a shortlist and do lightweight investment analysis.

**What:** two notebooks that produce dated datasets, a Streamlit dashboard that
browses the latest dataset, and docs that make the project self-maintainable.

**Success looks like:**
1. Notebook **File 1** rebuilds a full "YC Dataset Base" (all companies 2020→now)
   into dated `.parquet` + `.xlsx`.
2. Notebook **File 2** adds LLM `ai_description` + `ai_risks` into a dated
   "YC Dataset AI Summary" `.parquet` + `.xlsx`, paying only for **new/changed**
   companies, at an **estimated ≈ $8.5** for a full run (target ≤ $9).
3. A **hosted Streamlit dashboard** (independent of the maintainer's machine) reads
   the latest dataset, offers rich filters/charts/comparison, and keeps personal
   notes across refreshes.
4. Re-running is **two GitHub Actions buttons** (one per notebook); no structural
   changes to the notebooks are ever required to refresh.

---

## 2. Reproducibility (contract)

Reproducibility here means **logic/code reproducibility, not data reproducibility**:

- The notebooks are **thin** and self-contained: essentially all logic lives in the
  shared `src/yc_scouter/` package, so the same functions run identically in Colab,
  in GitHub Actions, and locally.
- The environment is pinned with a **hashed lockfile** + a fixed **Python 3.11.x**,
  so "same code" behaves the same over time.
- **Data may differ between runs** within normal tolerance — the upstream YC source
  is rebuilt daily, and File 1 deliberately re-scrapes everything on each run. We do
  **not** snapshot raw data or hash-verify datasets. AI text is naturally
  non-deterministic and is bounded only by `temperature=0` + the result cache.

There is **no** dated-raw-snapshot / manifest / sha256 machinery. File 1 fetches
live and processes in the same run.

---

## 3. Data Source

- **`yc-oss/api`** — public community JSON (`all.json`), rebuilt daily from the
  official YC directory. Covers batches **Winter 2020 → current** (~3,800–4,000
  companies in 2020–2026).
- **~29 fields per company**, including: `id` (immutable numeric key), `slug`
  (mutable, used for links only), `name`, `website`, `batch`, `status`
  (Active/Acquired/Public/Inactive), `industry`, `subindustry`, `tags`,
  `one_liner`, `long_description`, `team_size`, `stage`, `regions`/locations,
  `url` (YC profile), `isHiring`, `top_company`, `launched_at`.
- **Not available (do not fabricate):** founders / contacts / social links, cap
  tables, funding amounts, valuations. Missing data → empty cell + an open link.
- **Batch-year filter:** extract the 4-digit year from the batch label
  (`\b20\d{2}\b`), keep 2020→current year. Left boundary fixed at 2020; right
  boundary is "now".

---

## 4. File 1 — Notebook `01_dataset_base`

Full re-scrape every run (cheap, no API key):

1. **Fetch** `all.json` from yc-oss.
2. **Normalize** → typed DataFrame; parse `batch_year`; filter 2020→current;
   **dedupe by `id`** with a **stable total sort** (`sort_values("id")` before
   `drop_duplicates`) so row order is deterministic.
3. **Enrich** → `investability` heuristic + OPEN-source deep-dive links only
   (website, YC profile, Google News, Product Hunt, Hacker News, GitHub, Wikipedia).
4. **Score** → configurable interestingness `score` (0–100).
5. **Export** dated `.parquet` (canonical) + `.xlsx` (human view) into Folder 1.

**Output switch at the top of the notebook** (via env var so structure never
changes): `save to Google Drive folder "Project YC Scouter"` **or** `download when
the run finishes`. In GitHub Actions the mode is `commit to repo`. Google Drive is
**only** for the manual Colab path; it is never wired into Actions.

**Output name:** `yc_dataset_base_<YYYY-MM-DD>.{parquet,xlsx}` (ASCII, ISO date;
the human-facing Russian title lives inside the Excel sheet header, never in the
filename).

---

## 5. File 2 — Notebook `02_ai_summary`

Incremental LLM enrichment, driven by a content-addressed cache:

1. Load the **latest** `yc_dataset_base_*.parquet` (newest by filename).
2. Load the existing AI results/cache **from the repo** (so both Colab and Actions
   start from the same state and don't re-pay).
3. Call the LLM **only** for companies whose cache key
   **`(id, model_id, prompt_version)`** is absent. Nothing else is re-summarized —
   even if a company's description changed, an unchanged key is a cache hit (to
   force a global refresh, change the prompt → `prompt_version` changes).
4. Export dated `.parquet` + `.xlsx` into Folder 1.

### 5.1 LLM outputs (exactly two, factual only)

- **`ai_description`** — 6–7 sentences (~120–140 words): what the company does, the
  idea, what is uniquely differentiated, notable strengths, and any useful factual
  info present in the source. Marked as AI-authored. Prefer richer.
- **`ai_risks`** — 1–2 short, concrete risks. Prefer shorter.

The one-liner is **not** generated by AI — YC's own `one_liner` field is used.
No speculative fields (moat/competitors/traction/funding) — factual only.

### 5.2 Provider switch

- Explicit switch at the top of the notebook: **Claude** (chosen default) or **Groq**
  (kept as an option). Provider + model live in **one config constant / env var**.
- **Default: Claude `claude-haiku-4-5`** ($1 / $5 per 1M input/output).

### 5.3 Token budget (cost estimate, no hard runtime cap)

- `MAX_DESC_CHARS = 2200` (input ≈ 780 tokens/company).
- `max_tokens = 430` (output ≈ 260 tokens/company).
- **Estimated** full run over ~4,000 companies ≈ **$8.3–8.6** (target ≤ $9). This is
  a planning estimate, **not** an enforced runtime limit — the notebook does not
  stop itself at a dollar threshold.
- For visibility, the summarizer **prints a running cost estimate** (from the actual
  token usage returned by each API response) so the maintainer can watch spend, but
  it never auto-halts. The resumable cache still means an interrupted run continues
  where it left off without re-paying.

### 5.4 Cache & reproducibility of AI

- Cache keyed on **`(id, model_id, prompt_version)`**, where
  `prompt_version = sha256(SYSTEM_PROMPT + PROMPT_TEMPLATE)[:12]`.
- All three key parts are stored as **separate columns**; old results are **never
  overwritten** (a new prompt/model writes new rows, preserving history).
- `temperature = 0`. AI text is the sanctioned non-reproducible part.
- **Migration note:** the previous project's summaries used a different (2–3
  sentence summary + 1–2 risks) prompt. The new richer-description prompt has a
  different `prompt_version`, so the existing ~1,736 companies are **re-summarized
  once** — included in the ~$8.5 full-run estimate — to keep one consistent style
  and version across the whole dataset.

---

## 6. Folder 1 — dated dataset store (`data/`)

- Each run writes **4 files**: `base.parquet`, `base.xlsx`, `ai.parquet`,
  `ai.xlsx`, all dated `_<YYYY-MM-DD>`.
- The **dashboard** loads the newest run via
  `sorted(glob("data/yc_dataset_ai_*.parquet"))[-1]` — no pointer file.
- **Git policy:** commit the **latest** dated set the dashboard needs (keeps the
  repo lean); push the **full dated history** to **GitHub Releases** to avoid
  long-term git bloat. AI cache is committed so incremental runs stay cheap.

---

## 7. Update / Refresh (button-only)

- **No cron.** Two **manual** GitHub Actions workflows (`workflow_dispatch`):
  - **Button 1 →** rebuild **File 1** (headless via **papermill** against the
    unchanged `.ipynb`, driven by env vars), commit the dated Base files.
  - **Button 2 →** rebuild **File 2** (reads keys from GitHub Secrets, honors the
    cache + $9 guard), commit the dated AI files.
- The dashboard auto-updates on the resulting push (Streamlit redeploys on commit).
- Personal notes are **never** inside the dataset files, so a refresh cannot delete
  them (see §9).

---

## 8. Dashboard — phase 1 (Streamlit)

- **Host:** **Streamlit Community Cloud** (free; public repo; auto-redeploy on push;
  Secrets UI for the notes backend). Hugging Face Spaces documented as fallback.
- Reads the latest dated dataset from the repo; **never** fetches the internet.
- **UI language: Russian.** Reuses the existing dashboard: tabs (Overview/KPIs +
  Plotly charts, Companies table + CSV/Excel export, Compare up to 5, Notes), and
  filters (industry, subindustry, status, investability, funnel stage, tags,
  favorites, batch year, score & team-size ranges, search).

---

## 9. Personal notes / CRM

- Stored **externally** (Google Sheets, wired later; local CSV until then), keyed on
  the immutable **`id`** (survives slug renames), left-joined at display time.
- A data refresh or redeploy physically cannot delete notes.
- Owner/viewer model: an `[app] owner_key` gates saving; visitors get temporary,
  session-only edits.

---

## 10. Phase 2 — full website (later)

Deferred until phase 1 is complete. Path: publish the dataset as a stable
data-contract artifact (parquet/JSON with pre-computed `score`/`investability`/
`ai_*` columns), build a static front-end (e.g. Cloudflare Pages), add a
database (e.g. Supabase) only when multi-user notes/auth are needed. The pipeline
and dataset are reused unchanged.

---

## 11. Tech Stack

- **Python 3.11.x** (pinned via `.python-version`).
- **Shared package `src/yc_scouter/`** (renamed from `yc_radar`), imported by both
  notebooks and the dashboard.
- Core libs: `httpx`, `pandas`, `pyarrow` (parquet), `openpyxl` (xlsx), `plotly`
  (charts), `streamlit` (dashboard), `anthropic` (Claude), `groq` (optional),
  `gspread`/`google-auth` (notes, later), `papermill` (headless notebook runs in CI).
- Dependencies pinned via a **hashed lockfile** (`requirements.txt`, generated from
  `requirements.in`), installed with `--require-hashes` in Colab + Actions.

---

## 12. Commands

```bash
# Setup (reproducible)
pip install -r requirements.txt --require-hashes    # or: pip install -e .

# File 1 headless (as CI runs it)
papermill notebooks/01_dataset_base.ipynb /tmp/out1.ipynb -p mode ci

# File 2 headless (needs ANTHROPIC_API_KEY)
papermill notebooks/02_ai_summary.ipynb /tmp/out2.ipynb -p provider claude

# Dashboard
streamlit run app.py

# Quality gates
ruff check src tests app.py
black --check src tests app.py
pytest -q
```

---

## 13. Project Structure (final phase — ~20 tracked paths, agreed under constraint 4)

```
README.md                         short overview, "built with Claude Code", live dashboard link
LICENSE
requirements.in                   top-level deps (human-edited)
requirements.txt                 pinned + hashed deps (generated; the reproducibility anchor)
pyproject.toml                    makes `pip install -e .` work so notebooks/app import one package
.python-version                   pins Python 3.11.x everywhere
.gitignore                        excludes .env, *.json creds, caches
.env.example                      key NAMES only (ANTHROPIC_API_KEY, GROQ_API_KEY, Google creds)
app.py                            Streamlit dashboard entry point (Russian UI)
src/yc_scouter/                   shared package: fetch, normalize, enrich, score, export, ai,
                                  filters, user_data, gsheets, config, pipeline
notebooks/
  01_dataset_base.ipynb           File 1: scrape YC 2020→now → dated Base parquet/xlsx
  02_ai_summary.ipynb             File 2: LLM description + risks, cache by (id,model,prompt_version)
data/                             Folder 1: latest dated base+ai (parquet+xlsx) the dashboard reads
  cache/ai_cache.json             AI cache (committed) for cheap incremental runs
docs/
  HOW_IT_WORKS.md                 File 3: architecture, how it works, which APIs/sites used
  AI_METHODOLOGY.md               File 4: prompts + skills + how to replicate the AI-agent help
  HOW_TO_UPDATE.md                maintenance checklist (keys, lockfile, model migration, buttons)
  DEPLOY.md                       hosting steps (Streamlit Cloud + notes backend)
.streamlit/config.toml            dashboard config (+ secrets.toml.example template)
.github/workflows/
  build-dataset.yml               Button 1: File 1 via papermill, commit dated files
  build-ai-summary.yml            Button 2: File 2 via papermill, secrets + cache + $9 guard
tests/                            determinism + schema-guard + logic unit tests
```

Auxiliary files the maintainer might not have anticipated but that are **required**
and were explicitly agreed: `requirements.txt` + `.python-version` (reproducibility),
`src/` package (no duplicated notebook logic), `.github/workflows/` (the two
buttons), `.streamlit/` (dashboard config), `data/cache/` (cheap incremental AI),
`tests/`. Deployment is **config + docs**, not a "File 5 notebook".

---

## 14. Code Style

- PEP 8, **black** (line-length 100), **ruff** (E,F,I,UP,B); type hints on public
  functions.
- Small pure testable functions in `src/`; notebooks orchestrate only.
- Model IDs, token limits, budget, paths, and the dated-filename builder live in
  `src/yc_scouter/config.py` — single source of truth.
- No silent failures on network/API — timeout, retry with backoff, log skips.

---

## 15. Testing Strategy

- **pytest**; network + LLM fully **mocked** (no live calls, no spend in tests).
- Unit tests: batch-year parsing/filter, dedupe-by-id + stable sort, score math,
  open-link generation, notes merge idempotency (keyed by `id`), filter logic,
  AI cache-key + budget-guard logic, schema-guard on the source.
- `ruff`/`black` clean; keep the suite green before every commit.

---

## 16. Boundaries

**Always:**
- Use the public yc-oss JSON; OPEN-source deep-dive links only.
- Keep secrets in `.env`/GitHub Secrets/Streamlit Secrets (never committed).
- Track/print the AI cost estimate (target ≤ $9); key notes + AI cache on `id`.
- Write tests for parsing/scoring/cache/budget logic; keep notebooks thin.

**Ask first:**
- Changing the AI model, prompt (⇒ re-summarization cost), or token budget.
- Adding paid/keyed APIs, scraping any HTML source, or adding a founders source.
- Changing the output schema or the dated-file naming convention.

**Never:**
- Commit API keys / real `.env` / service-account JSON.
- Fabricate founders, cap tables, funding, or valuations.
- Add closed/paywalled links (Crunchbase, LinkedIn, PitchBook).
- Store personal notes inside a regenerated dataset file.
- Remove failing tests without approval.

---

## 17. Maintenance & Longevity (summarized; full checklist in docs/HOW_TO_UPDATE.md)

The project is **not** fully hands-off — expect ~15 min every few months:

| Item | When to act | Action |
|---|---|---|
| Anthropic credits/billing | before a full run | keep balance funded; File 2 is resumable + guarded |
| Model retirement (~6–12 mo) | model ID 404s | change one config constant |
| Groq free-tier / key (if used) | on 401 / limit change | rotate key, keep model in config |
| Locked dependencies | 6–12 mo or on breakage | regenerate `requirements.txt`, re-test |
| GitHub Actions | on use | button-only; each run commits (no 60-day auto-disable concern) |
| yc-oss schema drift | on fetch error | schema-guard fails loudly; keep last-good data |
| Streamlit sleep (12h idle) | on visit | click to wake; normal for a personal tool |
| Notes safety | after any refresh | verify notes survive (external store, keyed by id) |

---

## 18. Resolved Decisions

1. Repo: **public**.
2. **Migrate** the existing repo (rename package `yc_radar → yc_scouter`).
3. Batch range: **2020 → current year**; File 1 full re-scrape each run.
4. Data reproducibility: **logic only**, no snapshots (per user).
5. AI: **Claude `claude-haiku-4-5`**, **two outputs** (`ai_description` richer ~120–140
   words, `ai_risks` 1–2 short), `MAX_DESC_CHARS=2200`, `max_tokens=430`, estimated
   full-run cost ≈ **$8.5** (target ≤ $9, **no** hard runtime cap; prints a running
   cost estimate), cache key `(id, model_id, prompt_version)`. Existing summaries
   re-computed once under the new prompt.
6. Provider switch Claude/Groq; one-liner from YC (not AI).
7. Updates: **two manual buttons** (File 1, File 2); no cron; no Google Drive in CI.
8. Hosting: **Streamlit Community Cloud** now; full website later (phase 2).
9. Notes: external store keyed on **`id`**; owner/viewer model.
10. Language: **English** everywhere except **Russian dashboard UI** (+ this chat).
11. Docs: `HOW_IT_WORKS.md`, `AI_METHODOLOGY.md`, `HOW_TO_UPDATE.md`, `DEPLOY.md`.
12. File naming: `yc_dataset_<base|ai>_<YYYY-MM-DD>.{parquet,xlsx}`.
