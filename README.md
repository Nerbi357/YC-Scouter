# YC Scouter

A personal tool to scout and analyze **Y Combinator companies from 2020 to now**.
It collects the public YC data, enriches it (investability heuristic, open-source
deep-dive links, an interestingness score), adds concise **AI descriptions + risks**
per company, and serves it in an interactive dashboard for filtering, charting,
comparing, and keeping a personal shortlist.

> 🔗 **Live dashboard:** **https://nerbi357-yc-scouter.streamlit.app/**
> (hosting details in [`docs/DEPLOY.md`](docs/DEPLOY.md)).

> Built with **[Claude Code](https://claude.com/claude-code)** using spec-driven,
> test-driven agent skills — see [`docs/AI_METHODOLOGY.md`](docs/AI_METHODOLOGY.md).

## What's inside

- **File 1** — `notebooks/01_dataset_base.ipynb`: scrapes all YC companies
  (2020→now) into a dated `yc_dataset_base_<date>.parquet` + `.xlsx`.
- **File 2** — `notebooks/02_ai_summary.ipynb`: adds `ai_description` + `ai_risks`
  (Claude by default, or Groq) into `yc_dataset_ai_<date>.parquet` + `.xlsx`, paying
  only for new companies (≈ $8–9 for a full run).
- **Dashboard** — `app.py`: a Streamlit app (Russian UI) reading the newest dated
  dataset; filters, charts, comparison, export, and personal notes.
- **Two buttons** — GitHub Actions rebuild the data on demand; no schedule.

## Quick start (local)

```bash
pip install -r requirements.txt --require-hashes    # or: pip install -e .
streamlit run app.py                                 # dashboard (after data exists)
pytest -q                                            # tests (network + LLM mocked)
```

Run the pipeline via the notebooks (Colab or `papermill`), or the two GitHub
Actions workflows. AI needs `ANTHROPIC_API_KEY` (or `GROQ_API_KEY`); without a key
the AI columns show a placeholder and nothing is charged.

## Docs

- [`SPEC.md`](Archive/SPEC.md) — the specification (source of truth).
- [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md) — architecture & implementation.
- [`docs/AI_METHODOLOGY.md`](docs/AI_METHODOLOGY.md) — the prompts + how it was built.
- [`docs/HOW_TO_UPDATE.md`](docs/HOW_TO_UPDATE.md) — maintenance checklist.
- [`docs/DEPLOY.md`](docs/DEPLOY.md) — hosting + Google Sheets + sharing.

## Honesty about data

Uses the community `yc-oss/api` (open). Open-source deep-dive links only (no
Crunchbase/LinkedIn). Cap tables, funding, and valuations for private startups
don't exist publicly, so the tool never fabricates them; `investability` is an
honest status-derived heuristic.
