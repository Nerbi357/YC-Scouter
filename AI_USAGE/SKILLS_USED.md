# The agent setup used on this project

This project was built by an AI coding agent that was given **written methods to
follow** rather than being asked to improvise each time. This page describes that
setup concretely; the reusable idea behind it is in
[`../FOR_AI/AI_INSTRUCTIONS.md`](../FOR_AI/AI_INSTRUCTIONS.md) §9.

## The idea in one paragraph

A *skill* is a plain Markdown file describing how a class of task should be done —
how to plan a feature, how to write a test first, how to investigate a failure, how
to review a diff before merging. The agent reads the relevant one and follows it.
The benefit is consistency: the same request produces comparable work across
sessions and days, and any lesson learned once can be written down so it is not
re-learned. The files are committed with the project, so a new session inherits
them automatically.

## What is in the repository

The agent's working files live in `.claude/` and stay with the project:

| Path | What it holds |
|---|---|
| `.claude/skills/` | 24 method files — one per class of task |
| `.claude/commands/` | shortcuts that invoke a method: spec, plan, build, test, review, ship, simplify, performance audit |
| `.claude/agents/` | role definitions used for focused passes: reviewer, security auditor, test engineer, performance auditor |
| `.claude/settings.json` | session setup — prepares the environment at the start of every session |
| `.claude/session_start.sh` | installs the pinned dependencies so tests and linters run immediately |

They are a vendored copy of the open toolkit
[`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) (MIT). To
reproduce the setup elsewhere:

```bash
git clone https://github.com/addyosmani/agent-skills
cp -r agent-skills/.claude <your-repo>/.claude
```

## Which methods actually did work here

| Method | What it produced on this project |
|---|---|
| Idea refinement | turned a rough brief into concrete decisions: source, model and budget, hosting, update strategy, repository layout |
| Specification | the written spec approved before any code — objective, data model, the two runnable units, budget, boundaries |
| Planning | vertical tasks with acceptance criteria, dependency order, and owner checkpoints between phases |
| Incremental build + test-first | the working loop: failing test → minimal code → whole suite green → linters → one atomic commit |
| Debugging and error recovery | the default response to any failure — reproduce, find the root cause in the traceback, only then change code. This is what turned "the dashboard crashed" into three distinct causes, fixed separately |
| Code review | pre-merge review across correctness, readability, architecture, security, performance |
| Security hardening | the owner/visitor model, fail-closed access, constant-time secret comparison, no secrets in the repository |
| Browser verification | the habit of checking UI changes in a real browser against real data instead of trusting unit tests |
| Documentation of decisions | recording each decision *with its reason*, which is what the project memory is made of |
| Performance work | measure → change → measure again, and publish the result even when it is "no change" |

## Roles, and when several were run at once

Most work was one focused pass. Two situations justified running several agents in
parallel:

- **Discovery** — independent researchers on the open questions of the spec (data
  source, cost, hosting, update strategy, longevity), each bringing back trade-offs
  for the owner to decide.
- **Adversarial audit** — several attackers on the finished dashboard with
  different lenses (correctness, data integrity, access, resilience), each blind to
  the others, so they did not share a blind spot. Every finding was reproduced
  independently before it was fixed. This produced the ten critical defects listed
  in [`AI_METHODOLOGY.md`](AI_METHODOLOGY.md) §6.

## The rules the agent worked under

Open sources only, no paywalled links · never fabricate funding, cap-table or
valuation figures · never commit secrets · everything written into the repository
in English · options presented before any large change · every change lands with
tests and linters green · what the agent decided on its own is reported out loud.
