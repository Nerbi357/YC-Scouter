# PLAN — YC Scouter v2 and beyond

> **Live document.** It is the map of the tree: the trunk, the branches that exist,
> the branches that could exist, and what must be agreed before each one opens.
> Read `AI_INSTRUCTIONS.md` and `PROJECT_MEMORY.md` first. The source study behind
> this plan is [`SOURCE_RESEARCH.md`](SOURCE_RESEARCH.md).
>
> Shaped with the **`living-project`** skill (`.claude/skills/living-project/`):
> build wide before deep, every step must make the next step cheaper, and a branch
> that fails is still a branch as long as the failure is published.

**Where the project stands:** v1.0 is released, deployed and finished. This plan
re-opens the working phase. v1.0 stays reachable by tag, and nothing in it gets
broken to make room for v2 — the pipeline it defines becomes *one source among many*.

---

## The one-sentence goal

**One place where the early-stage universe is visible — every fact carrying the
source it came from — usable by an investor as a working tool and by anyone else as
something genuinely interesting to poke at.**

---

## The architecture everything attaches to

Six layers. Each knows only the one below it. A new source, method, format or
audience attaches at exactly one layer and touches nothing else.

```
sources       every fetch stored as it arrived, with url, timestamp, content hash
identities    one company = one id; domain, CIK, Companies House no., GitHub org
facts         LONG, not wide: (company_id, field, value, observed_at, source, url, confidence)
derived       everything computed: scores, clusters, embeddings — each tagged with the method that made it
views         precomputed answers: a profile, a timeline, a theme map, a feed
presentation  Streamlit / static site / MCP / bot — reads views, never the layers below
```

**Two properties do the work.** The facts table is long, so **adding the eleventh
source is an insert, not a migration**. The derived layer records *which method*
produced each value, so a second scoring method sits beside the first instead of
replacing it — and the two can be compared.

**Three consequences that arrive for free** once this exists, rather than being three
separate features: the provenance line under every value, the company timeline, and
the coverage matrix that says "this source does not cover this company" instead of
showing a misleading blank.

---

## Epochs

Tasks are written only when an epoch opens. Everything after E2 is **deliberately
unordered** — the next branch is chosen, not queued.

### E0 — Foundation *(no visible change; everything later depends on it)*  ⏳ *first slice built 2026-07-27*

**Built so far:** `facts.py` (the long table with provenance), `identities.py` (the
one place that decides whether two records are one company), `sources/` (the
registry) with **YC as the first plugin**, and `pipeline.build_facts()`, which folds
the dated archive into history.

**Measured on the real archive**, replaying both dated datasets: **29,442 facts ·
4,040 companies · 0.13 MB**. A snapshot is ~6 MB, so the long table holds two days
of history in one fiftieth of the space of one day of snapshots — the storage
objection to a history dissolves at this shape. Ten companies changed between
2026-07-24 and 2026-07-25, and those changes are now visible as history rather than
as two files: *Notabene* Early → Growth, *Sota2* Consumer → B2B.

Replaying is idempotent: running it twice adds nothing, it only moves `last_seen`.

**Still to do in E0:** the dashboard reading through the new layers, and a contract
test per source.

**Produces:** the six layers as real modules; the existing YC pipeline rewritten as
**the first source plugin** with unchanged output; the facts table with provenance;
contract tests per source; the identity table with domain normalisation.

**Leaves out:** any new source, any UI change.

**Done when:** the current dashboard runs on the new layers with byte-identical
results, and adding a fake second source requires no edit outside its own module.

### E1 — The trunk: one enricher end to end *(SEC Form D)*  ⏳ *in progress*

**Agree before starting:** nothing — this is the naive version by design.

**Step 1 — the coverage spike (built 2026-07-27, waiting to be run).**
`src/yc_scouter/sec_edgar.py` + `notebooks/03_spike_formd_coverage.ipynb` + a third
Actions button. It looks up a deterministic sample of companies in EDGAR's company
search restricted to Form D and counts four outcomes: **matched** (one filer by that
name), **ambiguous** (several — never resolved by picking one), **none**, and
**error** (a failed request, which says nothing about the company). The report lands
in `data/spikes/formd_coverage_<date>.json`.

The result decides the branch: a high match rate justifies real entity resolution in
E2; a low one closes this branch honestly and the plan changes. **The number goes in
this file either way.**

**Run 1 (2026-08-04): no measurement — SEC refused every request with HTTP 403.**
200 of 200 rows came back as errors, which is *not* a statement about the companies.
The cause is our own: SEC asks automated clients to declare a contact address in the
User-Agent, and the default one names only the repository. Two fixes went in rather
than a retry: the refusal body is now captured (a status code is not a diagnosis),
and a single probe request decides whether the service will talk to us at all, so a
blocked run stops after one request and reports `status: blocked` instead of two
hundred identical failures that look like absence.

**To run it again:** set the repository secret `SEC_USER_AGENT` to something like
`YC-Scouter research (you@example.com)` and press the button. If it is still refused
with a declared contact, the browse-edgar CGI endpoint is the suspect and the JSON
full-text search at `efts.sec.gov` is the alternative to try next.

**Produces:** a measured match rate on a 200-company sample **published whether it is
good or bad**; Form D events in the facts table with links to the filings; the first
provenance line in the UI.

**Leaves out:** clever matching. Exact-name matching first, its failure rate reported,
and that failure is what motivates E2.

**Done when:** the number exists and is written down. If the match rate is very low,
this branch is *finished*, not failed — and the plan changes on the evidence.

### E2 — Do it properly

**Produces:** entity resolution with a confidence threshold and a review queue for
everything below it; a manual override table; the coverage matrix in the UI; per
source, a freshness and health line.

**Leaves out:** anything cosmetic.

**Done when:** no company page can show a fact from another company, and every empty
cell is distinguishable from an uncovered one.

### E3+ — Branches (unordered; each independently finishable)

| Branch | What it adds | Depends on | Definition of done |
|---|---|---|---|
| **Company profile page** | one URL per company: facts with provenance, a **timeline** on a slider, the AI text clearly labelled | E0, E1 | a stranger understands the company and where each fact came from, on a phone |
| **Theme map over time** | embeddings → clusters → how themes rise and fall across batches | E0 | someone finds a trend they did not expect and re-runs it with another filter |
| **MCP server** | the dataset queryable from any AI assistant | E0 | an analyst asks in their own words and gets rows with sources |
| **Telegram bot** *(deferred to v3)* | alerts, queries and a digest | E0 + one enricher | a subscription produces a message the owner actually wants |
| **More rosters** | curated accelerator lists; SBIR and CORDIS as rosters *and* money | E0 | each roster names its provenance and its update cadence |
| **News feed** | GDELT mentions per company, deduplicated | E0 | the feed is about *these* companies, with a measured false-positive rate |
| **Public static site** | precomputed JSON, no server, no bill | E0 + profile pages | twenty seconds to understand, one thing to touch immediately |
| **PDF memo** | one page per company, the artefact that gets forwarded | E1 | contains facts and sources, not prose |
| **Accounts and subscriptions** | follow companies, get a personal feed | site + a store | a hostile-input pass before it is public |
| **Startup-authored posts** | a company posts an update on its own page | accounts | moderation and identity decided *before* a line is written |

### En — v2.0

Full technical pass, an adversarial audit, the release, the changelog a stranger can
read, and the next set of branches proposed at the boundary.

---

## Decisions taken (2026-07-27)

1. **Two front-ends now, one site later.** Build them separately, then merge into a
   single site with **two viewing modes** — one for working, one for reading.
   **Streamlit stays as the training ground**: new ideas are tried there first and
   graduate to the site once they prove themselves. That reframes it from "the thing
   we will replace" to "where things are prototyped", and it is a better answer than
   the one proposed.
2. **Company profile pages with a timeline: approved, building now.**
3. **Telegram bot: deferred to the next version.** The immediate work is the
   extraction that would feed it anyway.
4. **Where the data lives: revisited next phase.** Until then the repository holds it.

## Still open

- ~~How a recurring refresh is implemented~~ — **settled 2026-07-27: it stays manual.**
  The owner presses the collect button himself, weekly. No schedule, nothing runs
  unattended, and the history accumulates at whatever pace he keeps.
- **How far into the social product to go.** A feed a visitor reads is a different
  commitment from accounts, subscriptions and user-generated posts, which bring
  moderation, identity and abuse handling with them.

---

## Cannot be done retroactively — start early

- **Snapshots of anything a source may drop.** Dated files already do this for YC;
  new sources must do it from their first run.
- **Wayback is the exception that saves us:** website history already exists and can
  be fetched later, so it is *not* urgent.
- **Own observations that exist only going forward** — job counts, code activity,
  press cadence. Every week not recorded is gone.
