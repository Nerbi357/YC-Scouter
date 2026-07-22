# YC Startup Radar (2024–2026)

A personal radar for Y Combinator startups from the last three batches years
(**2024–2026**). It fetches the public YC company data, filters and cleans it,
enriches each company with an investability heuristic, open-source deep-dive
links, a configurable interestingness score, and optional AI idea/uniqueness/risk
summaries, then gives you two ways to review:

- a **styled Excel** snapshot you can sort/filter/annotate offline, and
- an interactive **Streamlit** dashboard for filtering, searching, and shortlisting.

Personal ratings/notes persist across data refreshes. Full requirements: `SPEC.md`.
Implementation plan: `tasks/plan.md`.

## Data sources & honesty

- **Core data:** the community `yc-oss/api` JSON (rebuilt daily from the official
  YC directory).
- **Deep-dive links:** OPEN sources only — company website, YC profile, Google
  News, Product Hunt, Hacker News, GitHub, Wikipedia. No Crunchbase/LinkedIn or
  other paywalled/login-walled links.
- **Not included, by design:** cap tables and exact funding/valuation numbers for
  private startups don't exist publicly, so the tool never fabricates them. The
  `investability` column is an honest, status-derived heuristic.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: add ANTHROPIC_API_KEY to enable AI summaries
```

## Run the pipeline (produces the dataset + Excel)

```bash
# interactive
jupyter lab notebooks/yc_radar.ipynb

# or headless
jupyter nbconvert --to notebook --execute notebooks/yc_radar.ipynb --output yc_radar.ipynb
```

Outputs land in `data/processed/`: `yc_radar.parquet` (canonical), `yc_radar.xlsx`
(styled, clickable links), and `yc_radar.csv`.

## Browse it (Streamlit)

```bash
streamlit run app.py
```

The dashboard reads the exported Parquet — run the notebook first. Filter by
industry/status/batch/team-size/score, search, open per-company cards, and edit
your rating / watchlist / notes (Save writes to `data/user_data.csv`).

## AI summaries & cost

AI idea/uniqueness/risk summaries use **Claude Haiku 4.5** via the Batch API.

- They run **only** when `ANTHROPIC_API_KEY` is set (in `.env`). Without it, the
  columns show a placeholder and **no API call — and no charge — is made**.
- Billing follows your key: the summaries are charged to *your* Anthropic account
  when *you* run the notebook. Full YC 2024–2026 set ≈ **$1.5–3 one-time** (Batch
  API −50% + prompt caching).
- Results cache to `data/processed/ai_cache.json`, so re-runs only pay for **new**
  companies.

## Project layout

```
notebooks/yc_radar.ipynb   pipeline + analytics (fetch→normalize→enrich→score→AI→export)
app.py                     Streamlit dashboard (reads the export)
src/yc_radar/              reusable, tested logic
  fetch.py  normalize.py  enrich.py  score.py  ai.py  export.py  filters.py  user_data.py
tests/                     pytest suite (network + AI fully mocked)
data/                      raw cache + processed exports (gitignored)
SPEC.md  tasks/plan.md     spec and implementation plan
```

## Development

```bash
pytest --cov=src/yc_radar   # tests never hit the network or the AI API
ruff check src tests app.py
black src tests app.py
```
