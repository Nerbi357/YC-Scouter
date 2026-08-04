# SOURCE RESEARCH — what can be covered, for which companies, from where

> **Status:** working document for the v2 design (2026-07-27). It becomes
> `DOCS/DATA_SOURCES.md` when the sources actually ship; until then it lives here,
> next to the plan it feeds.

**Confidence marks used below — the same in every row:**

| Mark | Meaning |
|---|---|
| ✅ **verified** | read in current documentation during this research pass |
| 🟡 **reported** | stated by secondary write-ups, not read in the primary source |
| ⚪ **inference** | my reasoning from the above, not a fact anyone published |
| ⛔ **blocked** | could not be checked here — the sandbox's egress policy refuses
  `sec.gov`, `api.github.com`, `hn.algolia.com`. **A blocked check is not a negative
  result**; these must be re-run from Colab or Actions before anything is built on them. |

Nothing in this file is a measured coverage number. Every "how many companies would
this actually match" question is listed at the end as work to do, because guessing it
is exactly the failure mode this document exists to prevent.

---

## 1. The finding that reshapes the plan

**Only YC publishes a machine-readable portfolio.** Searching for equivalents at
Techstars, Antler and Entrepreneur First turns up portfolio *web pages* and
commercial aggregators (Tracxn, VCBacked, Crunchbase) — no official open API, no
published dataset. 🟡

That splits every source into two kinds, and the split is the architecture:

- **Rosters** — *which companies exist and who backed them.* Scarce, mostly not
  machine-readable, and the reason a "ten accelerators" plan is harder than it looks.
- **Enrichers** — *what happened to a company.* Keyed by **domain or legal name**, so
  they work for **any** company regardless of who accelerated it. Plentiful, free,
  official, and stable.

The valuable asset is the enricher layer. A roster is one CSV per accelerator; an
enricher works for every company the project will ever hold.

---

## 2. Rosters — who exists

| Source | Coverage | Access | Risk | Confidence |
|---|---|---|---|---|
| **YC via `yc-oss/api`** | the full YC portfolio | open JSON, no key | none — already in production | ✅ in use |
| **Techstars / Antler / EF / 500 / Seedcamp portfolio pages** | their portfolios | HTML only | **EU sui generis database right protects a substantial investment in compiling a database; systematically mirroring an entire catalogue is the risky end of the spectrum, while a modest extract is not.** robots.txt and ToS are what regulators look at first | 🟡 |
| **Manual curated CSV per accelerator** | whatever we choose to enter | ours | none | ⚪ |
| **SBIR/STTR awards** | US companies with federal R&D grants — *a roster in its own right*: 220,000+ awards since 1983 across 11 agencies, downloadable in bulk | free public API + bulk files | none | 🟡 |
| **CORDIS (EU research projects)** | EU-funded projects and participants | EC open data, no key | none | 🟡 |

**The honest read:** for accelerators other than YC, the choice is between fragile
scraping with a legal grey zone, and small curated lists with visible provenance.
Curated lists are slower but they never break, never mislead, and can be published.
SBIR and CORDIS are the interesting surprise — they are rosters *and* money data, and
they cover deep tech, which YC under-represents.

---

## 3. Enrichers — what happened

| Source | What it gives | Whose companies | Access | Limits | Confidence |
|---|---|---|---|---|---|
| **SEC EDGAR** | **Form D private-placement filings: issuer, date, offering amount, amount sold** — the closest thing to real funding data that is free and official. Three services: `data.sec.gov` (JSON submissions), `efts.sec.gov` (full-text search since 2001), `company_tickers.json` | US-incorporated issuers that file | free, no key; a User-Agent naming you and a contact email is requested | **stay under ~10 requests/second** | ✅ documented, ⛔ not called from here |
| **UK Companies House** | filing history, officers, persons with significant control, share capital | UK companies | free API, key required | **600 requests / 5 minutes**, then HTTP 429 | ✅ |
| **GDELT DOC 2.0** | news mentions worldwide: title, URL, domain, country, language; entity endpoints for organisations | anyone in the news | free API | ~100 articles per query, newest-first | ✅ |
| **Hacker News (Algolia)** | mentions, Show HN / Launch HN with dates and points; `/search` and `/search_by_date` | anyone discussed on HN | free, **no key** | ~10,000 requests/hour per IP reported; 1,000 hits max | 🟡, ⛔ |
| **Wayback CDX** | every archived snapshot of a site: 14-digit timestamp, status, MIME, content digest — **history we do not have to store** | any company with a website | free, no key | fair use | ✅ |
| **GitHub** | commits, contributors, stars for a company's org | companies with public code | free API, key raises limits | rate-limited per hour | 🟡, ⛔ |
| **Product Hunt v2 (GraphQL)** | launches, votes, comments | consumer/dev products | free account token | **"The Product Hunt API must not be used for commercial purposes"** — a hard stop for anything sold to funds | ✅ |
| **Company's own site / careers page** | is it alive, does it price, how many roles are open | everyone with a site | direct | politeness and robots.txt | ⚪ |

---

## 4. What is genuinely not available for free — and the honest substitute

| Wanted | Reality | Substitute we can defend |
|---|---|---|
| Revenue | never published for private companies | hiring volume, code activity, press cadence — labelled as proxies, never as revenue |
| Valuation | not published; paid databases estimate it | nothing. **Leave the field absent rather than model it** |
| Cap table / investor list | not public | Form D discloses the offering and related persons for US filers; UK filings disclose officers and PSCs |
| Round size | not published | Form D *offering amount* — which is what was offered, not always what closed. That distinction goes in the UI, not in a footnote |
| Headcount over time | YC's `team_size` moves rarely | job postings, LinkedIn is off-limits by our own rule, so: careers pages |

---

## 5. How the sources join

**Join keys, in order of trust:**

1. **Domain** — the strongest key. Normalise to registrable domain, strip `www`.
2. **Legal name + jurisdiction** — for registry sources; requires the fuzzy layer.
3. **Explicit identifiers once found** — SEC CIK, Companies House number, GitHub org.
   Once resolved, they are stored, and every later run reuses them instead of
   re-guessing. ⚪

**The rule that keeps it honest:** a match below the confidence threshold is *not*
merged. It goes into a review queue with both candidates and their source links. One
publicly wrong merge — two same-named companies fused into a single profile — costs
more trust than fifty missing matches.

**Storage shape:** facts are stored **long, not wide** —
`(company_id, field, value, observed_at, source_id, source_url, confidence)`. Adding
the eleventh source is an insert, not a migration. This is also what makes the
timeline, the provenance line under every value, and the coverage matrix fall out for
free rather than needing three separate features.

---

## 6. Where it can live, for free

| Option | Free allowance | Why it matters here | Confidence |
|---|---|---|---|
| **GitHub Releases assets** | large files, **outside the git history** | snapshots stop bloating the repository | ⚪ |
| **Cloudflare R2** | 10 GB, and **no egress charge** | a static site can read data directly | 🟡 |
| **Cloudflare Pages + Workers** | unlimited static bandwidth; Workers 100k requests/day; D1 5 GB with 5M row-reads/day; 500 builds/month | the whole public site, static-first, no bill | 🟡 |
| **Supabase** | 500 MB Postgres, **50,000 monthly active users** for auth, 2 projects | the only free path to accounts and subscriptions — **but a free project pauses after ~7 days without activity** | 🟡 |
| **Hugging Face Datasets** | free, versioned, public | publishing the dataset *and* storing it in one move | ⚪ |

---

## 7. What must be measured before anything is built

Each of these is a half-day and each can kill or confirm a branch. None has been done:

1. **Form D match rate** on a 200-company YC sample — the number that decides whether
   funding data is a headline feature or a footnote.
2. **GitHub org discovery rate** — how many companies can be linked to a public org
   without guessing.
3. **HN mention rate** and its noise level for common company names.
4. **GDELT precision** for startup names — how much of it is the wrong "Motion".
5. **Wayback coverage depth** for small startup domains — how far back, how dense.
6. **Careers-page detectability** — how many sites expose a machine-readable listing.

---

## Sources consulted

- [SEC.gov — Developer Resources](https://www.sec.gov/about/developer-resources) ·
  [EDGAR full-text search](https://www.sec.gov/edgar//search/)
- [Companies House Developer Specs](https://developer-specs.company-information.service.gov.uk/) ·
  [Developer guidelines](https://developer.company-information.service.gov.uk/developer-guidelines)
- [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) ·
  [GDELT data access](https://www.gdeltproject.org/data.html)
- [Hacker News API guide (Algolia + Firebase)](https://cotera.co/articles/hacker-news-api-guide)
- [Wayback Machine APIs](https://archive.org/help/wayback_api.php)
- [SBIR Data Resources](https://www.sbir.gov/data-resources)
- [Product Hunt API docs](https://api.producthunt.com/v2/docs)
- [Cloudflare Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) ·
  [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [Supabase free-tier limits (secondary)](https://infrafree.dev/en-us/provider/supabase)
- [Scraping, robots.txt and EU database rights (secondary)](https://www.browserless.io/blog/is-web-scraping-legal)
- [Techstars portfolio](https://www.techstars.com/portfolio) ·
  [Antler portfolio](https://www.antler.co/portfolio)
