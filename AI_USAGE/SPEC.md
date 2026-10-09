# PRODUCT SPEC — Scouter v2

> **What this is.** The target state of the product, written so that an executing
> agent (or a team) can build it without re-deriving decisions, and so that the owner
> can say *yes* or *no* to each part and edit it over time. It was distilled from a
> structured interview with the owner on 2026-10-09; his answers are the source of
> every requirement here, and the places where he said "discuss" are marked
> **⚖ decision** rather than silently decided.
>
> **How to use it.** Read §1–§4 to know what is being built and for whom. §5–§9 say
> what and how. §10–§13 say how the work runs. §14 is the roadmap. §15 lists what is
> still open. When something changes, change it here first — this file outranks
> `PLAN.md`, which now tracks execution against it.
>
> **Status:** draft for the owner's review. Nothing in it is approved yet.

---

## 1. Vision

**One place where an analyst can see every early-stage company that has surfaced
anywhere, everything publicly knowable about each one — and where every number can be
traced to its source and its date.**

Not a bigger Crunchbase. The layer *before* the databases: companies at the moment
they first appear — in an accelerator batch, on a launch board, in a grant list, in a
filing — followed from there, with the path recorded (accelerator X → Y → acquired).

### The scene the product is built for

An analyst at a seed fund opens the site before a call. She types the company's name.
The profile shows what it does, who backed it, a timeline of everything that has
happened to it that is publicly recorded — first appearance, batch, filings, launches,
hires, press — each line carrying the source it came from. She checks two numbers
against their sources in one click each. She adds the company to her watchlist and
leaves a note. Next week a Telegram message tells her the company filed a Form D.

A manager uses the same profile for ten minutes of preparation before negotiations. A
visitor with no account uses the market map to see what is being built in space tech
this year and which companies exist in it — and understands, without being told,
that every figure on the page can be checked.

The owner can audit any figure on the site against the raw record it came from.

---

## 2. Users and their jobs

| User | Job | Sharpest pains (owner's ranking) |
|---|---|---|
| **Fund analyst** (any fund type) | find companies a database does not have yet; understand one company fast; track a hundred without missing an event | find · understand · track |
| **Fund manager / partner** | ten minutes of preparation before a call | understand |
| **Outside visitor** (no account) | see what a market looks like; which companies exist in it; read about a few | explore |
| **Owner** | run the product; verify any figure; feed it to colleagues at a fund | audit · operate |

Everything else — reporting to LPs, sharing inside a team — is **later**.

### What the owner does with the current tool, honestly

He used it a couple of times to filter by sector, read a description and leave for the
company's own site. He stopped because (1) it holds only YC and (2) there is little
useful information beyond the links. The new product must be judged against that
bar: **if the only useful thing is still the outbound link, it has failed.**

---

## 3. Definition of done for v1

v1 is done when **all** of the following are true:

1. **A fund uses it.** At least one fund (≤10 people) works in it without payment —
   the owner's own fund or colleagues'. Measured by: a watchlist with real companies,
   notes written by someone other than the owner, alerts received.
2. **A manager's verdict.** The fund's managing partner has used it and the owner has
   recorded his reaction verbatim — whatever it is.
3. **The analyst test (the owner's words):** the site gives *more* data and
   information than an ordinary analyst can gather by hand — both in finding
   companies (building a funnel) and in information about each (moving through it).
   Measured by a side-by-side on 20 companies: what the site shows vs. what an analyst
   finds in an hour.
4. **Every figure is traceable.** No number appears without a source and a date.
   Verified by an automated check over the rendered views, not by inspection.
5. **It can be linked to.** A public URL the owner is proud to put in a portfolio.

**Not required for done:** payment, more than one fund, mobile-first, the social
layer, CIS markets.

---

## 4. Scope

### In v1

- Company profiles with a **timeline of events**, each with provenance.
- **Market map** as the home screen: segments, years, counts, movement — plus search.
- Search and filters (sector, stage, status, year, source/accelerator, country).
- **Watchlist**, personal **notes**, **compare** (up to five).
- **Alerts**: Telegram and in-app, on watchlist events.
- **Accounts** for up to ten users of one fund; notes are personal.
- **Public part**: profiles and the market map are visible without an account;
  watchlist, notes and alerts require one.
- AI description **on request** (not by default), expanded into a fuller, clearer
  summary than today's, always labelled as generated.
- Markets: **US accelerators and well-known global ones** first (YC, Techstars, 500,
  Antler, EF, Seedcamp…), then Europe. **English everywhere.**
- Weekly refresh, automated; a path to daily.

### Later (owner's "yes, but not now")

Export, API, MCP server, PDF memo, shared team notes, SSO, mobile-first, more
markets (Kazakhstan, CIS), startup-authored posts, affiliated-person feeds.

### Never, or not without a separate decision

- Paid tiers (the product is free).
- Inventing a figure the source does not publish — valuations, revenue estimates.
- Profiles of **people**. v1 shows companies; a person's name appears only as part of
  an official record (a filing, a press release) and never as a page of its own.
  Revisited with legal advice before any CIS market (152-ФЗ) or EU data (GDPR).
- Paywalled or credentialed sources (Crunchbase, PitchBook, LinkedIn).

### Proposed out-of-scope for v1 (owner said "discuss" — **⚖ decision**)

1. Any market outside US/global accelerators.
2. Any social feature beyond personal notes.
3. Any data that requires a human to confirm *every* row.

---

## 5. Why this and not Tracxn (differentiation — **⚖ decision**, owner asked for options)

| Angle | What it means | How defensible |
|---|---|---|
| **1. Provenance first** | every number is a link to its source and a date; the UI refuses to render a figure without one | strong — incumbents show numbers, not receipts |
| **2. Coverage honesty** | "this source does not cover this company" is a visible state, never a blank | strong, cheap, rare |
| **3. The earliest layer** | companies at the point of first appearance — batch, launch, grant, filing — before they exist in paid databases | strong, and it is what seed analysts actually lack |
| **4. Timeline as the object** | the profile is a path (X → Y → acquired), not a snapshot | medium — others have timelines, few build around them |
| **5. Open and reproducible** | the pipeline and the dataset are public; anyone can rerun the numbers | strong for trust, unusual in the category |
| **6. Free** | no tier, no seat price | strong for adoption, weak as a moat |
| **7. Affiliated-person feed** | posts by a CEO/CFO on the profile | **not recommended for v1** — personal data, fragile sources, low defensibility |

**Recommendation:** build v1 around **1 + 2 + 3**, make 4 the visible form of it, and
let 5 and 6 be the stance rather than features. If Tracxn became free tomorrow, 1–3
would still be missing from it.

---

## 6. Data

### 6.1 Object model

```
Source      id, title, url, terms, covers[], cadence, health
Company     company_id, canonical name, domain, country, sector, first_seen (date + source)
Identity    company_id ↔ {domain, name_key, CIK, registry number, GitHub org, …}
Fact        (company_id, field, value, value_num, observed_at, last_seen, source, source_url, confidence)
Event       a fact whose field is an event type: first_seen, batch_joined, filing, launch,
            hire_wave, press, status_change, acquired, closed — with a date and a source
Coverage    (company_id, source) → covered | uncovered
Note        (user_id, company_id, text, updated_at)        — private
Watch       (user_id, company_id, since)                   — private
Alert       (user_id, event_id, channel, delivered_at)
```

The facts table already exists (`src/yc_scouter/facts.py`) and is **long, not wide**:
a new source is an insert, never a migration. Events are facts with an event field;
the timeline is the company's events sorted by date.

### 6.2 Priorities (owner's ranking)

**Tier 1** — existence and description · financials (revenue, profit where public) ·
rounds and investors · news and mentions.
**Tier 2** — team and hiring · product, registrations, patents · own notes and status.

A company may be shown with only a name and a sector, **with the coverage state
visible** (owner's choice D2-a).

### 6.3 Quality rules — the ones that come from "the worst thing is a wrong figure"

1. **No figure without a source and a date.** Enforced in the view layer: a value
   without `source_url` and `observed_at` does not render.
2. **Confidence travels with the value**: `verified` (official record) · `reported`
   (secondary) · `derived` (ours, e.g. `custom_score`) · `generated` (AI). Visible,
   not hidden in a tooltip.
3. **Two sources may disagree; both are shown.** The product never averages them.
4. **Uncovered ≠ empty.** The coverage matrix is rendered, not implied.
5. **Entity resolution never guesses.** Below the confidence threshold, candidates go
   to a review queue; the owner (a few hours a week, by his own estimate) confirms.
6. **Derived numbers are labelled as ours** (`custom_score` already is) and carry
   their method.
7. **Cross-source consistency checks run on every refresh** — e.g. a company marked
   acquired by one source and hiring by another is flagged, not silently shown.
8. **A data-contract check gates every refresh**: row counts within tolerance,
   required fields present, no source with 100% errors. A failing contract blocks the
   publish and notifies the owner.

### 6.4 Legal policy — **⚖ decision, with a recommendation the owner should read**

The owner chose "everything technically accessible" (D4-c). **Recommendation: do not.**
For a product meant as a portfolio piece and a tool inside a fund, the exposure is
reputational, not only legal. The policy proposed instead:

- **Tier A — official APIs and open data**: use freely (SEC, Companies House, GDELT,
  HN, Wayback, SBIR, CORDIS, yc-oss).
- **Tier B — public pages without an API**: fetch politely (robots.txt, identified
  user agent, rate limits), store facts extracted, **never republish the page or the
  dataset wholesale**, and record the terms next to the source.
- **Tier C — paywalled, credentialed, or explicitly "no automated access"**: never.
- **Per-source terms live in the registry** (`sources/`), and a source whose terms
  forbid the product's use is not registered.
- Product Hunt's API forbids commercial use; the product is free, so it is usable —
  recorded as a condition that changes if the product ever charges.

### 6.5 Freshness

Weekly in v1, automated (GitHub Actions, free for a public repository); daily as the
sources and the budget allow. **The owner's manual cadence produced zero refreshes in
ten weeks** — the plan no longer depends on it. Every refresh is idempotent (an
unchanged source adds no rows) and gated by the contract check.

### 6.6 Storage — **⚖ decision**

| Option | Cost | Fits | Risk |
|---|---|---|---|
| Git repository | $0 | code and small tables | 1 GB ceiling, every data push redeploys |
| **GitHub Releases assets** | $0 | dated archives | manual to browse, fine for machines |
| **Cloudflare R2** | $0 up to 10 GB, no egress fee | serving JSON to the site directly | account setup |
| Google Drive | $0 | nothing automated well | fragile for pipelines |
| Local disk | $0 | not a product | not a product |

**Recommendation:** code in git; the facts table and its dated archives in **R2**
(read by the site) with a mirror on **GitHub Releases**; the public dataset also
published to Hugging Face for trust and reuse. Fits the $10/month ceiling with room.

---

## 7. Sources for v1

Split into **rosters** (who exists) and **enrichers** (what happened), as in
`SOURCE_RESEARCH.md`. Confidence marks there apply; everything below is to be verified
from Actions, not from the agent sandbox.

### Rosters, in order

| Source | Status | How |
|---|---|---|
| YC (yc-oss) | in production | API |
| Techstars, 500, Antler, EF, Seedcamp, Alchemist, HAX | **to build** | curated lists + Tier-B fetch of portfolio pages, one module each, terms recorded |
| Hacker News "Launch HN" / "Show HN" | to build | Algolia API — *first appearance* events |
| Product Hunt launches | to build | API, non-commercial condition |
| SBIR / CORDIS | to build | open data — rosters *and* money |
| GitHub trending orgs | later | API |

### Enrichers, in order

| Source | Gives | Status |
|---|---|---|
| SEC EDGAR Form D | filings with dates and amounts | spike built; **blocked until `SEC_USER_AGENT` is set**; then measure coverage |
| GDELT | news mentions | to build |
| Hacker News | mentions, launches | to build |
| Wayback CDX | site history without storing it | to build |
| GitHub | code activity | to build |
| Companies House | UK filings | when Europe opens |
| Careers pages | hiring volume | to build, Tier B |

### Market phasing

1. US accelerators + global (above). 2. Europe (Companies House, EU registries).
3. Kazakhstan, CIS — **only after** the legal section is revisited.

---

## 8. Product

Design bar (owner): **Apple / sequoiacap.com** — typographic, quiet, generous space,
no dashboard chrome. Mobile must open and be usable; desktop is primary.

### 8.1 Screens

**Home — the market map** *(public)*

```
┌────────────────────────────────────────────────────────────────────┐
│  Scouter                                   Search ▭    Sign in     │
│                                                                    │
│  What early-stage companies are building                          │
│  3 sources · 4,800 companies · updated 2026-10-06                  │
│                                                                    │
│  [ Sector ▾ ] [ Year ▾ ] [ Source ▾ ] [ Country ▾ ]                │
│                                                                    │
│  ┌──────────── treemap / bars by sector, size = companies ───────┐ │
│  │  B2B ████████████  Fintech ██████  Health █████  Space ██      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  Movement this month        New this month        Most active     │
│  ▸ 12 status changes        ▸ 38 companies        ▸ 5 filings     │
│                                                                    │
│  ▸ every figure on this page links to its source                   │
└────────────────────────────────────────────────────────────────────┘
```

**Search / list** *(public)* — filters left, results as compact rows: name, one line,
sector, first seen (source), latest event. Row click → profile.

**Company profile** *(public; notes and watch need an account)*

```
┌────────────────────────────────────────────────────────────────────┐
│  ← back                                        ☆ Watch   ✎ Note   │
│                                                                    │
│  Genecis Bio                                                       │
│  Makes guilt-free plastics from food waste                         │
│  Industrials · Winter 2020 · Toronto · Active        coverage ●●○○ │
│                                                                    │
│  Timeline                                                          │
│  2020-01  First seen — YC batch Winter 2020            [yc]        │
│  2021-06  Form D filed, offering $3.0M                 [sec]       │
│  2023-03  Launch HN, 212 points                        [hn]        │
│  2025-11  Hiring wave: 6 open roles                    [careers]   │
│  2026-07  Team size 30 → 47                            [yc]        │
│                                                                    │
│  Facts                                   Sources consulted         │
│  Team      47     yc · 2026-07-25        yc        ● covered       │
│  Status    Active yc · 2026-07-25        sec       ● covered       │
│  Funding   $3.0M  sec · 2021-06-12       gdelt     ○ not yet       │
│                                          github    ○ no public org │
│                                                                    │
│  ▸ Generate a description (AI, labelled)                           │
│  Links  Website · YC · Filing · News                               │
└────────────────────────────────────────────────────────────────────┘
```

Every value in *Facts* and every line in *Timeline* is a link to its source record.
The coverage column is the honesty feature — it is never hidden.

**Watchlist and feed** *(account)* — the user's companies, newest event first; a
toggle for Telegram delivery; each event links to the profile and the source.

**Compare** *(public)* — up to five profiles side by side, facts aligned by field,
provenance kept per cell.

### 8.2 Alerts

Telegram bot (free) and in-app. A scheduled job diffs the facts table after each
refresh and sends one message per watched company with new events. Nothing is sent
for facts without a source.

### 8.3 Accounts and privacy

Email + magic link (no passwords to leak). Up to ten users; notes and watchlists are
**personal**. No SSO in v1. Account deletion and export — later.

### 8.4 AI

Description on request only, generated from the company's own public text plus the
facts on file, labelled, cached per `(company, model, prompt version)` as today, with
the same preflight and cost cap. Never produces a number the sources do not hold.

### 8.5 The public part — explained (owner asked, F4)

"Public" means a visitor without an account can open it. The recommendation is that
**profiles, the market map, search and compare are public**, because that is what
makes the product linkable, findable and worth a portfolio; **watchlist, notes and
alerts are private**, because they are the user's own. Nothing private is ever shown
to another user. The alternative — everything behind a login — would make it
invisible, which conflicts with the portfolio goal.

---

## 9. Architecture and stack — **⚖ decision on the front-end**

### 9.1 Shape: static-first

```
sources ──► facts (long table) ──► views (precomputed JSON per company, per market)
                                        │
                      ┌─────────────────┴──────────────────┐
                      ▼                                    ▼
             public static site                 private slice: auth, notes,
             (profiles, map, search, compare)   watchlist, alerts
```

Everything public is **precomputed and served as files** — no server to attack, no
bill, fast on a phone. Only the private slice needs a store.

### 9.2 Three ways to build the front-end, and how hard each is for the owner

| Option | What it is | Design bar | Accounts | Difficulty to run alone |
|---|---|---|---|---|
| **A. Streamlit** (today) | Python pages | cannot reach it | hacky | trivial, already runs |
| **B. Static site + managed backend** ★ | Astro or Next (static export) on Cloudflare Pages; auth/notes/watchlist on Supabase or Cloudflare D1 + Workers; alerts from a scheduled job | fully reachable | proper | **moderate**: two free services, one deploy command, no servers to patch |
| **C. Full web app** | Next.js + Postgres on a small VPS or Fly.io | fully reachable | proper | **hard** alone: a server to keep alive, backups, upgrades |

**Recommendation: B.** It meets the design bar, costs $0–5/month, and the owner can
redeploy it with one command. Streamlit stays as the **training ground** (owner's
earlier decision) for trying ideas before they reach the site.

The agent builds B; the owner needs to create two free accounts (Cloudflare,
Supabase) and paste two secrets. That is the whole operational burden.

### 9.3 Costs within the $10/month ceiling

Cloudflare Pages $0 · R2 $0 (≤10 GB) · Supabase free (auth, 500 MB) · GitHub Actions
$0 (public repo) · Telegram Bot API $0 · AI descriptions on request ≈ cents.
**Expected: $0/month; ceiling respected with a margin.** The one risk: Supabase free
projects pause after 7 days without activity — a weekly refresh job that touches the
database keeps it alive, and it is written as a requirement.

### 9.4 Repository layout

The current repository stays the pipeline and the training ground. The site is a
second folder (`site/`) in the same repository until the product is real, then a
decision on splitting. Data leaves the repository for R2 (§6.6).

---

## 10. Pipeline and automation

- **Scheduled** weekly run (Actions): rosters → identities → enrichers → facts →
  contract check → views → publish to R2 → alerts. Each stage idempotent.
- **Preflight** per source (as File 2 has today): fail before spending; one probe per
  service; a blocked source is reported, never counted as "no data" (the Form D
  lesson).
- **Entity resolution** with a review queue; unresolved candidates never merge.
- **Measurement before building**: every new source starts as a coverage spike on a
  sample, and the number goes in `PLAN.md` whether it is good or bad.
- **Observability**: a status page (per-source freshness and health, last run, row
  counts) generated with the views — the owner must never again have to guess whether
  the product is up.

---

## 11. Quality and verification

The owner wants to make conceptual decisions only. That requires the machinery to
catch everything else:

- **Tests first** (already the habit): unit tests per module, contract tests per
  source, view tests that assert "no figure without a source".
- **CI on every push**: tests, lint, format, a build of the site, and a link check —
  currently absent and required.
- **Data-quality tests on real data**: run against the facts table after each refresh
  (consistency rules of §6.3), failing the publish on violation.
- **Browser checks** on the built site against the real dataset (Playwright), on a
  phone viewport too.
- **An independent reviewer agent** (`.claude/agents/`), run at every milestone: reads
  the spec, attacks the build, reports gaps and proposes improvements. Finder and
  verifier are never the same agent.
- **Measured negatives are results**: a source that does not cover enough is closed
  honestly and recorded.

---

## 12. Non-functional requirements

| Requirement | v1 bar |
|---|---|
| **Correctness over uptime** (owner, I1) | a wrong figure is a release-blocking bug; an hour of downtime is not |
| Freshness | weekly, automated; the date is shown on every page |
| Performance | public pages are static: first paint < 2 s on mobile |
| Mobile | opens and is usable; not primary |
| Security | no secrets in the repository; magic-link auth; private data never in public JSON; hostile-input pass before accounts open |
| Privacy | no person profiles; no personal data beyond what an official record contains; revisit before CIS/EU |
| Observability | status page with per-source health |
| Reproducibility | pipeline and dataset public; environment pinned |
| Cost | ≤ $10/month, expected $0 |

---

## 13. Roles and operating model

- **Owner** (≈20 h/week): product decisions, acceptance of each milestone, review-queue
  confirmations, the fund relationship. Does not write code.
- **Builder agent**: implements against this spec, tests first, one branch per
  milestone merged into `main` after checks.
- **Reviewer agent**: independent, adversarial, at every milestone; its findings are
  recorded with verdicts.
- **Cadence**: a milestone is proposed with its acceptance criteria → built → reviewed
  → the owner accepts or sends back. Nothing depends on the owner remembering to
  press a button: refresh and alerts are scheduled.

---

## 14. Roadmap — milestones with acceptance

Epochs follow the living-project shape; the first three are ordered, the rest are
chosen, not queued.

| # | Milestone | Produces | Accepted when |
|---|---|---|---|
| **M0** | Unblock and measure | `SEC_USER_AGENT` set; Form D coverage number; CI on every push; scheduled weekly refresh for YC into facts | the number is in `PLAN.md`; CI is green on `main`; a refresh ran unattended |
| **M1** | Views and the first profile | precomputed JSON views; the company profile with timeline and provenance rendered as a static page | 20 real companies render; every figure links to a source; mobile usable |
| **M2** | The market map and search | home screen, filters, list, compare | a stranger understands the home page in twenty seconds (tested on two people) |
| **M3** | Rosters beyond YC | three accelerators + HN launches, each with terms recorded; identity resolution with review queue | companies from ≥ 2 rosters show a path; no wrong merge in a 50-company audit |
| **M4** | Enrichers | Form D events, GDELT, HN, Wayback, careers | timelines carry events from ≥ 3 sources on ≥ 30% of companies (measured) |
| **M5** | Accounts, watchlist, notes, alerts | magic link, personal data, Telegram bot | a colleague's note survives a refresh; an alert arrives within a day of an event |
| **M6** | The analyst test | 20 companies, site vs. one hour of an analyst | the site wins on ≥ 15 of 20, documented |
| **M7** | Pilot | the fund uses it; the partner's verdict recorded | §3 definition of done |

Design work (references, typography, the map) starts at M1 and runs alongside.

---

## 15. Open decisions (owner to settle; blocking ones first)

1. **⚖ Front-end option** — A/B/C (§9.2). Recommended B. *Blocks M1.*
2. **⚖ Legal policy** — Tier A/B/C (§6.4) instead of "everything accessible". *Blocks M3.*
3. **⚖ Storage** — R2 + Releases (§6.6). *Blocks M0's refresh job.*
4. **⚖ Name.** "YC Scouter" no longer describes the product. Working name here is
   *Scouter*; the owner names it.
5. **⚖ Differentiation** — confirm 1+2+3 (§5).
6. **⚖ Out-of-scope list** (§4) — confirm or edit.
7. **Design references** — the owner sends 3–5 links to screens he likes and 2 he
   dislikes, one line each on why. Needed by M1.
8. **Person data** — confirm "no person profiles in v1" (§4, §12).

---

## 16. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| A roster page changes shape | a source silently returns nothing | contract check fails the publish; status page shows it |
| A wrong merge reaches the site | the one failure the owner named as unacceptable | threshold + review queue; audit of 50 before each milestone |
| Free-tier services pause or change terms | downtime or migration | static public part never depends on them; private slice is small and portable |
| The owner's hours drop | the project stalls again | nothing scheduled depends on him; milestones are small and independently valuable |
| Sources forbid the use | legal/reputational exposure | Tier policy; terms recorded per source; no republishing |
| AI text drifts into claims | wrong "facts" | on request only, labelled, number-free by prompt and by check |

---

## 17. Glossary

**Roster** — a source that says a company exists. **Enricher** — a source that says
what happened to it. **Fact** — one observation with provenance. **Event** — a fact
with a date that belongs on a timeline. **Coverage** — whether a source was consulted
for a company. **View** — a precomputed answer the site renders. **Tier A/B/C** — the
legal classes of sources (§6.4).
