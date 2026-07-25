# IDEAS — the backlog

Proposals that were noticed while working but not requested. Nothing here is
scheduled: the owner decides what graduates into the plan. Each entry says what it
would give, what it would cost, and where it came from.

Format: `[status] Idea — value · cost · origin`, where status is
`open` (waiting for a decision), `declined` (decided against, with the reason) or
`done`.

---

## Reliability

- **[open] Data-contract checks after every run.** After File 1 / File 2, assert
  invariants on the produced dataset — row count within 90% of the previous run,
  required columns present, AI coverage ≥ 99%, one model, matching prompt version —
  and fail the workflow if they break. *Value: the only thing that catches **silent**
  breakage (a renamed source field, a half-empty rebuild). Cost: ~1 hour. Origin:
  the failure-alerting discussion; the owner chose the preflight only for now.*
- **[open] A data-health line in the dashboard.** `Data: 2026-07-25 · 4040
  companies · AI 100% · model claude-haiku-4-5`, written by the run into
  `data/last_run.json`, plus a gentle warning when the data is older than N months.
  *Value: the state is visible where the owner actually looks. Cost: ~1 hour.*
- **[open] Check-only scheduled workflow.** Weekly, changes nothing and spends
  nothing: pings the source, verifies the model still exists, opens an issue if not.
  *Value: you learn about a retired model before you need the data. Cost: ~40 min.
  Conflicts with the "no schedules" rule — that is why it is only an idea.*

## The dashboard

- **[open] "What changed since the last run".** A view comparing the newest dataset
  with the previous one: companies added, statuses changed, scores moved. *Value:
  turns a refresh into news instead of a bigger table. Cost: ~2 hours.*
- **[open] Saved filters / shareable links.** Name a filter combination, get a URL
  that restores it. *Value: repeat scouting sessions stop being re-typed. Cost:
  ~1.5 hours (the selection already travels in the URL).*
- **[open] Notes digest export.** One document with every favourite: card, notes,
  tags, stage — as Markdown or Excel. *Value: the shortlist becomes something you
  can send someone. Cost: ~1 hour.*
- **[open] Highlight the search term** inside descriptions in the card list.
  *Value: you see why a company matched. Cost: ~30 min.*

## Performance (measured, postponed by the owner)

- **[open] Cache the Overview charts by a filter hash.** ≈ 0.36 s per rerun — the
  largest single item. *Cost: ~30 min.*
- **[open] Render only the active tab.** ≈ 0.4 s per rerun, at the cost of tab
  switching becoming a server round-trip (~0.3 s instead of instant). *Cost: ~2
  hours, touches navigation.*
- **[declined] Paginate the bulk notes editor.** Measured 1.06 s → 1.12 s, i.e. no
  effect, and it would cost the ability to edit many companies at once. Reverted.

## Beyond this project

- **[open] Phase 2: a standalone website.** The dataset is already a clean data
  contract (Parquet/JSON with `score`, `investability`, `ai_*` precomputed), so a
  static front-end could be built on top without touching the pipeline. *The owner
  decided: not this time.*
