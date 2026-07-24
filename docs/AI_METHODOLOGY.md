# AI methodology

Two separate things live here: (1) the **LLM prompts** the project uses to
summarize companies (File 2), and (2) the **agent-skills workflow** used to build
the project with Claude Code — so you can replicate the same assistance.

---

## Part 1 — The company-summary prompts (File 2)

Defined in `src/yc_scouter/ai.py`. Two factual outputs per company:

- `ai_description` — 6–7 sentences (idea, uniqueness, strengths, useful facts).
- `ai_risks` — 1–2 short concrete risks.

The one-liner is **not** AI-generated (YC's own `one_liner` is used). Nothing
speculative (funding/traction/valuation) is requested — factual only.

**System prompt (verbatim intent):** "You are a venture analyst. Using ONLY the
facts provided … Return a single JSON object with `description` (6–7 sentences …)
and `risks` (1–2 short concrete risks). Do NOT invent facts, numbers, funding,
valuations, traction, or metrics."

**User prompt template:** name, one-liner, industry/subindustry, tags, status,
team size, batch, stage, and the (truncated) `long_description`.

**Parameters** (in `config.py`, one place to change):
- Model: `claude-haiku-4-5` (default) or a Groq model; `temperature=0`.
- `MAX_DESC_CHARS = 2200` (input ≈ 780 tokens), `MAX_TOKENS = 430` (output ≈ 260).
- Estimated full run (~4,000 companies) ≈ **$8–8.5** (target ≤ $9). The summarizer
  prints a running cost estimate; it never auto-halts.

**Cache & versioning:** results are keyed on `(id, model_id, prompt_version)`,
where `prompt_version = sha256(SYSTEM_PROMPT + PROMPT_TEMPLATE)[:12]`. Editing the
prompt changes the version, which triggers a clean re-summarization; old entries
are kept. So only NEW keys are ever billed. To intentionally refresh every
description, edit the prompt (the version bumps automatically).

**Providers:** `claude` (default), `groq` (free tier, opt-in), and `mock` (offline,
no spend — used for demos and the notebook smoke test).

---

## Part 2 — How this project was built with Claude Code (replicate it)

The project was built with **Claude Code** using the vendored `agent-skills`
(under `.claude/`). The workflow, in order:

1. **`/idea-refine`** — turned a rough brief into concrete decisions. A multi-agent
   discovery pass researched the open questions (data source, model/token/cost,
   hosting, update strategy, reproducibility, repo structure, longevity risks) and
   surfaced trade-offs to decide.
2. **`/spec`** (spec-driven-development) — wrote `SPEC.md`: objective, phases,
   data model, File 1/File 2, budget, hosting, structure, boundaries. Approved
   before any code.
3. **`/plan`** (planning-and-task-breakdown) — `tasks/plan.md` + `tasks/todo.md`:
   vertical tasks with acceptance criteria, a dependency graph, and human
   checkpoints between phases.
4. **`/build auto`** (incremental-implementation + test-driven-development) — each
   task: write a failing test → minimal code → full suite green → `ruff`/`black`
   → one atomic commit. Network and the LLM are mocked in tests (no spend).
5. **debugging-and-error-recovery** — on any failure, diagnose the root cause from
   the traceback before changing code.

**To get the same help again:** open the repo in Claude Code, then drive it with
those slash commands. A good opening prompt:

> "Read `SPEC.md`, `docs/HOW_IT_WORKS.md`, and `docs/HOW_TO_UPDATE.md`. We work in
> the working/final-phase model. Continue with `/plan` then `/build auto`, TDD,
> atomic commits, and stop at each phase checkpoint for my review."

Ground rules the agent followed (keep them): open sources only, never fabricate
funding/cap-table numbers, never commit secrets, English everywhere except the
dashboard UI (Russian), and stop for approval at each phase checkpoint.
