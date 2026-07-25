# YC Scouter

A personal tool to scout and analyze **Y Combinator companies from 2020 to now**.
It collects the public YC data, enriches it (investability heuristic, open-source
deep-dive links, an interestingness score), adds concise **AI descriptions + risks**
per company, and serves it in an interactive dashboard for filtering, charting,
comparing, and keeping a personal shortlist.

> 🔗 **Live dashboard:** **https://nerbi357-yc-scouter.streamlit.app/**
> (deploy your own: [`docs/HOW_TO_DEPLOY_DASHBOARD.md`](docs/HOW_TO_DEPLOY_DASHBOARD.md)).

> Built with **[Claude Code](https://claude.com/claude-code)** using spec-driven,
> test-driven agent skills — see [`AI_USAGE/`](AI_USAGE/AI_METHODOLOGY.md).

## What's inside

- **File 1** — `notebooks/01_dataset_base.ipynb`: collects all YC companies
  (2020→now) into a dated `yc_dataset_base_<date>.parquet` + `.xlsx`.
- **File 2** — `notebooks/02_ai_summary.ipynb`: adds `ai_description` + `ai_risks`
  (Claude by default, or Groq) into `yc_dataset_ai_<date>.parquet` + `.xlsx`, paying
  only for new companies (≈ $8 for a full run, cents for a refresh).
- **Dashboard** — `app.py`: a Streamlit app (Russian UI) reading the newest dated
  dataset; filters, charts, comparison, export, and personal notes.
- **Two buttons** — GitHub Actions rebuild the data on demand; no schedule.

## Repository map

| Path | What it is |
|---|---|
| `app.py` | the dashboard — the only thing you run |
| `src/yc_scouter/` | all the logic; the notebooks, CI and the app import it |
| `src/tests/` | the test suite (network + LLM mocked, so it never costs anything) |
| `notebooks/` | File 1 and File 2 — thin wrappers over the package |
| `data/` | dated datasets (Parquet + Excel) and the AI cache |
| `docs/` | documentation for humans (see below) |
| `AI_USAGE/` | how this was built with AI, written to be reusable elsewhere |
| `.github/workflows/` | the two update buttons |
| `.streamlit/` | dashboard config + a secrets template |
| `.claude/` | agent skills and session setup used while building |

## Quick start (local)

```bash
pip install -r requirements.txt --require-hashes    # or: pip install -e .
streamlit run app.py                                 # dashboard (after data exists)
pytest                                               # tests (network + LLM mocked)
```

Run the pipeline via the notebooks (Colab or `papermill`), or the two GitHub
Actions workflows. AI needs `ANTHROPIC_API_KEY` (or `GROQ_API_KEY`); without a key
the AI columns show a placeholder and nothing is charged.

## Docs

- [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md) — architecture, data flow, the
  prompts, and the rules the dashboard is built to obey.
- [`docs/HOW_TO_DEPLOY_DASHBOARD.md`](docs/HOW_TO_DEPLOY_DASHBOARD.md) — publish your
  own copy: hosting, Google Sheets for notes, sharing the link safely.
- [`docs/HOW_TO_UPDATE.md`](docs/HOW_TO_UPDATE.md) — maintenance checklist.
- [`AI_USAGE/AI_METHODOLOGY.md`](AI_USAGE/AI_METHODOLOGY.md) — a reusable playbook
  for building a project like this one with an AI agent.
- [`AI_USAGE/SKILLS_USED.md`](AI_USAGE/SKILLS_USED.md) — which agent skills were
  used here and what each contributed.
- [`FOR_CLAUDE.md`](FOR_CLAUDE.md) — **read this first when continuing this project
  in a new AI session**: conventions, decisions, structure rules, open tasks.

## Honesty about data

Uses the community `yc-oss/api` (open). Open-source deep-dive links only (no
Crunchbase/LinkedIn). Cap tables, funding, and valuations for private startups
don't exist publicly, so the tool never fabricates them; `investability` is an
honest status-derived heuristic.
