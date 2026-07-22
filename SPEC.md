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
- **Patents count** — PatentsView / Google Patents by assignee name. Fuzzy name
  matching → flagged as approximate, never authoritative.
- **Deep-dive links** — generated URLs (no scraping): Crunchbase search, LinkedIn
  company search, Google News, the startup's own site, YC profile.
- **GitHub signal** — for devtools/OSS startups, star count if a public repo is
  found (optional).
- **AI idea/uniqueness summary & risk notes** — optional, via the Claude API,
  summarizing `long_description` into "what they do / why unique / what to check".
  Requires an API key; off by default.

### Tier C — NOT publicly available (explicitly out of scope)
- ❌ **Cap table** for private startups — does not exist publicly. Only public
  (post-IPO) companies have a real capital structure, surfaced via `status=Public`.
- ❌ **Exact funding amounts / valuations / round details** — not in YC data.
  Crunchbase has some, but it is a paid/limited API → represented as **link-outs**,
  not fabricated numbers.
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
| `crunchbase_url`, `linkedin_url`, `news_url` | B | generated deep-dive links |

**Optional (Tier B):** `patents_count`, `github_stars`, `ai_risk_notes`.

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

### Recommended presentation (pick during Plan phase)
- **(A)** Notebook + styled Excel export — simplest, fully offline review. ✅ default
- **(B)** Notebook + Streamlit dashboard — best interactive browsing/filtering.
- **(C)** Both (A produces the data, B browses it).

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
  processed/                → exported xlsx/csv (gitignored)
app.py                      → optional Streamlit dashboard (option B)
tests/
  test_normalize.py         → batch filtering, typing, dedup
  test_score.py             → scoring math
  test_enrich.py            → link generation, patent-match fallbacks
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
- Fabricate or estimate cap-table / funding / valuation numbers and present them as
  fact.
- Remove failing tests without approval.

---

## 11. Success Criteria

- [ ] Notebook runs end-to-end and outputs `data/processed/yc_radar.xlsx` + `.csv`.
- [ ] Contains all YC companies from batches 2024, 2025, 2026 (deduplicated).
- [ ] Each row has: industry, idea summary, status, investability, team_size,
      score, and deep-dive links.
- [ ] Output is filterable/sortable by industry, batch, status, team size, score.
- [ ] Analytics section: distributions by industry, batch, status, geography.
- [ ] `src/yc_radar/` logic covered by tests ≥ 80%; `ruff`/`black` clean.
- [ ] Honest handling of unavailable data (no fabricated financials).

---

## 12. Open Questions (for user)

1. **Presentation:** option A (Excel only), B (Streamlit dashboard), or C (both)?
2. **AI summaries:** enable optional Claude-API "idea/uniqueness/risk" summaries
   (needs API key, small cost) or keep raw descriptions only?
3. **Patents enrichment:** include best-effort patents count (fuzzy, slower), or
   skip for v1?
4. **Batch scope:** all batches tagged 2024–2026 as they appear in the source — OK?
5. **Crunchbase:** link-outs only (free) is the plan — confirm you don't have a
   Crunchbase API key you want to use for real funding numbers.
```
