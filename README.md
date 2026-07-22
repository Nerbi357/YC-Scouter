# YC Startup Radar (2024–2026)

A personal radar for Y Combinator startups from the last three batches years
(**2024–2026**). It fetches the public YC company data, filters and cleans it,
enriches each company with an investability heuristic, open-source deep-dive
links, a configurable interestingness score, and optional AI idea/uniqueness/risk
summaries, then gives you two ways to review:

- a **styled Excel** snapshot you can sort/filter/annotate offline, and
- an interactive **Streamlit** dashboard for filtering, searching, and shortlisting.

Personal ratings/notes persist across data refreshes. Full requirements: `SPEC.md`.

## ▶️ Easiest: run on Google Colab (all-in-one)

Open **`notebooks/yc_radar_colab.ipynb`** in Google Colab and `Runtime → Run all`.
It is self-contained (no repo clone, no local setup) and:

1. installs dependencies and writes its own pipeline module + dashboard app,
2. fetches live YC data → builds **`yc_radar.xlsx`** and pops a download,
3. (optional) fills AI idea/risk summaries if you add an `ANTHROPIC_API_KEY` in
   Colab **Secrets** (🔑) — Claude Haiku 4.5, ≈ 3–4 USD for the full set; skip it and
   the AI columns show a placeholder with no charge,
4. launches the **Streamlit dashboard** behind a temporary public
   `trycloudflare.com` link (the last cell prints the URL; stop that cell to shut
   the dashboard down).

To upload it to Colab: `File → Upload notebook` and pick
`notebooks/yc_radar_colab.ipynb`, or push this repo to GitHub and open the notebook
via Colab's GitHub tab.

> Colab note: Streamlit can't be reached directly from Colab, so the notebook
> tunnels it via cloudflared — that's why you get a public link instead of
> `localhost`. The Excel file is the primary deliverable; the dashboard is for
> interactive browsing of that same data.

---

The sections below describe running the project **locally** (outside Colab).
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

## AI summaries

AI idea/uniqueness/risk summaries are pluggable engines in `ai.py`:

- **Claude Haiku 4.5 (paid, cheap — recommended)** — `make_claude_summarizer(...)`,
  synchronous with a resumable cache and progress output. Tuned for review quality
  within budget: cheapest capable model, `max_tokens=500` (richer 2–3 sentence
  summary + concrete risks), truncated input (`MAX_DESC_CHARS=1500`) → ≈ **3–4 USD**
  for the full 2024–2026 set. For the absolute lowest price, use the Batch API (−50%):
  `add_ai_summaries(df, api_key=...)` with no summarizer.
- **Groq (free)** — `make_groq_summarizer(...)`, free tier at console.groq.com.
  Note: the free daily token cap can't cover the whole set in one run.

Either way: no key → the columns show a placeholder and **no API call is made**.
Results cache to `data/processed/ai_cache.json`, so re-runs only summarize **new**
companies. The engine is injected via the `summarizer=` argument of
`add_ai_summaries`, so swapping it never touches the rest of the pipeline.

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
