# Agent Skills (vendored)

This directory vendors the [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills)
toolkit into the project so the skills, slash commands, and specialist agents are
available automatically in every Claude Code session — no per-session plugin install
needed.

## Contents

- `skills/` — 24 lifecycle skills (spec, planning, TDD, review, security, shipping, …)
- `commands/` — 8 slash commands: `/spec`, `/plan`, `/build`, `/test`, `/review`,
  `/webperf`, `/code-simplify`, `/ship`
- `agents/` — 4 specialist personas (code-reviewer, security-auditor, test-engineer,
  web-performance-auditor)
- `references/` — supplementary checklists the skills link to

## Typical workflow

`/spec` → `/plan` → `/build` → `/test` → `/review` → `/ship`

## Attribution

Source: https://github.com/addyosmani/agent-skills — MIT License,
Copyright (c) 2025 Addy Osmani. See `LICENSE.agent-skills`. Vendored unmodified.
Update by re-copying `skills/`, `commands` (from the upstream `.claude/commands/`),
`agents/`, and `references/` from the upstream repo.
