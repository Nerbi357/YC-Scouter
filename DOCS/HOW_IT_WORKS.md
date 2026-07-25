# How YC Scouter works

This document explains the project from the inside: what it is made of, how data
flows through it, which external services it touches, and why the notable
decisions were made the way they were. It is meant to be readable by someone who
has never seen the repository — a curious visitor, a future maintainer, or an AI
agent picking the project up.

---

## 1. The idea in one paragraph

Y Combinator publishes its companies openly. YC Scouter takes every company from
**2020 to the current year**, cleans the data, adds a few honest derived signals
(an "investability" status, open-source research links, an interestingness score),
asks an LLM for a short factual description and a couple of concrete risks per
company, and serves the result as an interactive dashboard where you can filter,
chart, compare and keep private notes. It is a personal scouting tool, not a data
vendor: it never invents numbers it cannot source.

## 2. The five moving parts

```
   ┌──────────────────────────┐        ┌──────────────────────────┐
   │  File 1                  │        │  File 2                  │
   │  notebooks/01_dataset_   │        │  notebooks/02_ai_        │
   │  base.ipynb              │        │  summary.ipynb           │
   │                          │        │                          │
   │  fetch yc-oss all.json   │        │  load newest Base        │
   │  → normalize (id, years) │        │  → summarize NEW keys    │
   │  → enrich + score        │        │    via Claude (or Groq)  │
   │  → write dated Base      │        │  → write dated AI files  │
   └───────────┬──────────────┘        └───────────┬──────────────┘
               │            data/  (dated Parquet + Excel)         │
               └───────────────────────┬───────────────────────────┘
                                       ▼
                            ┌─────────────────────┐
                            │  app.py (Streamlit) │  reads the newest file
                            │  the dashboard      │  never fetches, never pays
                            └──────────┬──────────┘
                                       ▼
                          Google Sheet — your private notes
```

Plus **two buttons** (GitHub Actions) that run File 1 and File 2 on demand, and a
**package** (`src/yc_scouter/`) that holds all the actual logic so the notebooks,
the buttons and the dashboard all run the same code.

## 3. Where the data comes from

- **Source:** the community mirror **[`yc-oss/api`](https://yc-oss.github.io/api/companies/all.json)** —
  a JSON export of the official YC directory, rebuilt daily. Open, no key, no
  scraping.
- **Fields used:** `id` (the immutable key), `slug` (links only), `name`,
  `website`, `batch`, `status`, `industry`, `subindustry`, `tags`, `one_liner`,
  `long_description`, `team_size`, `stage`, `regions`, `url`.
- **Never available, never invented:** founders' contacts, cap tables, funding
  rounds, valuations. Where a fact does not exist publicly, the cell stays empty
  and the card offers an open link instead.

### Derived fields (what the project adds)

| Field | How it is computed | What it means |
|---|---|---|
| `batch_year` | parsed from `batch` ("Winter 2024" → 2024) | lets you filter by year |
| `investability` | derived from YC's `status` (Active / Acquired / Public / Inactive) | an honest status heuristic, **not** a prediction |
| `score` (0–100) | a transparent weighted formula in `score.py` (recency, team size, status, data completeness) | a sortable "worth a look" signal |
| deep-dive links | built as URLs, no scraping: website, YC profile, Google News, Product Hunt, Hacker News, GitHub, Wikipedia | open sources only — no Crunchbase/LinkedIn |
| `ai_description`, `ai_risks` | one LLM call per company (see §5) | 6–7 factual sentences + 1–2 concrete risks |

## 4. The package (`src/yc_scouter/`)

Everything lives here so that a notebook, a CI job and the dashboard behave
identically. Each module does one thing:

| Module | Responsibility |
|---|---|
| `config.py` | **the single source of truth**: model ids, token limits, the price table and cost estimate, data paths, dated-filename helpers, the year range (2020→now), the prompt fingerprint |
| `fetch.py` | download the source JSON (fresh every run; an optional local cache for development) |
| `normalize.py` | raw records → a typed table: parse the batch year, keep 2020→now, **de-duplicate by `id`** with a stable sort so the order is deterministic |
| `enrich.py` | the `investability` heuristic and the open deep-dive links |
| `score.py` | the 0–100 interestingness score |
| `ai.py` | the prompts, the provider adapters (Claude / Groq / offline mock), the resumable cache and the running cost estimate |
| `export.py` | write the dated Parquet + styled Excel pair |
| `filters.py` | the dashboard's filtering and search, kept free of Streamlit so it can be unit-tested |
| `user_data.py` | personal notes: schema, tolerant type coercion, merging onto the company table by `id` |
| `gsheets.py` | the Google Sheets backend for notes, with the safety rules of §7 |
| `pipeline.py` | `build_base()` and `build_ai()` — the thin API the notebooks call |

The notebooks are deliberately **thin**: a parameter cell and a few calls. All
logic that could break lives in the package, where it is tested.

## 5. The AI step — prompts, parameters, cost

Defined in `src/yc_scouter/ai.py`; every knob lives in `config.py`.

**What is asked for.** Exactly two outputs per company:

- `ai_description` — 6–7 sentences: the idea, what is distinctive, strengths,
  useful facts;
- `ai_risks` — 1–2 short, concrete risks worth checking.

The one-liner is **not** generated — YC's own is better and free.

**System prompt (intent, verbatim in the code):** *"You are a venture analyst.
Using ONLY the facts provided … Return a single JSON object with `description`
(6–7 sentences …) and `risks` (1–2 short concrete risks). Do NOT invent facts,
numbers, funding, valuations, traction, or metrics."*

**User prompt:** the company's own fields — name, one-liner, industry and
subindustry, tags, status, team size, batch, stage, and the `long_description`
truncated to `MAX_DESC_CHARS`.

**Parameters** (all in `config.py`):

| Setting | Value | Why |
|---|---|---|
| Model | `claude-haiku-4-5` (default), Groq optional, `mock` offline | cheap, fast, good enough for factual summarising |
| `temperature` | `0` | same input → same output |
| `MAX_DESC_CHARS` | 2200 (≈ 780 input tokens) | a character cap **is** a cost cap |
| `MAX_TOKENS` | 430 (≈ 260 output tokens) | fits the two fields with headroom |
| Full run | ≈ **$7–8.5** for the whole dataset (target ≤ $9) | the summarizer prints a running estimate; it never auto-stops |

**The cache is the cost control.** Every result is stored under
`(id, model_id, prompt_version)`, where
`prompt_version = sha256(SYSTEM_PROMPT + PROMPT_TEMPLATE)[:12]`. Consequences:

- re-running File 2 charges **only for companies that are new** (a refresh after a
  full run costs cents);
- a crash mid-run is harmless — the next run resumes;
- editing the prompt changes the fingerprint, which re-summarises everything
  **on purpose**, and old results are kept rather than overwritten;
- the model id is part of the key, so switching models re-summarises once and the
  dataset always records which model produced it.

## 6. Reproducibility — what it does and does not mean

**Reproducible: the code.** The environment is pinned to a hashed lockfile
(`requirements.txt`, installed with `--require-hashes`) on Python 3.11, and both
notebooks import the same package as CI and the dashboard.

**Not reproducible: the data — by design.** The source is rebuilt daily and
companies get added, renamed and re-classified. Two runs a week apart legitimately
differ. There is no snapshot/manifest machinery, because pretending the world is
frozen would be the bigger lie. What *is* guaranteed: every run is written to its
own dated pair of files, so previous results stay exactly as they were.

## 7. The dashboard (`app.py`)

A Streamlit app with a Russian UI. It **reads** the newest
`data/yc_dataset_ai_*.parquet` (falling back to `_base_`), and never fetches or
calls an AI — so it is fast, free and cannot spend money.

**Layout:** filters in the sidebar (search, industry/subindustry, status,
investability, funnel stage, tags, favourites, batch year, integer From/To ranges
for score and team size) and four tabs — **Обзор** (KPI cards and six charts),
**Компании** (a selectable table, a detail card, and paginated company cards),
**Сравнение** (up to 5 companies side by side), **Заметки** (bulk editing).
Export (CSV / Excel / Parquet) sits on the tab bar, flush right, and builds the
file only when asked.

**Rules the dashboard is built to obey** — each one exists because breaking it
caused a real failure:

- **Nothing heavy is built eagerly.** Exports are generated on demand; search is
  vectorised; the card list is paginated at 50; per-card note editors open on a
  button. Building exports on every rerun once exhausted the free tier's resources.
- **The most-used interaction gets its own render scope.** The table and the detail
  card live in a single `st.fragment`, so picking a company repaints that block
  only — 1.1 s → 0.4 s on the full dataset.
- **Widget state is tied to what is on screen.** Streamlit remembers a selection
  and table edits by *row position*, so both the table and the notes editor derive
  their key from the visible ids — otherwise a filter change silently opens or
  edits a different company.
- **Imperfect data must not kill the page.** `prepare_data()` drops rows with an
  unusable `id`, collapses duplicate ids (they would collide as widget keys), and
  fills columns a rebuild might have dropped. Only a missing `id`/`name` stops the
  app, with an instruction instead of a blank crash page.
- **A failed read never authorises a write.** Notes are read from the Sheet once
  per session; while the Sheet is unreadable, saving is blocked, and the backend
  refuses to overwrite a populated sheet with an empty one (it writes first, then
  clears leftovers).
- **Access fails closed.** With a shared Sheet configured and no owner key set,
  everyone is a visitor — never everyone an owner.
- **Visitors are isolated both ways.** A visitor's notes live in their session:
  fully functional, invisible to the owner, and never written to the shared store.
- **Any uncaught error is explained.** The whole render is wrapped so a failure
  shows the reason, a reset button and the details — never an empty page.

## 8. Updating — two buttons, no schedule

`.github/workflows/build-dataset.yml` and `build-ai-summary.yml` are manual
(`workflow_dispatch`) workflows. Each installs the pinned lockfile, runs the real
notebook headlessly with **papermill**, and commits the dated output files (File 2
also commits the updated AI cache). Pushing to `main` redeploys the dashboard
automatically.

Before spending anything, File 2 runs a **preflight** (`src/yc_scouter/preflight.py`):
key present, key valid, credit available, model still offered. Each of those four
failures gets a named message with the fix, on the first line of the log, instead of
the run dying in the middle. See `HOW_TO_UPDATE.md`.

There is deliberately **no cron**: data that changes only when the owner asks is
predictable, cannot silently spend money, and cannot break the live dashboard
while nobody is watching. Personal notes are keyed by the immutable company `id`
and stored outside the repository, so a refresh never touches them.

Step-by-step instructions: [`HOW_TO_UPDATE.md`](HOW_TO_UPDATE.md).

## 9. Testing

`pytest` with the network and the LLM fully mocked — running the suite never costs
anything. Alongside the unit tests:

- **notebook smokes** execute the real `.ipynb` files through papermill against a
  fixture, so a broken notebook fails in CI rather than in Colab;
- **AppTest render tests** boot the dashboard headlessly and assert it renders
  without exceptions;
- **browser checks** (Playwright, run manually against the real dataset) verify
  what unit tests cannot see: that tabs are clickable, that the card matches the
  clicked row, that a note typed in the UI reaches storage.

## 10. Where to look next

- [`HOW_TO_DEPLOY_DASHBOARD.md`](HOW_TO_DEPLOY_DASHBOARD.md) — publish it yourself.
- [`HOW_TO_UPDATE.md`](HOW_TO_UPDATE.md) — the maintenance checklist.
- [`../AI_USAGE/PROJECT_MEMORY.md`](../AI_USAGE/PROJECT_MEMORY.md) — the continuity
  file for working on this project with an AI agent, next to the instructions that
  agent follows.
