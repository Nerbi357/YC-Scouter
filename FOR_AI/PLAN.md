# PLAN — YC Scouter

The living plan: what is done, what is in flight, what was deliberately postponed.
Updated in the same pass as the work. History and reasoning live in
[`PROJECT_MEMORY.md`](PROJECT_MEMORY.md); the rules of engagement live in
[`AI_INSTRUCTIONS.md`](AI_INSTRUCTIONS.md).

**Definition of done for every phase (all four):** the result exists and is
demonstrable · tests pass and cover what the phase introduced · a checklist of what
went in and what was postponed · the owner's explicit approval.

---

## Phase 1 — Pipeline and data — **done**

Goal: collect every YC company from 2020 to now and enrich it with an LLM, cheaply
and repeatably.

- [x] File 1 collects the full Base into dated Parquet + Excel
- [x] File 2 adds `ai_description` + `ai_risks`, paying only for new companies
- [x] Cache keyed `(id, model_id, prompt_version)`; a full run measured ≈ $7.14
- [x] Two manual GitHub Actions buttons, no schedule
- [x] Current dataset: **4040 companies**, 100% AI coverage, one model

## Phase 2 — Dashboard — **done**

Goal: browse, filter, compare and annotate the dataset from any browser.

- [x] Four tabs, rich filters, charts, comparison, export (CSV/Excel/Parquet)
- [x] Personal notes keyed by the immutable company id
- [x] Owner notes in a Google Sheet; visitors isolated in both directions
- [x] Deployed and public: https://nerbi357-yc-scouter.streamlit.app/

## Phase 3 — Robustness — **done**

Goal: the dashboard must not break on imperfect data, a failing store, or a stranger.

- [x] All confirmed **critical** audit findings closed (10 of them — see
      `PROJECT_MEMORY.md` §9), each with a regression test
- [x] A failed store read can never erase notes; access fails closed
- [x] Imperfect datasets degrade instead of crashing
- [x] Preflight before spending: key, credits and model id checked up front
- [x] 161 tests, ruff clean, verified in a real browser on the real dataset

## Phase 4 — Structure, documentation and language — **done**

Goal: a repository a stranger can read and an agent can resume.

- [x] Root reduced to blocks plus mandatory files; `DOCS/`, `AI_USAGE/`, `FOR_AI/`
- [x] Everything in English, including the dashboard UI
- [x] `DOCS/HOW_IT_WORKS.md`, `HOW_TO_DEPLOY_DASHBOARD.md`, `HOW_TO_UPDATE.md`
- [x] `FOR_AI/AI_INSTRUCTIONS.md` — portable rules for working with the owner
- [x] `FOR_AI/PROJECT_MEMORY.md` + this plan
- [ ] `AI_USAGE/AI_METHODOLOGY.md` rewritten around this project's real prompts
- [ ] Final `README.md` + `README.ru.md` (Russian version, linked from the English one)

Deliberately postponed: renaming `FOR_AI/PROJECT_MEMORY.md` (the name is easy to
change if the owner prefers another); the `.claude/` folder name cannot change — the
harness finds it by path.

## Phase 5 — Full audit — **next**

Goal: find what the first audit's confirmed-critical pass did not cover.

- [ ] Re-run the adversarial audit with several agents and different lenses
      (correctness, data integrity, access, resilience, UX)
- [ ] Reproduce every candidate finding before fixing anything
- [ ] Fix by blast radius; each fix lands with a test that fails without it
- [ ] Report what was found, what was fixed, and what was consciously left

## Phase 6 — Performance — **postponed by the owner**

Measured by ablation on the real dataset; do not redo the parts marked as measured.

- [ ] Cache the Overview charts by a filter hash (≈ 0.36 s per rerun — the largest)
- [ ] Consider rendering only the active tab (≈ 0.4 s, at the cost of tab switching
      becoming a server round-trip)
- [x] ~~Paginate the bulk notes editor~~ — **tried and reverted**: 1.06 s → 1.12 s,
      i.e. no effect. Do not retry.

## Not doing (and why)

- **A full website (phase 2 of the original idea)** — the owner decided not this
  time; the dataset is already a clean contract if it comes back.
- **A scheduled data refresh** — updates stay manual on purpose: predictable, no
  silent spending, nothing breaks while nobody is watching.
- **A separate "File 5" deployment notebook** — `app.py` plus
  `DOCS/HOW_TO_DEPLOY_DASHBOARD.md` already fill that role.
- **Data-contract checks and a data-health line in the dashboard** — proposed as
  failure alerting, the owner chose the preflight only for now.
