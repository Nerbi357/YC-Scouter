# Skills used to build this project

The project was built with **[Claude Code](https://claude.com/claude-code)** driven
by a vendored copy of the open toolkit
**[`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills)** (MIT).
The working copy lives in `.claude/` at the repo root, so every Claude Code session
picks the skills up automatically — nothing to install.

This page explains **which of them actually did work here, and what each one
contributed**, so the same assistance can be reproduced elsewhere. For the
principles that came out of it, see [`AI_METHODOLOGY.md`](AI_METHODOLOGY.md).

## How to get the same setup

```bash
git clone https://github.com/addyosmani/agent-skills
cp -r agent-skills/.claude <your-repo>/.claude    # skills, commands, agents
```

Then open the repository in Claude Code and drive it with the slash commands
below. A skill is just a Markdown instruction file: the agent reads it and follows
that method instead of improvising, so the same command produces comparable work
across sessions.

## The commands that shaped this repository

| Command | Skill behind it | What it produced here |
|---|---|---|
| `/idea-refine` | `idea-refine` | turned a rough brief into concrete decisions: data source, model and budget, hosting, update strategy, repo layout |
| `/spec` | `spec-driven-development` | the written specification approved before any code — objective, data model, the two runnable units, budget, boundaries |
| `/plan` | `planning-and-task-breakdown` | vertical tasks with acceptance criteria, dependency order and owner checkpoints between phases |
| `/build auto` | `incremental-implementation` + `test-driven-development` | the implementation loop: failing test → minimal code → green suite → linters → one atomic commit |
| `/review` | `code-review-and-quality` | pre-merge review across correctness, readability, architecture, security, performance |
| `/test` | `test-driven-development` | the "prove it" pattern for bugs: reproduce with a test first, then fix |
| `/code-simplify` | `code-simplification` | removing accidental complexity without changing behaviour |
| `/ship` | `shipping-and-launch` | the pre-launch checklist before the dashboard went public |
| `/webperf` | `performance-optimization` | the dashboard performance passes (measure → change → re-measure) |

## Skills that were used without a command

- **`debugging-and-error-recovery`** — the default response to every failure:
  reproduce, find the root cause in the traceback, then change code. This is what
  turned "the dashboard crashed" into three distinct, separately-fixed causes.
- **`security-and-hardening`** — the owner/visitor access model, fail-closed
  access checks, constant-time secret comparison, never committing keys.
- **`browser-testing-with-devtools`** — the habit of verifying UI changes in a real
  browser against the real dataset instead of trusting unit tests.
- **`documentation-and-adrs`** — recording decisions *with their reason*, which is
  what the continuity file and the "do not reinvent" section are made of.
- **`git-workflow-and-versioning`** — atomic commits, a working branch, and a
  `main` that always equals what is deployed.

## Specialist agents (`.claude/agents/`)

Used for focused, parallel passes rather than everyday edits:
`code-reviewer`, `security-auditor`, `test-engineer`, `web-performance-auditor`.
The most valuable run was an **adversarial audit**: several agents attacking the
dashboard in parallel with different lenses, each finding independently reproduced
before anything was fixed.

## Multi-agent runs

Two moments justified fanning out to many agents at once:

1. **Discovery** — researching the open questions of the spec in parallel
   (source, cost, hosting, update strategy, longevity) and bringing back
   trade-offs to decide.
2. **Adversarial audit** — attacking the finished dashboard from several angles
   simultaneously, then verifying every candidate finding before fixing it.

Everything else was faster as a single focused session.

## Ground rules the agent was held to

Open sources only (no paywalled links); never fabricate funding, cap-table or
valuation numbers; never commit secrets; code, comments and docs in English while
the dashboard UI and the owner conversation stay in the owner's language; present
options before large changes; every change lands with tests and linters green.
