# YC Scouter

**A personal scouting tool for Y Combinator companies from 2020 to today.**
It collects every company YC publishes, adds honest derived signals, asks a language
model for a short factual description and a couple of concrete risks per company,
and serves all of it as an interactive dashboard you can filter, chart, compare and
annotate.

> 🔗 **Live dashboard — [nerbi357-yc-scouter.streamlit.app](https://nerbi357-yc-scouter.streamlit.app/)**
> · 🌐 [README.ru.md](README.ru.md)

**Several thousand companies** · batches 2020–2026 · every one of them carrying an AI
description and risks · rebuilt on demand by pressing two buttons.

---

## What it does

- **Finds** — filter by industry and subindustry, YC status, investability, batch
  year, team size, score, your own funnel stage and tags, or search across names,
  ideas, descriptions and your notes.
- **Explains** — every company card carries YC's own one-liner, a 6–7 sentence AI
  description, 1–2 concrete risks worth checking, and links to open sources only
  (site, YC profile, news, Product Hunt, Hacker News, GitHub, Wikipedia).
- **Compares** — up to five companies side by side.
- **Remembers** — favourites, tags, a personal funnel stage and free-text notes,
  stored outside the app so a data refresh never touches them.
- **Exports** — the filtered selection as CSV, Excel or Parquet.
- **Stays honest** — see [Honesty about data](#honesty-about-data).

## How it works

```
File 1  collect  →  dated Base dataset   (free, repeatable, no keys)
File 2  enrich   →  dated AI dataset     (costs money, resumable, cached)
app.py  read     →  the dashboard        (never fetches, never pays)
```

- **File 1** — `notebooks/01_dataset_base.ipynb`: pulls every YC company from the
  open [`yc-oss/api`](https://yc-oss.github.io/api/companies/all.json), normalises
  it, adds `investability`, deep-dive links and a 0–100 score, and writes
  `yc_dataset_base_<date>.parquet` + `.xlsx`.
- **File 2** — `notebooks/02_ai_summary.ipynb`: adds `ai_description` and `ai_risks`
  with **Claude by Anthropic** (Groq optional), writing
  `yc_dataset_ai_<date>.parquet` + `.xlsx`. Results are cached per
  `(company, model, prompt version)`: the full run of 2026-07-24 cost **$7.14** for
  ~4,000 companies, and the refresh a day later cost **half a cent** for the 3 new
  ones. It checks the key, the credit balance and the model **before**
  spending anything.
- **Dashboard** — `app.py`: a Streamlit app that reads the newest dated dataset.
- **Two buttons** — GitHub Actions run File 1 and File 2 on demand. There is no
  schedule on purpose: nothing changes and nothing is spent unless you ask.

Full architecture, the prompts and the design rules:
[`DOCS/HOW_IT_WORKS.md`](DOCS/HOW_IT_WORKS.md).

## Repository map

| Path | What it is |
|---|---|
| `app.py` | the dashboard — the only thing you run |
| `src/yc_scouter/` | all the logic; the notebooks, CI and the app import it |
| `src/tests/` | the test suite; network and LLM mocked, so a run never costs anything |
| `notebooks/` | File 1 and File 2 — thin wrappers over the package |
| `data/` | dated datasets (Parquet + Excel) and the AI cache |
| `DOCS/` | documentation for people (see below) |
| `AI_USAGE/` | working files for the AI agent: instructions, project memory, idea backlog |
| `.github/workflows/` | the two update buttons |
| `.streamlit/` | dashboard config + a secrets template |
| `.claude/` | agent configuration used while building (skills, roles, session setup) |

## Quick start

```bash
pip install -r requirements.txt --require-hashes    # pinned + hashed lockfile
streamlit run app.py                                # the dashboard
pytest                                              # the test suite
```

Run the pipeline through the notebooks (Colab or `papermill`) or through the two
GitHub Actions workflows. The AI step needs `ANTHROPIC_API_KEY` (or `GROQ_API_KEY`);
without a key the AI columns show a placeholder and nothing is charged.

Deploying your own copy — hosting, notes that survive restarts, sharing the link
safely: [`DOCS/HOW_TO_DEPLOY_DASHBOARD.md`](DOCS/HOW_TO_DEPLOY_DASHBOARD.md).

## Documentation

- [`DOCS/HOW_IT_WORKS.md`](DOCS/HOW_IT_WORKS.md) — architecture, the data source and
  derived fields, the prompts and their cost controls, the reproducibility
  contract, and the rules the dashboard is built to obey.
- [`DOCS/HOW_TO_DEPLOY_DASHBOARD.md`](DOCS/HOW_TO_DEPLOY_DASHBOARD.md) — publish your
  own copy, step by step, from zero.
- [`DOCS/HOW_TO_UPDATE.md`](DOCS/HOW_TO_UPDATE.md) — the maintenance checklist: the
  two buttons, keys, models, dependencies, what breaks and what to do.
- [`AI_USAGE/PROJECT_MEMORY.md`](AI_USAGE/PROJECT_MEMORY.md) — **start here when
  continuing this project with an AI agent**: decisions and their reasons, current
  state, open tasks. Next to it,
  [`AI_INSTRUCTIONS.md`](AI_USAGE/AI_INSTRUCTIONS.md) (how that agent is expected to
  work) and [`IDEAS.md`](AI_USAGE/IDEAS.md) (proposals not yet scheduled).

## Honesty about data

The source is the community mirror `yc-oss/api` — open, no key, rebuilt daily. Every
deep-dive link points at a freely accessible page; there are no Crunchbase or
LinkedIn links. Cap tables, funding rounds and valuations for private startups are
not published anywhere, so this tool never invents them: where a fact does not
exist, the cell stays empty and the card offers an open link instead.
`investability` is an honest status-derived heuristic, not a prediction. The AI
fields are generated **only** from the company's own published text.

Reproducibility here means *code*, not data: the environment is pinned to a hashed
lockfile, while the source legitimately changes between runs — so every run is
written to its own dated pair of files and previous results stay untouched.

## AI usage

This repository was produced with the assistance of **Claude by Anthropic**, used as
a coding agent. The author defined the requirements, made all product and
architectural decisions, and reviewed every change before it was merged. The agent
wrote implementation code, tests and documentation drafts under that direction.

Two dataset fields (`ai_description`, `ai_risks`) are generated by **Claude** from
public source text and are labelled as machine-generated wherever they appear; the
model, the prompts, the parameters and the cost controls are documented in
[`DOCS/HOW_IT_WORKS.md`](DOCS/HOW_IT_WORKS.md). Generated text may contain
inaccuracies inherited from the source, and no figure the source does not publish is
ever produced by the model.

The author is solely responsible for the final content of this repository. How the
agent was directed, verified and constrained is written down in
[`AI_USAGE/AI_INSTRUCTIONS.md`](AI_USAGE/AI_INSTRUCTIONS.md).

## License

[MIT](LICENSE).
