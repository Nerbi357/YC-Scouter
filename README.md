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

**In practice:** narrow the list to fintech companies from the last two batches that
are still hiring, open one, read the two risks worth checking before a call, tag it
`watch` and move to the next. **A dataset is committed to this repository**, so
`streamlit run app.py` works the moment you clone it — a key is needed only to
rebuild the data, never to look at it.

---

## What Y Combinator is

Y Combinator is a US startup accelerator that has funded companies at their earliest
stage since 2005 — Airbnb, Stripe, Dropbox, Coinbase and Reddit all went through it.
Every company gets the same standard deal (a fixed amount of money for a fixed share
of the company), joins a three-month **batch** named after the season it starts in —
Winter, Spring, Summer or Fall — and ends it at Demo Day, presenting to investors.

YC publishes its entire portfolio openly, and that is what makes this project
possible. But the directory is a *list*: nothing is ranked, two companies cannot be
put side by side, and there is nowhere to record what you thought about them. That is
the gap this tool fills.

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

## Quick start

```bash
pip install -r requirements.txt --require-hashes    # pinned + hashed lockfile
streamlit run app.py                                # the dashboard, on the committed data
pytest                                              # the test suite
```

Rebuilding the data is a separate, optional step: run the pipeline through the
notebooks (Colab or `papermill`) or through the two GitHub Actions workflows. Only
that step needs `ANTHROPIC_API_KEY` (or `GROQ_API_KEY`); without a key the AI columns
show a placeholder and nothing is charged.

Deploying your own copy — hosting, notes that survive restarts, sharing the link
safely: [`DOCS/HOW_TO_DEPLOY_DASHBOARD.md`](DOCS/HOW_TO_DEPLOY_DASHBOARD.md).

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

## Where everything lives

| Path | What it is |
|---|---|
| `app.py` | the dashboard — the only thing you run |
| `src/yc_scouter/` | all the logic; the notebooks, CI and the app import it |
| `src/tests/` | the test suite; network and LLM mocked, so a run never costs anything |
| `notebooks/` | File 1 and File 2 — thin wrappers over the package |
| `data/` | dated datasets (Parquet + Excel) and the AI cache |
| `DOCS/` | the three documents below |
| `AI_USAGE/` | working files for the AI agent: instructions, project memory, idea backlog |
| `.github/workflows/` | the two update buttons |
| `.streamlit/` | dashboard config + a secrets template |
| `.claude/` | agent configuration used while building (skills, roles, session setup) |

- [`HOW_IT_WORKS.md`](DOCS/HOW_IT_WORKS.md) — architecture, derived fields, the
  prompts and their cost controls, the reproducibility contract.
- [`HOW_TO_DEPLOY_DASHBOARD.md`](DOCS/HOW_TO_DEPLOY_DASHBOARD.md) — publish your own
  copy, step by step, from zero.
- [`HOW_TO_UPDATE.md`](DOCS/HOW_TO_UPDATE.md) — maintenance: the two buttons, keys,
  models, dependencies, what breaks and what to do.
- Continuing this project with an AI agent? Start from
  [`AI_USAGE/PROJECT_MEMORY.md`](AI_USAGE/PROJECT_MEMORY.md) — decisions and their
  reasons, current state, open tasks — next to
  [`AI_INSTRUCTIONS.md`](AI_USAGE/AI_INSTRUCTIONS.md) and
  [`IDEAS.md`](AI_USAGE/IDEAS.md).

## How to read the numbers

Some fields come from YC and some are this project's own. The card never mixes them
up, and neither does this table.

| Field | Where it comes from | What it means |
|---|---|---|
| `batch` | YC | The intake the company joined — a season and a year, e.g. *Winter 2020*. |
| `status` | YC | *Active*, *Inactive*, *Acquired* or *Public*. |
| `stage` | YC | A rough size marker: *Early* or *Growth*. |
| `top_company`, `is_hiring` | YC | YC's own flags, passed through untouched. |
| `investability` | **this project** | A plain reading of `status`: an active private company is reachable only through an accredited round, an SPV or a secondary sale; an acquired or inactive one is not investable at all. A statement about access — **not** a prediction and not advice. |
| `score` (0–100) | **this project** | A transparent weighted blend of cheap signals: YC's *top company* flag (weight 3), how recent the batch is (2), whether the company is hiring (1), team size (1), a substantive description (0.5) and how richly it is tagged (0.5). Deterministic, and retunable in [`src/yc_scouter/score.py`](src/yc_scouter/score.py). The scale is deliberately hard: in the run of 2026-07-25 the median was 23.4 and the highest score 72.9. |
| `ai_description`, `ai_risks` | **a language model** | 6–7 sentences and 1–2 risks worth checking, generated from the company's own published text and labelled as machine-generated everywhere they appear. |

## Honesty about data

- **Open sources only.** The data comes from the community mirror `yc-oss/api` (no
  key, rebuilt daily); every deep-dive link points at a freely accessible page.
- **Nothing is invented.** Funding, valuations and cap tables for private startups
  are not published anywhere, so no cell here contains them — an unknown fact stays
  empty and the card offers a link instead. The AI fields are written **only** from
  the company's own published text.
- **Reproducible code, not frozen data.** The environment is pinned to a hashed
  lockfile; the source legitimately changes between runs, so every run lands in its
  own dated pair of files and earlier ones stay untouched.

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
