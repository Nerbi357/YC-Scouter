# PLAN — YC Scouter

A working instrument for the phases still in flight. **It is deleted when the audit
closes**; whatever is still true by then moves into
[`PROJECT_MEMORY.md`](PROJECT_MEMORY.md). Rules of engagement:
[`AI_INSTRUCTIONS.md`](AI_INSTRUCTIONS.md). Unscheduled proposals:
[`IDEAS.md`](IDEAS.md).

**Definition of done for every phase (all four):** the result exists and is
demonstrable · tests pass and cover what the phase introduced · a checklist of what
went in and what was postponed · the owner's explicit approval.

---

## Phases 1–3 — pipeline, dashboard, robustness — **done**

Summarised in `PROJECT_MEMORY.md` §9: the two buttons, the full dataset with 100% AI
coverage, the deployed dashboard, all confirmed critical audit findings closed, the
preflight before spending, a green test suite.

## Phase 4 — structure, documentation, language — **done**

- [x] Root reduced to blocks plus mandatory files; `DOCS/`, `AI_USAGE/`
- [x] Everything in English, including the dashboard UI
- [x] `DOCS/`: how it works · how to deploy · how to update
- [x] `AI_USAGE/`: portable instructions · project memory · idea backlog
- [x] Final `README.md` + `README.ru.md` for Russian speakers

## Phase 5 — full audit — **awaiting approval**

Goal: find what the first pass (confirmed-critical only) did not cover, at every
severity, and close what matters.

- [x] Five lenses attacked the project in parallel: data correctness · access and
      privacy · resilience to hostile input · user flows · operations and
      documentation accuracy
- [x] Every candidate handed to a *different* agent to refute — 30 candidates,
      **9 confirmed** (2 high, 5 medium, 2 low), 21 refuted
- [x] All nine fixed, each with a test that fails without it, plus one more the
      browser check found while verifying (the ✕ never closed the card)
- [x] Verified: whole suite green, ruff, browser pass on the real dataset
- [ ] Owner reviews the report and approves the phase
- [ ] Delete this file and fold what remains into `PROJECT_MEMORY.md`

## Phase 6 — performance — **postponed by the owner**

Measured; see `IDEAS.md` for the two remaining options and the one that was tried
and reverted. Do not repeat the reverted experiment.

## Not doing (and why)

- **A standalone website** — the owner decided not this time.
- **A scheduled data refresh** — updates stay manual: predictable, no silent
  spending, nothing breaks unattended.
- **A separate "File 5" deployment notebook** — `app.py` plus
  `DOCS/HOW_TO_DEPLOY_DASHBOARD.md` fill that role.
