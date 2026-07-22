# Spec: YC Startup Radar (2024–2026)

A personal research tool that collects Y Combinator companies from the last three
years (batches **2024–2026**), enriches them with as much decision-useful data as
is publicly obtainable, and presents them in a filterable, sortable form so the
user can review startups and decide which are worth deeper diligence / potential
investment interest.

---

## 1. Objective

**Who:** A single user (personal use), reviewing YC startups to build a personal
"radar" and shortlist companies of interest.

**What:** A Jupyter notebook (primary deliverable) that:
1. Parses YC companies filtered to batches from 2024, 2025, 2026.
2. Normalizes them into a clean, typed table (pandas DataFrame).
3. Enriches with best-effort external signals (patents, deep-dive links, optional
   AI summaries).
4. Computes an interpretable ranking score.
5. Exports a review-friendly file (Excel + CSV) and provides analytics charts.

**Why:** Speed up manual review. The user browses the output, filters/sorts by the
criteria they care about, and marks a personal shortlist.

**Success looks like:** One command / one notebook run produces an `.xlsx` (and
`.csv`) of all YC 2024–2026 companies with, at minimum, per company: **industry,
idea summary (what they do + uniqueness), status, investability signal, key
quantitative fields, deep-dive links, and a ranking score** — filterable by
industry, batch, status, team size, and score.

---

## 2. Data Sources & Availability (honest scope)

### Tier A — Core, reliable (primary source)
**`yc-oss/api`** — public JSON, MIT-style community dataset, rebuilt daily from the
official YC directory. Fields per company:

- `name`, `slug`, `website`, `all_locations` / `regions`
- `one_liner`, `long_description`, `team_size`
- `industry`, `subindustry`, `tags`, `batch`, `stage`, `status`
- `status` ∈ {`Active`, `Acquired`, `Public`, `Inactive`}
- `isHiring`, `top_company`, `nonprofit`, `launched_at`
- diversity highlights, demo-day/app video flags, `url` (YC profile)

Fallback / cross-check: YC's own Algolia-backed company search endpoint.

### Tier B — Enrichment, best-effort (optional notebook cells)
- **Deep-dive links (OPEN sources only)** — generated URLs (no scraping), pointing
  only at freely accessible pages so the user can study each company at no cost:
  the startup's own **website**, its **YC profile**, **Google Search/News**,
  **Product Hunt**, **Hacker News (Algolia search)**, **GitHub**, and **Wikipedia**.
  No Crunchbase / LinkedIn / paywalled or login-walled links.
- **GitHub signal** — for devtools/OSS startups, star count if a public repo is
  found (optional).
- **AI idea/uniqueness summary & risk notes** — optional, via the Claude API,
  summarizing `long_description` into "what they do / why unique / what to check".
  Requires an API key; off by default. Cost estimate in §5a.
- ~~Patents count~~ — **dropped for v1** (fuzzy matching, low signal/effort ratio).

### Tier C — NOT publicly available (explicitly out of scope)
- ❌ **Cap table** for private startups — does not exist publicly. Only public
  (post-IPO) companies have a real capital structure, surfaced via `status=Public`.
- ❌ **Exact funding amounts / valuations / round details** — not in YC data, and
  the closest sources (Crunchbase/PitchBook) are paywalled/login-walled, which the
  user has excluded. Represented only via **open** link-outs (Google News, HN),
  never fabricated numbers.
- ❌ Anything requiring scraping sources whose ToS forbid it (e.g. LinkedIn).

> **Rule:** Never fabricate or estimate financial figures and present them as fact.
> Missing = empty cell + a link to where the user can check manually.

---

## 3. Output Columns (the final table)

**Required (Tier A + derived):**
| Column | Source | Notes |
|---|---|---|
| `name` | A | |
| `batch` / `batch_year` | A | filtered to 2024–2026 |
| `industry`, `subindustry`, `tags` | A | primary filters |
| `one_liner` | A | short idea |
| `idea_summary` | A/derived | "what they do + uniqueness" (from long_description, optional AI) |
| `status` | A | Active / Acquired / Public / Inactive |
| `stage` | A | |
| `team_size` | A | quantitative |
| `location`, `region` | A | |
| `is_hiring` | A | activity signal |
| `top_company` | A | YC's own success signal |
| `investability` | derived | Public=market-buyable; Acquired=no; Active=accredited/SPV only |
| `score` | derived | weighted, configurable ranking |
| `yc_url`, `website` | A | |
| `news_url`, `producthunt_url`, `hn_url`, `github_url`, `wikipedia_url` | B | OPEN-source deep-dive links only |

**Optional (Tier B):** `github_stars`, `ai_summary`, `ai_risk_notes` (patents dropped for v1).

**User-owned (persisted across refreshes):** `my_rating` (0–5), `watchlist` (bool),
`my_notes` (free text).

---

## 4. Additional criteria available for the radar (proposed)

Beyond industry + idea + quantitative metrics, these are cheaply derivable and
useful for reviewing:
- Founder count / repeat-founder & background keywords (where present in profile)
- Hiring intensity (open-roles / isHiring)
- Top-company flag (YC-marked breakouts)
- B2B vs B2C / business-model tags
- Geography & region clustering
- Website liveness / domain signal
- Product-launch traction (Hacker News / Product Hunt presence — optional)
- Description-derived keywords: "moat", "AI", "open-source", regulated-market flags
- A configurable **interestingness score** combining the above with user weights

---

## 5. Tech Stack

- **Language:** Python 3.11+
- **Primary deliverable:** `notebooks/yc_radar.ipynb`
- **Core libs:** `requests`/`httpx`, `pandas`, `openpyxl` (styled Excel export),
  `matplotlib`/`plotly` (charts), `python-dotenv`
- **Reusable logic:** `src/yc_radar/` package (imported by the notebook so logic is
  testable, notebook stays thin)
- **Optional review UI:** `app.py` — a **Streamlit** dashboard reading the exported
  dataset (interactive filters/sort/search). Recommended as the browsing layer.
- **Optional AI enrichment:** Claude API (`anthropic`), off by default.

### Presentation: **BOTH (C)** — how the two layers work together

The notebook and the dashboard are **two views of one dataset**, not two separate
apps:

1. **`notebooks/yc_radar.ipynb` = the pipeline + producer.** It fetches YC data,
   normalizes/filters to 2024–2026, enriches (open links, optional AI), scores, and
   **writes the single source of truth** to `data/processed/yc_radar.parquet` (+ a
   styled `.xlsx` and a `.csv`). It also holds the analytics/charts. Run it whenever
   you want fresh data. → produces **Excel**, a portable offline snapshot you can
   sort/filter/annotate anywhere.
2. **`app.py` (Streamlit) = the consumer / browser.** It **reads that same exported
   file** and gives an interactive UI: sidebar filters (industry, batch, status,
   team size, score slider), full-text search, sortable table, and a per-company
   card with all the open-source links. It never re-fetches — it just browses what
   the notebook produced.
3. **Personal notes survive refreshes.** Your `my_rating` / `watchlist` / `my_notes`
   live in a separate `data/user_data.csv` keyed by company `slug`. Both the
   notebook export and the Streamlit app read/merge it, so re-running the pipeline
   with fresh YC data never wipes your annotations.

Flow: `run notebook → yc_radar.parquet/.xlsx → streamlit run app.py`. Excel = the
snapshot you keep; Streamlit = live exploration of that snapshot.

### 5a. AI Summary cost estimate (optional feature, OFF by default)

Assumptions: **~1,200–1,600 companies** in batches 2024–2026 (use 1,500 for the
math); per company ≈ **700 input tokens** (long description + one-liner + prompt) +
**250 output tokens**.

| Model | $/1M in · out | Per company | **~1,500 companies** | With Batch API (−50%) |
|---|---|---|---|---|
| **Haiku 4.5** (recommended) | $1.00 · $5.00 | ~$0.0020 | **≈ $2.9** | **≈ $1.5** |
| Sonnet 5 | $3.00 · $15.00 | ~$0.0059 | ≈ $8.8 | ≈ $4.4 |
| Opus 4.8 (overkill) | $5.00 · $25.00 | ~$0.0098 | ≈ $14.6 | ≈ $7.3 |

**Bottom line:** enabling AI summaries for the whole YC 2024–2026 set costs roughly
**$1.5–3 with Haiku 4.5** (one-time per full refresh; prompt-caching the shared
instruction prefix trims it further). Cheap enough to enable — but it stays **off by
default** and behind your own `ANTHROPIC_API_KEY` so nothing runs without your
explicit opt-in.

---

## 6. Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the notebook end-to-end (headless)
jupyter nbconvert --to notebook --execute notebooks/yc_radar.ipynb \
  --output yc_radar.ipynb

# Or open interactively
jupyter lab notebooks/yc_radar.ipynb

# Optional interactive dashboard (if option B chosen)
streamlit run app.py

# Lint / format / test
ruff check src tests
black src tests
pytest -q --cov=src/yc_radar
```

---

## 7. Project Structure

```
SPEC.md                     → this spec (source of truth)
requirements.txt            → pinned dependencies
.env.example                → optional API keys (never commit real .env)
notebooks/
  yc_radar.ipynb            → primary deliverable: parse → enrich → analyze → export
src/yc_radar/
  fetch.py                  → download YC dataset (with local cache)
  normalize.py              → clean/typed DataFrame, batch-year filter (2024–2026)
  enrich.py                 → patents, deep-dive links, optional AI/GitHub
  score.py                  → configurable interestingness score
  export.py                 → styled Excel + CSV export
data/
  raw/                      → cached API responses (gitignored)
  processed/                → exported yc_radar.parquet / .xlsx / .csv (gitignored)
  user_data.csv             → personal ratings/watchlist/notes (persisted, gitignored)
app.py                      → Streamlit dashboard (reads data/processed/)
tests/
  test_normalize.py         → batch filtering, typing, dedup
  test_score.py             → scoring math
  test_enrich.py            → open-source link generation, graceful missing-field handling
```

---

## 8. Code Style

- PEP 8, formatted by **black**, linted by **ruff**; type hints on public functions.
- Small, pure, testable functions; the notebook orchestrates, `src/` holds logic.
- No silent failures on external calls — handle timeouts, log skips, keep going.

```python
def filter_batches(df: pd.DataFrame, years: tuple[int, ...] = (2024, 2025, 2026)) -> pd.DataFrame:
    """Keep only companies whose batch falls in the given years."""
    years_set = set(years)
    return df[df["batch_year"].isin(years_set)].reset_index(drop=True)
```

---

## 9. Testing Strategy

- **Framework:** pytest (+ pytest-cov).
- **Unit tests** on `src/yc_radar/` pure logic: batch-year parsing/filtering, dedup,
  score computation, deep-dive link generation, graceful handling of missing fields.
- External network calls are **mocked** (fixtures with sample API payloads) — tests
  never hit the live API.
- Notebook smoke-executed in CI via `nbconvert --execute` against cached fixture
  data (optional, once stable).
- Coverage target: ≥ 80% on `src/yc_radar/`.

---

## 10. Boundaries

**Always:**
- Use the public YC JSON API; cache responses locally; respect rate limits.
- Attribute the data source; keep secrets in `.env` (gitignored).
- Leave a cell/empty value + a manual-check link when data is unavailable.
- Write tests for parsing/normalization/scoring logic.

**Ask first:**
- Adding paid/keyed APIs (Crunchbase, patents key) or the AI-enrichment step (cost).
- Scraping any HTML source (ToS review first).
- Adding heavy dependencies or changing the output schema.

**Never:**
- Commit API keys or a real `.env`.
- Scrape sources that forbid it (e.g. LinkedIn).
- **Add links to closed / paywalled / login-walled resources** (Crunchbase,
  LinkedIn, PitchBook) — open sources only, per user decision.
- Fabricate or estimate cap-table / funding / valuation numbers and present them as
  fact.
- Remove failing tests without approval.

---

## 11. Success Criteria

- [ ] Notebook runs end-to-end and outputs `data/processed/yc_radar.parquet`,
      `.xlsx`, and `.csv`.
- [ ] Contains all YC companies from batches 2024, 2025, 2026 (deduplicated).
- [ ] Each row has: industry, idea summary, status, investability, team_size,
      score, and OPEN-source deep-dive links.
- [ ] Streamlit `app.py` reads the exported dataset and filters/sorts/searches it.
- [ ] Personal `my_rating` / `watchlist` / `my_notes` persist across data refreshes.
- [ ] Analytics section: distributions by industry, batch, status, geography.
- [ ] `src/yc_radar/` logic covered by tests ≥ 80%; `ruff`/`black` clean.
- [ ] Honest handling of unavailable data (no fabricated financials, open links only).

---

## 12. Resolved Decisions (from user, 2026-07-22)

1. **Presentation:** **C — both** Excel + Streamlit (see §5, how they work together).
2. **Deep-dive links:** **OPEN sources only** (website, YC, Google News, Product Hunt,
   Hacker News, GitHub, Wikipedia). No Crunchbase / LinkedIn / paywalled links.
3. **AI summaries:** optional, **OFF by default**, behind user's own API key.
   Full-set cost ≈ **$1.5–3 with Haiku 4.5** (see §5a) — user to opt in later.
4. **Patents:** **dropped for v1.**
5. **Batch scope:** all batches tagged **2024–2026** as they appear in the source. ✅
6. **No Crunchbase API key** — funding stays as open link-outs, never numbers.
```
