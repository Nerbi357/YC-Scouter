# AI methodology — a reusable playbook for building a project like this one

**What this file is.** A portable set of principles, not a description of YC
Scouter. If you are an AI agent (or a person directing one) about to build a
similar project — collect a public dataset, enrich it with an LLM, publish it as
a hosted dashboard, and keep it maintainable by one non-engineer owner — read
this first and adopt what fits. It is written to be dropped into *another*
repository unchanged.

*(Project-specific instructions for YC Scouter itself live in `FOR_CLAUDE.md` at
the repo root. This file deliberately contains no YC-specific decisions except as
illustrations.)*

---

## 1. The shape of the project

Five parts, in this order. Each is useful on its own, so the owner always has
something working:

| Part | What it is | Rule that keeps it healthy |
|---|---|---|
| **Collector** | fetches the public source into a dated dataset | no enrichment here — collection must be repeatable and free |
| **Enricher** | adds LLM fields to the collected dataset | separate runnable unit, because it costs money and needs keys |
| **Store** | dated files (`*_<stage>_<YYYY-MM-DD>.parquet` + a human-readable copy) | never overwrite a previous run; the newest file wins at read time |
| **App** | the dashboard that reads the newest dataset | reads only — it must never fetch or enrich |
| **Buttons** | one manual CI workflow per runnable unit | manual (`workflow_dispatch`), never a schedule |

Two file formats per run: a machine format (Parquet — typed, compact) and a
human format (Excel — openable by the owner without any tooling).

### Lay the repository out for the reader, not for the machine

The landing page of the repository is documentation. Keep it to **blocks plus the
few files that must be at the root**, and give every block one job:

```
README.md            what this is (a stranger reads this first)
<CONTINUITY>.md      how to work on THIS project with an agent
app.py               the entry point
requirements.txt     the lock — most hosts only look in the root
pyproject.toml       packaging + tool config — must be in the root
src/                 all the logic … and the tests (src/tests): service code
notebooks/           the runnable units, thin
data/                dated outputs; an archive, never pruned silently
DOCS/                for humans: how it works / how to deploy / how to maintain
AI_USAGE/            for other people's agents: portable methodology
.<agent>/            for your agent: skills, hooks, session setup
```

Two rules make this stick: **one document per job** (if two files answer the same
question, merge them), and **a new file goes into a block, never into the root**.
Check before moving anything: some paths are dictated by the platform (CI
workflow directories, host config directories, the dependency file) and moving
them silently breaks deployment.

## 2. Principles that survived contact with reality

**A stable key or nothing.** Everything the user creates (notes, tags, statuses)
must attach to an **immutable id** from the source, never to a name or a slug.
Names repeat and slugs change on rename; either one orphans user data silently.
Check for duplicates in the key on load and collapse them — a duplicate key can
crash a UI that builds widget keys from it.

**Reproducibility is about code, not data.** Pin the environment (a hashed
lockfile + a fixed language version) and keep all logic in an importable package
so notebooks, CI and the app run the same code. Do **not** try to freeze the data:
a live source legitimately changes between runs. Say this out loud in the docs, or
someone will file it as a bug.

**Pay only for what is new.** Cache every LLM result under
`(item_id, model_id, prompt_version)` where
`prompt_version = sha256(system_prompt + user_template)[:12]`. Editing a prompt
then *automatically* invalidates exactly what it should, and a re-run after a
failure costs almost nothing. Print a running cost estimate; do not silently
abort on a budget — tell the owner the number and let them decide.

**Never fabricate.** For anything the source does not publish (funding, cap
tables, valuations, contacts), the correct output is an empty cell plus a link to
an open source. State this in the README as a promise; it is the difference
between a tool and a rumour generator.

**Degrade, don't die.** A hosted app is used by people who cannot read a
traceback. Every external dependency (the store, the credentials, the dataset
schema) must have a defined behaviour when it is missing: show a plain-language
banner, keep the rest usable, and wrap the whole render in a last-resort handler
that prints the reason and offers a reset. A blank crash page is a bug.

**A failed read must never authorise a write.** If the shared store cannot be
read, the in-memory state is *empty*, and saving it would erase everything. Block
writes while the store is unreadable, refuse to overwrite a populated store with
an empty one, and write-then-truncate rather than clear-then-write.

**Fail closed on access.** If the app has an owner mode and a shared backend, a
missing or blank password must make everyone a *visitor*, not everyone an owner.
Compare secrets in constant time and treat a blank secret as "not configured".

**Isolation both ways.** If visitors can experiment, give them a session-local
copy of the user data: they get full functionality, the owner's data is never
shown to them, and their edits never reach the shared store. Test both directions
explicitly — it is the kind of thing that silently regresses.

**Measure before optimising, and report the failures.** Wall-clock numbers from
the real dataset, not intuition. In this project the first "obvious" optimisation
(paginating a big editor) measured 1.06 s → 1.12 s, i.e. nothing, and was
reverted; the actual cost was elsewhere. Keep the measurement script; state the
negative result in the log so nobody retries it.

**Budget the browser, not just the CPU.** On a small free-tier host, the
expensive things are the number of widgets and the volume of data serialised per
interaction, not pandas. Build heavy artefacts (exports, files) only on demand,
paginate long lists of interactive elements, and put the most-used interaction in
its own render scope so it does not repaint the page.

## 3. Working with the owner

The owner is the domain expert and the decision-maker; they are usually not the
one reading tracebacks. What worked, repeatedly:

- **Options, then code.** For anything with a trade-off, present 2–4 options with
  the effect, the downside and a recommendation, and wait. Do not start large
  edits on an assumption.
- **Speak in their language and their terms.** Adopt the vocabulary they use for
  phases and artefacts. Keep the conversation in their language even when the code
  and docs are in English.
- **Step-by-step for anything outside the repo.** "Open Settings → Secrets, paste
  this, save" beats "configure the credentials".
- **Disagree when they are wrong, once, with evidence** — then do what they
  decide. A measured number ends an argument faster than an opinion.
- **Report honestly.** If a change did not help, say so with the numbers. If a
  step was skipped, say which. Never present an unverified claim as done.
- **One decision, one record.** Every choice the owner makes goes into a
  continuity file (see below) the moment it is made.

## 4. The continuity file

Assume the conversation will be lost. Keep a single file in the repo (here:
`FOR_CLAUDE.md`) that lets a fresh agent resume with nothing else:

1. what the project is and who it is for;
2. how to communicate with the owner (language, style, approval rules);
3. the methodology and which skills/commands are in play;
4. git and deployment mechanics (branch, what is deployed, how);
5. a map of the repo — one line per file;
6. locked technical decisions, each with the reason ("do not reinvent");
7. the owner's decision log, dated;
8. what is done, what is next, what is known-broken;
9. maintenance risks and their symptoms;
10. a starter prompt for the next session.

Update it in the same commit as the change it describes. A stale continuity file
is worse than none: this project once recorded a repository rename as "not done"
when it was done, and the next session acted on it.

## 5. The build loop

A spec-driven, test-driven cycle, with the owner as the gate between phases:

```
/idea-refine  →  /spec  →  /plan  →  /build (TDD)  →  /review  →  ship
     ↑                                   ↓
     └──────── owner checkpoint ─────────┘
```

- **Refine** the brief into concrete decisions before writing a spec; research the
  open questions (source, model and cost, hosting, update strategy, longevity) and
  bring the trade-offs back as choices.
- **Spec** the objective, data model, units of work, budget and boundaries.
  Approved *before* code.
- **Plan** vertical slices with acceptance criteria and an explicit dependency
  order, with human checkpoints.
- **Build** each slice as: failing test → minimal code → whole suite green →
  linters → **one atomic commit** whose message says *why*.
- **Review** adversarially before calling it done (see below).
- Mock the network and the LLM in tests. A test run must never cost money.

## 6. Verifying a UI you cannot see

Unit tests do not catch "the export row covers the tab bar". For anything with a
browser:

- drive the **real app in a real browser** (Playwright) against the **real
  dataset**, and assert on what a user would notice: this element is clickable,
  this text appeared, this file now contains what I typed;
- when you fix a UI bug, add a browser check that fails without the fix;
- **suspect your own test before the code** when a check disappoints: several
  "failures" here were wrong selectors and wrong expectations, not app bugs;
- keep the scripts — they are the regression suite for the parts unit tests
  cannot reach.

## 7. Adversarial review

Before declaring a phase done, attack the app deliberately: an agent (or several,
in parallel, with different lenses — correctness, data integrity, access,
resilience) tries to break it, then every finding is independently reproduced
before it is fixed. Sort by blast radius, not by ease: "can this destroy the
user's data?", "can a stranger write to it?", "does one bad row kill the page?".
Fix in small commits, each with a test that fails without it.

The most valuable findings in this project were all of that shape: an unreadable
store erasing every note, a blank password making every visitor an owner, one
duplicated id taking the whole app down, a selection remembered by row position
opening the wrong record after a filter change.

## 8. Prompts for the enrichment step

- **Two outputs, not five.** Ask for exactly the fields the UI shows. Every extra
  field is money and a place for the model to speculate.
- **Ground the model in the record.** Pass the source's own fields verbatim and
  cap the free-text input (a character cap is a cost cap).
- **Forbid invention explicitly** in the system prompt: no numbers, funding,
  traction or metrics that are not in the input.
- **Ask for JSON** with named keys and parse defensively — a model may return a
  list where you expect a string; normalise on the way in.
- **`temperature = 0`** and one model per run, recorded in the output, so a
  dataset is always traceable to what produced it.
- **Keep a mock provider** that produces the same shape offline, for tests and
  demos.

## 9. Longevity

Write down, in the maintenance doc, what will break and how it will look:
credits running out, a model being retired (one constant to change), a service
account key expiring (the exact error string), a free host sleeping, dependencies
drifting, and a *newer* runtime on the host than the one you pin locally — that
last one caused two production crashes here, both invisible in local tests.

---

*Companion file: `SKILLS_USED.md` — which agent skills were actually used in this
project, what each contributed, and where to get them.*
