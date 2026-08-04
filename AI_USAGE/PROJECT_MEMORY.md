# PROJECT MEMORY — YC Scouter

> **Purpose.** This file is *this project's* memory. If the session restarted or the
> work continues elsewhere, it restores what is being built, how, and why — with
> nothing lost.
>
> **Reading order.** [`AI_INSTRUCTIONS.md`](AI_INSTRUCTIONS.md) first (how to work
> with the owner — it applies to every project and outranks any habit), then this
> file, then `../DOCS/HOW_IT_WORKS.md` (how the code works) and
> `../DOCS/HOW_TO_UPDATE.md` (maintenance). Ideas that were raised but not
> scheduled live in [`IDEAS.md`](IDEAS.md).
>
> **Keep it current.** Decisions, results and open questions are written here in the
> same pass as the work. A stale memory file is worse than none.

---

## 1. What this project is

**YC Scouter** — a personal tool for the owner (Nerbi357) to find and evaluate
Y Combinator startups **from 2020 to the present**.

- Repository: **`Nerbi357/YC-Scouter`** (public). An older clone may still be wired
  to the repository's previous path; GitHub redirects, so it keeps working. Inside
  an agent sandbox, do **not** rewrite that remote: fetching accepts either name,
  but only the path the sandbox was created with is authorised to push (verified
  2026-07-25 — the renamed URL fetches and then fails the push with HTTP 403).
- Live dashboard: **https://nerbi357-yc-scouter.streamlit.app/**
- Data: **several thousand companies** (batches 2020–2026), all with an AI description
  and risks. Exact counts are deliberately kept out of the documents — they drift with
  every rebuild; the dashboard shows the number of the dataset it is reading.

It consists of two notebooks (collect → AI-enrich), dated datasets in `data/`, a
Streamlit dashboard and documentation.

## 2. Project phases (the owner's vocabulary)

- **Working phase** — drafts, scratch files and experiments are fine.
- **Final phase** — only agreed files remain; the owner's routine is "press two
  buttons every few months".

**Where it stands (2026-07-27):** v1.0 is released and finished, and the project has
**re-entered the working phase** for v2 — a multi-source platform. v1.0 is not
broken to make room: its pipeline becomes one source among many. The map of the work
lives in [`PLAN.md`](PLAN.md), the source study in
[`SOURCE_RESEARCH.md`](SOURCE_RESEARCH.md).

## 3. How to communicate

The full contract — decision rights, the idea funnel, phases, self-audit, the
team-of-agents and skills philosophy, templates — lives in
[`AI_INSTRUCTIONS.md`](AI_INSTRUCTIONS.md) and applies here unchanged. Only the
project-specific additions are listed below.

- **Honesty about this data:** never invent cap tables, round sizes or valuations
  for private startups; where the source is silent, the cell stays empty and the
  card offers an open link instead.
- **Honesty about results, with this project's own example:** paginating the bulk
  notes editor was expected to speed up a rerun and measured 1.06 s → 1.12 s, i.e.
  nothing. It was reverted and recorded so nobody retries it.
- The owner runs the notebooks in **Google Colab** and presses the two buttons on
  GitHub — instructions for them are always click-by-click.

## 3a. The owner's requirements for project structure (follow these)

The owner wants a **maximally clean repository**: the GitHub landing page shows
only blocks and a few mandatory files, with no service clutter.

**Placement rules (agreed 2026-07-25):**

1. **Keep the root minimal:** `README.md`, `README.ru.md`, `app.py`,
   `requirements.txt`, `pyproject.toml`, `LICENSE`, `.gitignore`,
   `.python-version`. Nothing else goes to the root — a new file goes into a block.
   **One deliberate exception:** `SIGNALS.md`, added 2026-07-27 with the
   `signal-capture` skill, which puts the log at the root on purpose — the owner reads
   it there, and a log filed away in a service folder is a log nobody processes. Move
   it into `AI_USAGE/` if the clean root wins; the hook's path is the only edit.
2. **Service code lives in `src/`** — including the tests (`src/tests/`), which are
   service code rather than a project block.
3. **Everything the AI agent needs lives in `.claude/`**: skills, commands, agents,
   `settings.json`, `session_start.sh`.
4. **`AI_USAGE/` is the AI's own folder**: `AI_INSTRUCTIONS.md`,
   `PROJECT_MEMORY.md`, `IDEAS.md`. Documents aimed at outside readers belong in
   `DOCS/`, not here.
5. **`DOCS/` holds documents for people**, one per job: how it works, how to
   deploy, how to update. Never create two documents answering the same question.
6. **Never delete anything from `data/`** — dated runs are kept as an archive.
7. **Everything the AI needs lives in `AI_USAGE/`**: `AI_INSTRUCTIONS.md` (portable
   rules, travels between projects), `PROJECT_MEMORY.md` (this file) and
   `IDEAS.md` (the backlog). No separate SPEC / plan / TODO in the final state —
   the plan is a working instrument and is folded in here when the project closes.
8. **The final version must look finished** (asked for 2026-07-27). The judgement is
   made from what a first-time visitor sees: the landing page, the file listing, the
   README. Anything that reads as a workbench — draft files, clutter in the root,
   working prefixes in commit subjects — is a defect. This includes the column
   GitHub prints next to every file with the subject of the last commit that touched
   it: those lines are part of the page, so they are written as short plain
   sentences (see `AI_INSTRUCTIONS.md` §10). The column itself cannot be turned off.

**What physically cannot be moved** (verified — moving it breaks the project):
`requirements.txt` (Streamlit Cloud only reads it from the root), `pyproject.toml`
(the root is required by `pip install -e .`, ruff and pytest),
`.github/workflows/` (GitHub only runs workflows from that path), `.streamlit/`
(Streamlit only reads config and secrets from there), `app.py` (the path is set in
the hosting configuration).

## 4. Methodology, skills and the working algorithm

A fork of **`addyosmani/agent-skills`** is vendored into `.claude/`, plus two skills
the owner supplied on 2026-07-27.

- **`living-project`** shapes v2 and outranks habit for anything structural: build
  wide before deep, every step must make the next cheaper, a failed branch is still a
  branch if its failure is published, and the ideas file is the visible roadmap rather
  than a tidy-up.
- **`signal-capture`** keeps [`SIGNALS.md`](../SIGNALS.md) at the root: raw
  observations about *how the work goes*, quoted verbatim, recorded as they happen and
  reviewed later against the skill library. Writing one is not proposing a fix. A
  `SessionStart` hook (`.claude/signals_check.sh`, wired into `.claude/settings.json`
  next to `session_start.sh`) reports the count each session and offers a review pass
  once the count reaches the threshold — **20 by default; the owner has not set this
  project's number yet.**

**The algorithm for any task (agreed with the owner):**

1. **Understand and propose.** Study the task, show 2–4 options with their effect,
   downsides and a recommendation. Wait for the owner to choose.
2. **Test first, then code** (TDD): red test → minimal code → whole suite green →
   `ruff` → **one atomic commit** whose message explains *why*.
3. **Verify for real.** For UI — a real browser (Playwright) against the real
   dataset; for speed — a before/after measurement, not a feeling.
4. **Deploy:** merge the working branch into `main` → push (Streamlit picks it up).
5. **Write the decision and the result into `PROJECT_MEMORY.md`** in the same pass.
   While a project is in flight there is also a [`PLAN.md`](PLAN.md) — it exists again
   for v2 and is folded back in here when the project next closes.
6. On any failure use `debugging-and-error-recovery`: find the root cause in the
   traceback first, then change code. Never guess.

Commands: `/spec /plan /build /test /review /ship /code-simplify /webperf`
(`.claude/commands/*`); skills: `.claude/skills/*`; agents: `.claude/agents/*`,
including `source-scout` for open-data research with confidence marks.

- **Do not move `.claude/`** — the harness finds it by path, and
  `.claude/settings.json` points at `.claude/session_start.sh`.
- For hard tasks the owner approves **multi-agent runs** (Workflow): that is how
  the discovery research and the adversarial audit of the dashboard were done.

## 5. Git and deployment

- **One branch only: `main`.** The owner asked for it (2026-07-25) once the project
  reached its final state: the working branch had become an exact copy of `main`
  after every merge, so it was clutter rather than protection.
- **`main` is what is deployed** to Streamlit Cloud, so a push goes live in 2–3
  minutes. That is the trade-off of a single branch, and it puts the burden on the
  checks: **run the tests and the linters before every push**, and for anything the
  visitor can see, the browser check as well. Nothing goes to `main` unverified.
- **For risky or multi-step work, create a temporary branch, merge it, delete it.**
  The rule is "no permanent second branch", not "never branch".
- **An assistant session cannot delete a remote branch here.** Its git credentials
  allow pushes but reject ref deletions (`git push --delete` → HTTP 403), so the
  last step of retiring a branch is the owner's: GitHub → *Branches* → the bin icon.
  Merge first, delete second — the assistant can prove the branch is fully contained
  in `main` (`git merge-base --is-ancestor <branch> origin/main`) before it goes.
- The two Actions buttons commit straight to `main` (dated datasets + the AI cache),
  so pull before starting work — CI may be ahead of you.
- Do not open pull requests unless explicitly asked.
- Never commit secrets (`.env`, `.streamlit/secrets.toml` are git-ignored).

## 6. Repository map (what lives where, and why)

```
README.md                   the shop window — for a first-time visitor (English)
README.ru.md                the same README, translated
app.py                      the Streamlit dashboard — the most active file
requirements.txt            pinned + hashed versions (must stay in the root)
pyproject.toml              dependency source, packaging, ruff/pytest settings
LICENSE .gitignore .python-version

src/yc_scouter/             ALL the logic (notebooks and the dashboard import it)
  config.py                 THE single source of truth: model, tokens, prices, paths
  fetch.py normalize.py     download YC data + normalize (key = the immutable id)
  enrich.py score.py        investability, open links, custom_score 0–100
  ai.py                     AI description + risks, cache on (id, model, prompt_version)
  export.py                 dated parquet/xlsx
  filters.py                dashboard filtering and search
  user_data.py              notes (id, watchlist, my_tags, my_stage, my_notes)
  gsheets.py                Google Sheets backend for the notes
  pipeline.py               build_base() / build_ai() — the thin API for notebooks
src/tests/                  the test suite; network and LLM mocked (a run costs nothing)

notebooks/01_dataset_base.ipynb   File 1 — collect all companies 2020→now
notebooks/02_ai_summary.ipynb     File 2 — AI enrichment (Claude/Groq/mock)
data/                       dated datasets + data/cache/ai_cache.json (archive, never pruned)

DOCS/HOW_IT_WORKS.md              how everything works — detailed, for outsiders
DOCS/HOW_TO_DEPLOY_DASHBOARD.md   step-by-step deployment + Google Sheet + sharing
DOCS/HOW_TO_UPDATE.md             maintenance checklist (buttons, keys, models, lock)

AI_USAGE/AI_INSTRUCTIONS.md  HOW to work with the owner — portable, travels along
AI_USAGE/PROJECT_MEMORY.md   THIS file — everything about this project
AI_USAGE/IDEAS.md            backlog: proposals raised but not scheduled

.claude/                    agent service files: skills, commands, agents,
                            settings.json, session_start.sh (prepares the session)
.github/workflows/          the two buttons: build-dataset.yml, build-ai-summary.yml
.streamlit/                 config.toml + secrets.toml.example (secrets never committed)
```

**Roles of the documents** (do not mix them):
`AI_USAGE/AI_INSTRUCTIONS.md` — how to work with the owner, on **any** project;
`AI_USAGE/PROJECT_MEMORY.md` — everything about **this** project (this file);
`AI_USAGE/IDEAS.md` — proposals not yet scheduled;
`DOCS/*` — for people: how it works / how to deploy / how to maintain;
`README.md` — the shop window and navigation.

## 6a. The original brief (absorbed from the deleted `Archive/SPEC.md`)

The task as the owner first stated it, so it is not lost:

> "YC Scouter" — a personal tool plus a hosted dashboard for finding and analysing
> Y Combinator companies **from 2020 to the present**.

The agreed (and delivered) contents:

1. **File 1** — a notebook collecting all YC companies → "YC Dataset Base *date*"
   (`.parquet` + `.xlsx`), with a switch at the top of the code: save to Google
   Drive (folder "Project YC Scouter") or download when the run finishes.
2. **File 2** — a notebook running every company through an LLM: a short
   description + 2–3 main risks (marked as AI-authored), with a provider switch
   (Claude / Groq) → "YC Dataset AI Summary *date*", same two formats.
   *Later simplified by the owner:* the one-liner comes from YC, two AI fields stay.
3. **A results folder** — 4 files per run (Base/AI × parquet/xlsx), dated.
4. **A "how it works" document** → `DOCS/HOW_IT_WORKS.md`.
5. **An "AI prompts and skills" document** → the prompts, their constraints and the
   cost controls live in `DOCS/HOW_IT_WORKS.md` §5; how the agent was set up and
   directed lives in `AI_USAGE/AI_INSTRUCTIONS.md`.
6. **File 5** — "a notebook preparing the dashboard deployment" → **not built
   separately**: `app.py` and `DOCS/HOW_TO_DEPLOY_DASHBOARD.md` fill that role.
7. **README** — a short description + a link to the dashboard.
8. **A dashboard on the internet**, independent of the owner's machine.

Constraints: reproducibility of **code logic**, not of data; the project can be
re-run to collect new companies; no service files beyond the agreed ones.

## 7. Locked technical decisions (do not reinvent)

1. **Everything is keyed by the immutable company `id`** (not `slug`: it changes on
   rename and orphans the notes).
2. **Reproducibility = code logic, not data.** Thin notebooks, all logic in `src/`,
   versions pinned by a hashed `requirements.txt` + Python 3.11. Data legitimately
   differs between runs.
3. **AI:** Claude `claude-haiku-4-5`, two outputs (`ai_description` 6–7 sentences,
   `ai_risks` 1–2 short ones). `MAX_DESC_CHARS=2200`, `MAX_TOKENS=430`. A full run
   is ≈ **$7–8.5** (target ≤ $9). The cache is keyed on
   `(id, model_id, prompt_version)` — we pay only for new companies. Changing the
   prompt bumps `prompt_version` and re-summarises everything. The 0–5 rating was
   **removed** on purpose.
4. **Updates are manual, two buttons** in GitHub Actions. No cron. Google Drive is
   never wired into Actions.
5. **Notes:** the owner → a Google Sheet (survives restarts); a visitor → their own
   session (`st.session_state`), fully isolated in both directions.
6. **Performance beats prettiness:** on the free tier nothing is built eagerly on
   every rerun (exports only on demand; search is vectorised).

## 8. The owner's decision log

- Public repository; AI provider is Claude; originally 3 AI fields, later reduced
  to 2 (the one-liner comes from YC).
- Dated names `yc_dataset_<base|ai>_<YYYY-MM-DD>.{parquet,xlsx}`.
- Documents for people: `HOW_IT_WORKS`, `HOW_TO_DEPLOY_DASHBOARD`, `HOW_TO_UPDATE`.
- Spec, plans and TODO were **absorbed into this file**; `Archive/` deleted
  (2026-07-25): instructions for the AI live in one place.
- Documents for outside readers about the AI work were **dropped** (2026-07-25) —
  the owner does not need them. What survives: the prompts and cost controls in
  `DOCS/HOW_IT_WORKS.md`, and the agent-facing files in `AI_USAGE/`.
- Tests moved to `src/tests/`, `session_start.sh` to `.claude/`, `requirements.in`
  folded into `pyproject.toml`, `.env.example` deleted.
- **File 5 of the original brief is not built separately**: `app.py` and
  `DOCS/HOW_TO_DEPLOY_DASHBOARD.md` fill that role.
- Score/team filters are "From"/"To" fields (not sliders); empty = no bound; the
  data's min/max shown in italics underneath.
- Cards: 50 per page, sorting, copy-card, notes inside every card.
- The "Invested" metric was removed (the funnel chart covers it).
- **Language (2026-07-25):** everything in the repository is English — code, docs,
  the dashboard UI and this file — so an English speaker can read the whole
  project. `README.ru.md`, a translation of the README, is the one exception. The
  language of the conversation is not fixed here: the owner names it at the start of
  each project (see `AI_INSTRUCTIONS.md` §2).
- Visitor-facing folders are named in CAPS (`DOCS/`, `AI_USAGE/`).
- **No drifting counts in descriptions** (2026-07-25): company and test counts drift
  with every rebuild and had already disagreed across files (4037 vs 4040).
  Descriptions say "several thousand" / "the test suite"; the dashboard reports the
  real number of the dataset it reads. **Measurements and examples keep their
  numbers** — they are facts about one moment — but must name the date or the run
  they came from ("the full run of 2026-07-24 cost $7.14 for ~4,000 companies").

## 9. What is done (state as of the last session)

- ✅ Pipeline, the full dataset with AI, both Actions buttons working.
- ✅ Dashboard deployed: 4 tabs, filters, charts, comparison, notes.
- ✅ Owner's notes in a Google Sheet; visitors get an isolated session.
- ✅ Safety net: any uncaught error shows the reason plus a reset button.
- ✅ Tolerant to "stringified" booleans from Sheets, duplicate ids, garbage ids.
- ✅ Hotfix: the export row no longer blocks the tab bar.
- ✅ Card list sped up: notes in the list open **on a button** (option A) — 132
  interactive elements instead of ~350, the Companies tab renders in **0.8 s**.
  The page size stays at 50 cards by the owner's decision.
- ✅ Row click → card sped up: **1.1 s → 0.4 s** (closing 1.2 → 0.3 s). Two causes:
  (1) a redundant `st.rerun()` in `selectable_table` — `on_select="rerun"` had
  already rerun the script and the card is drawn later in the same pass; (2) every
  click repainted all four tabs. The table and the card now live in one
  `@st.fragment` (`table_and_card`). Measured with Playwright on the real dataset.
- ✅ **All confirmed critical findings of the adversarial audit are closed**
  (2026-07-25, 4 atomic commits, +25 tests):
  1. Searching for `[` or `'` returned every company in the dataset — parquet returns `tags`
     as a `numpy.ndarray` and the search matched the array's repr
     (`filters.is_sequence`).
  2. An empty `team_size` counted as zero and passed an explicit "up to N" filter —
     an explicit bound now requires a known value.
  3. A failed Sheets read made the next save erase every note. Now: writing is
     blocked while the sheet is unreadable; `gsheets.save` refuses to overwrite a
     populated sheet with an empty one; it writes first and clears leftovers after
     (it used to `ws.clear()` before writing).
  4. A blank or misspelled `owner_key` with Sheets configured made everyone an
     owner → the gate fails closed plus a sidebar hint; the key comparison is
     constant-time and tolerates stray spaces.
  5. The sheet was read **on every rerun** → now once per session, with a
     "🔄 Reload from the sheet" button in the Notes tab.
  6. A duplicate `id` in the dataset caused `DuplicateWidgetID` and killed the
     dashboard; a garbage id sent notes nowhere. `prepare_data()` cleans both and
     reports what it cleaned.
  7. A column missing after a rebuild was a `KeyError` inside a chart. Optional
     columns are filled empty; only a missing `id`/`name` is fatal.
  8. The row selection lived **by position** → after a filter change a different
     company opened. The table's widget key is derived from the visible ids
     (`_selection_key`).
  9. Comparison crashed on companies sharing a name (108 such rows) → selection by
     `id`, label "Name · Batch" (+ `#id` when even that repeats).
  10. Choosing an industry reset the chosen subindustry → the still-valid part of
      the selection is kept (`keep_valid`).
- ✅ Small fixes from the owner's review (2026-07-25): "Next →" is no longer active
  on the last page (the step moved into an `on_click` callback — otherwise the
  button state lagged one render behind); the batch-year axis is categorical
  (`year_bar`), so no more "2020.5"; saving a note shows a green "Saved ✅" (a flag
  in session state survives `st.rerun`) plus a toast.
- ✅ **The owner's update routine was rehearsed end to end** (2026-07-25): both
  Actions buttons ran, the 2026-07-25 dataset added 3 new companies at 100%
  AI coverage, a single model, cost ≈ $0.005 (the cache paid only for the new
  ones). The dashboard picked up `yc_dataset_ai_2026-07-25.parquet` by itself.
  ⚠️ Diagnostic note: two File 1 runs at 12:33 and 12:36 failed with
  `startup_failure` and **zero jobs** — a failure on GitHub's side (the workflow
  never started), coinciding with the repository rename. Re-running the same file
  worked with no change. Cure: just press the button again.
- ✅ **Repository restructured to the owner's requirements** (2026-07-25): tests →
  `src/tests/`, `session_start.sh` → `.claude/`, `AI_USAGE/` created (portable
  methodology + skills description), `DEPLOY.md` → `HOW_TO_DEPLOY_DASHBOARD.md`
  (rewritten step by step), `HOW_IT_WORKS.md` expanded, `Archive/` deleted (the
  brief absorbed here), `requirements.in` → `pyproject.toml`, `.env.example`
  deleted. Verified after the move: the whole suite, ruff, a browser check on the real
  dataset (~4,000 rows), and **a File 1 Actions run on the new structure succeeded** (so
  `pip install -e .` and papermill still work).
- ⚠️ **The preflight itself caused one failed run** (2026-07-25) and was corrected:
  it gated on the provider's model *listing*, which carries dated snapshots
  (`claude-haiku-4-5-20251001`) but not necessarily the alias we call
  (`claude-haiku-4-5`), so File 2 refused to start on a model that works fine. The
  gate is now the single one-token call itself — the same thing the run does — and
  the listing only enriches the message when a model really is gone. Lesson worth
  keeping: a guard that can block correct work needs the same adversarial thinking
  as the thing it guards.
- ✅ **Preflight before spending** (2026-07-25, `src/yc_scouter/preflight.py`, 7
  tests): File 2 verifies the key, the credit balance and the model id before the
  loop, and turns each failure into a named instruction. Costs one token. A network
  blip is a warning, not a blocker.
- ✅ **Second adversarial audit, cross-verified** (2026-07-25): five agents attacked
  the project with different lenses (data correctness · access and privacy ·
  resilience to hostile input · user flows · operations and documentation accuracy),
  and each lens's findings were then handed to a *different* agent whose job was to
  refute them. 30 candidates → **9 confirmed** (2 high, 5 medium, 2 low), 21 refuted.
  All nine are fixed, plus one more that the browser check found while verifying:
  1. **Two sessions could delete each other's notes.** A save wrote back the
     whole-table snapshot the session had cached, so a note added from another tab —
     or typed into the Google Sheet by hand — vanished silently. Saving now re-reads
     the sheet and merges **only the changed companies** (`user_data.upsert`,
     `app.upsert_annotations`): last-writer-wins per company, not per table.
  2. **Closing the card on the Overview tab blanked the whole dashboard.**
     `detail_card` ran outside a fragment there but called
     `st.rerun(scope="fragment")`, which raises; the error screen's only recovery
     button clears session state — a visitor's entire set of notes. The Overview
     table+card now goes through `table_and_card` like the Companies tab.
  3. **Exports mangled `tags`** into a numpy repr (`"['Bio' 'Climate']"`) in both the
     shipped .xlsx and every dashboard download — the ndarray-vs-list trap again.
     Both flatteners now use `filters.is_sequence`.
  4. **An unparseable `secrets.toml` made every visitor the owner**: it looked exactly
     like "no secrets configured", i.e. like a private laptop. Unreadable secrets are
     now distinguished from absent ones and fail closed, with a banner.
  5. **The bulk save wrote every visible row**, which overflowed the auto-created
     1000-row worksheet (the save failed outright) and cost ~20 s of quadratic
     `.loc` growth that any anonymous visitor could trigger. It now writes only the
     diff, vectorised, and `gsheets.save` grows the grid before writing past it.
  6. **`inf` and out-of-range ids** crashed or silently collided; they are dropped
     and counted like any other unusable id.
  7. **A dead Google Sheet was re-contacted on every rerun** — i.e. every keystroke.
     The failure is cached too; "🔄 Reload from the sheet" is the retry.
  8. **The ✕ never actually closed the card** (found by the browser check, not by the
     audit): the table still held the row selection, so the next fragment rerun
     re-opened it. Closing now drops the table widget's state as well.
  Verified: the whole suite green (+13 tests), ruff, and a browser pass over the real
  dataset covering both cards and the notes tab.
- ✅ **Full switch to English** (2026-07-25): the dashboard UI, this file and the
  tests are English; `DOCS/` and `AI_USAGE/` are CAPS.
- ✅ **The finished look** (2026-07-27). The repository page is now judged as part of
  the product:
  - the **About** panel carries a description, the dashboard link and topics;
  - every row of the file listing shows the same subject, **`YC Scouter 1.0`**. It was
    done without touching a single byte of content: one commit flips every file's
    mode, the next restores it, so both commits "touch" every path while the final
    tree is identical to the one before them (verified with `git diff`);
  - the two update buttons write plain subjects (`Refresh the base dataset (date)`),
    because that line sits next to `data/` after every run;
  - **any later commit replaces the row of the files it touches.** That is expected;
    re-seal the listing by repeating the mode-flip pair as the last action before
    closing the project again.
- ✅ **Context for the first-time visitor** (2026-07-27). The README assumed too much:
  it never said what Y Combinator or a *batch* is, never showed the dashboard, and
  never said which numbers are YC's and which are ours. Added, in both READMEs: a
  short *What Y Combinator is* section, two screenshots (`DOCS/images/`), and a
  *How to read the numbers* table that marks the origin of every field and states
  plainly that `investability` is a statement about access, not a prediction.
  - **Re-taking the screenshots** (needed whenever the UI changes visibly): run the
    app locally on the newest dataset, drive it with Playwright, and inject
    `display:none` for `stToolbar`/`stAlertContainer` first — otherwise the shot
    carries the local-mode banner and a "Deploy" button. The page does not scroll
    with `window.scrollTo`: walk up from the card heading to the first ancestor whose
    `scrollHeight` exceeds its `clientHeight` and scroll that.
- ✅ **`score` renamed to `custom_score`** (2026-07-27, owner's request). The point is
  provenance: every other column is what the source says, and this one is our opinion,
  so the name has to say so. Datasets built before the rename stay readable —
  `prepare_data` maps the old column instead of blanking it, with a test that guards
  it, because `data/` is an archive.
- ⚠️ **`v1.0` had to be tagged by hand.** The sandbox may push branches but not tags
  (`git push origin v1.0` → HTTP 403, same restriction as deleting a ref). The tag
  and its release page are created in the GitHub UI: *Releases → Draft a new release
  → Choose a tag → v1.0 → Publish*.

## 10. What's next / open tasks

1. **⏳ Come back to performance work** (the owner asked to record this explicitly).
   What still costs time on every rerun — measured by ablation on the real dataset:
   - **charts ≈ 0.36 s** (cache the Plotly figures by a filter hash) — the largest;
   - **the 50 card expanders ≈ 0.16 s**, the two big tables ≈ 0.11 s each;
   - the bulk notes editor is ≈ 0.03 s — **paginating it was tried and reverted**
     (1.06 s → 1.12 s, i.e. no effect). Do not retry it.
   - The structural win would be rendering only the active tab (≈ 0.4 s), at the
     cost of tab switching becoming a server round-trip.
   - Measure with the Playwright script on the real dataset, before and after.
2. **Audit — closed and approved by the owner (2026-07-25).** Two passes were run:
   the first covered confirmed-critical defects, the second was cross-verified across
   five lenses (see §9). Everything confirmed is fixed with a regression test. The
   working plan file was deleted at that point, as agreed — a plan is an instrument
   for a project in flight, not part of a finished repository.
3. **Failure alerting** — the owner picked option 2 only (a preflight in File 2);
   done, see §9. The options he declined for now: a data-contract check after each
   run, a data-health line in the dashboard, and a check-only cron.
4. Possibly phase 2: a full website (Cloudflare Pages on the same dataset). The
   owner decided: **not this time**, keep it for the future.

**Deliberately not doing** (decided, do not re-propose without a reason):
a scheduled data refresh (updates stay manual: predictable, no silent spending,
nothing breaks unattended) · a separate "File 5" deployment notebook (`app.py` plus
`DOCS/HOW_TO_DEPLOY_DASHBOARD.md` fill that role) · documents about the AI work
aimed at outside readers · keeping `AI_INSTRUCTIONS.md` in its own repository.

## 11. Risks and maintenance (details in `DOCS/HOW_TO_UPDATE.md`)

- Anthropic credits run out → File 2 fails; the cache makes a retry cheap.
- The model is retired (~every 6–12 months) → change one constant in `config.py`.
- The Google service account is deleted / its key expires → `invalid_grant`;
  recreate the key, update the secrets, share the sheet with `client_email`.
- Streamlit Cloud sleeps after 12 h idle (wakes in ~15 s) — this is normal.
- Dependencies drift → recompile `requirements.txt` with
  `uv pip compile pyproject.toml --generate-hashes -o requirements.txt`.
- **Careful:** the host may run a newer Python/pandas than we pin locally — pandas
  3 differences have crashed the app twice (stringified booleans, writing text into
  a float column). Test on pandas 3.
- Upgrading Streamlit to **1.60+** requires dropping `pyarrow` below 25: 1.59.1 has
  no such bound, 1.60 introduced `pyarrow<25`.
- **GitHub Actions sometimes fails with `startup_failure` and zero jobs** — a
  failure on GitHub's side, not in our code. Cure: press the button again.

## 12. Starter prompt for a new session

> "Here is the repository Nerbi357/YC-Scouter, branch `main` (the only branch).
> Read `AI_USAGE/AI_INSTRUCTIONS.md` first, then `AI_USAGE/PROJECT_MEMORY.md`, then
> `DOCS/HOW_IT_WORKS.md`. Talk to me in `<language>`, write everything in the
> repository in English. Continue from §10, *What's next*."
