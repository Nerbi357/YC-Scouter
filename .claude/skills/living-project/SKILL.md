---
name: living-project
description: Shapes a project as a strong trunk with many well-finished branches, built wide before deep, so new methods, sources and formats attach later without rewriting what exists. Use when starting a project that will run for weeks or months and keep growing; when a project should serve several audiences at once (a paper, a portfolio, real users, a curious stranger); when the owner does not yet know the final shape and wants a construction kit rather than one finished result; or when an existing project has stalled, sprawled, or stopped generating new options. Triggers on "build this wide", "leave room for more branches", "make it a living project", "several versions like revisions of a paper", "I want to be proud of this".
---

# Living project

A project shape for work that will keep growing. The goal is not one polished
result but **a structure that carries many** — a strong trunk with branches that
are each finished, and to which new branches attach cheaply.

Use it from the first message of a project. Retrofitting this shape is expensive;
that is the whole point of it.

---

## 1. The prime rule

> **Build wide before you build deep. Every step must make the next step cheaper.**

Before building anything, ask what it will be reused for. A step that has to be
undone or rewritten to add the next branch was the wrong step. The test of the
architecture is not elegance — it is whether a new method, source, audience or
output can be added later while touching almost nothing that already exists.

Corollary: **do not go deep on the first idea.** The first idea is rarely the best
one, and depth taken early forecloses branches that were still cheap.

---

## 2. The eight principles

1. **A strong trunk with many well-finished branches.** Not one deep result.
2. **New branches attach without surgery.** Design for that before it is needed.
3. **A branch that fails is still a branch.** If ten approaches do not combine into
   one, that is ten small studies, each written up honestly. A cleanly measured
   negative result is part of the deliverable, not an embarrassment.
4. **Write down what you are not doing.** Everything considered and deferred goes
   into an ideas file with the reason. The point is not tidiness — the project
   should always have a **visible menu of what could come next**.
5. **Judged by several audiences at once.** A finished project should work
   simultaneously as material for a paper or write-up, a portfolio piece, something
   a non-specialist can play with, something worth arguing about with a colleague,
   and something the owner understands end to end. When a choice serves one and
   costs another, say so and let the owner choose.
6. **Established methods are the floor, not the goal.** They belong in the project
   as baselines, so anything new has something to beat. But a project whose
   contribution is "I ran the standard method" is not the goal — push every phase
   for at least one thing that is genuinely new, unusual, or under-explored.
7. **Keep proposing.** At the end of every phase, bring new branches. A project
   that stops generating options is finished whether or not it is done.
8. **The owner's interest is a success criterion**, ranked alongside the technical
   ones. If a direction is correct but boring, say it is boring and offer the
   version of it that is not.

---

## 3. The architecture that makes branching cheap

The generic pattern. Adapt the layer names; keep the property.

**Layers with stable interfaces.** Break the work into a small number of layers
where each one only knows the layer below it. A new idea then attaches at exactly
one layer and touches nothing else. Typically:

```
sources      →  what came in, exactly as it came in, plus provenance
normalised   →  cleaned and given a common shape
derived      →  everything computed from the normalised layer
joined       →  the derived layer aligned with whatever it is being related to
questions    →  one declarative record per question asked
presentation →  reads the questions layer, never the layer below it
```

**Two properties do almost all the work:**

- **The derived layer is long, not wide.** Key it by *what produced the value*:
  `(item_id, method_id, dimension, value)`. Then **adding the eleventh method is an
  insert, not a code change** — no new column, no migration, no downstream edits.
  A wide table with one column per method forces a schema change for every new
  idea, and that friction is exactly what stops projects from going wide.
- **A question is a config, not code.** Represent each question or experiment as a
  declarative record — which inputs, which target, which subset, which validation —
  that a single runner executes into a standardised result. Then **the fortieth
  question is a config file**, and results are comparable by construction because
  they all came out of the same runner.

**Presentation reads results, never internals.** Charts, reports and any interface
consume the questions layer. That way rebuilding a method never breaks a figure,
and a figure never quietly depends on a model's internal state.

**Refresh is incremental and idempotent.** Re-running months later must extend the
work, not rebuild it, and must not corrupt it if interrupted. Record provenance
with everything: where it came from, when it was fetched, and a content hash.

---

## 4. How the work is sequenced

**Plan epochs, not tasks.** An epoch is a coherent stage that produces something
demonstrable. Tasks appear only when their epoch opens — a detailed task list
written months early is a work of fiction.

For each epoch state three things:

- **what must be agreed before it starts** — these are the real decision points;
- **what it produces**;
- **what it deliberately leaves out.**

**The typical arc:**

```
E0  Foundation ....... architecture, layout, the reproducibility contract
E1  The trunk ........ the whole pipeline end to end, at deliberately naive settings
E2  Do it properly ... the corrections that make the naive version defensible
E3+ Branches ......... deliberately unordered
En  Finish ........... write-up, release, polish
```

**Epochs after the trunk are deliberately unordered.** Once E0–E2 stand, branches
attach independently and get built in whatever order is most interesting at the
time. That is the point: **choose the next branch, do not work through a queue.**

**Build the deliberately naive version first, and report its failure.** The
simplest possible end-to-end version usually does not work. Run it anyway, publish
that it did not, and use the failure to motivate everything after it. It is the
honest opening of any write-up, it proves the pipeline works before the modelling
starts, and it stops the project from mistaking complexity for progress.

**Order decisions by how much depends on the answer**, and say which are blocking.
Ask the blocking ones early and plainly; decide the rest yourself and say so.

**Identify what cannot be done retroactively, and start it immediately.** Every
project has a few of these — recording something that only exists going forward,
snapshotting a source that will change, capturing a baseline before an
intervention. They are usually cheap and always impossible to recover later. Find
them in the first hour.

---

## 5. Two tiers of idea, delivered at different moments

Separate them explicitly and never mix them into one list.

| Tier | What it is | When to raise it |
|---|---|---|
| **Actionable now** | doable within the next three to five steps; makes current work better or cheaper | **inline**, in the message it occurred to you |
| **Idea-level branch** | a new method, angle, audience or format | **at the close of a phase or branch**, when there is room to choose |

Raising branch-level ideas mid-work is noise. Raising them at a boundary is often
the most valuable thing produced in the whole session. Both tiers live in the ideas
file with a status marker: open, proposed, decided, or set aside with the reason.

**Look one step wider than the question.** When a task finishes, inspect what sits
next to it and say what would improve it. Keep it useful rather than noisy by
three rules: it must touch what was just done, it must be concrete enough to accept
or reject in one line, and it is a proposal — never a change made unilaterally.

---

## 6. The reproducibility contract

**Treat the repository as a chain of checkpoints.** After every meaningful step,
phase or decision, the owner must be able to reproduce the result **from the
repository alone**, on their own machine, without the agent's working environment.

That means, concretely:

- the executable path is **visible and runnable**, not hidden in an agent's shell
  history;
- every artefact lands in a **declared folder**, decided in advance;
- the environment is **pinned**;
- anything needing a key or costing money is **isolated and labelled**;
- a step that genuinely cannot be re-run is **said to be so, out loud, with the
  reason**;
- **when it is not obvious where a file belongs, ask.** A misplaced artefact is
  cheap to move now and expensive to find later.

**Where the logic lives — the rule that resolves the "notebooks vs library"
argument.** Put **infrastructure** in the importable, tested library: fetching,
parsing, storage, plumbing. Nobody wants to read it, everybody wants it to behave
identically everywhere. Put **everything contestable** in the visible, executable
narrative: how a thing is defined, how a sample is chosen, what is assumed, how a
result is validated.

> **The test: if a decision can be argued with on the merits, it is visible. If it
> is merely "this must be done correctly", it is in the library.**

This gives reproducibility *and* comprehensibility, and stops the fifth branch from
being a copy-paste of the first.

**Commit the fragile inputs, rebuild the stable ones.** Anything that a source
might change or remove gets committed. Anything reliably re-fetchable is
re-fetched. Never delete produced output — dated outputs are an archive.

---

## 7. The product layer is first-class

If the project has any audience beyond the owner, the visible layer is not a
garnish added at the end. Design it early even if it is built late.

**The bar: it must read as a finished product, not as the output of a working
file.** Someone arriving with no context should understand within twenty seconds
what it shows and want to touch something. If it looks like a dashboard someone
built for themselves, it has failed.

**Interesting, not merely informative.** The test: does a person *do* something,
get a result they did not expect, and want another go? Output that is merely
correct fails this test. Interaction that changes what someone believes passes it.

**Honesty is a constraint, not a disclaimer.** If the work produces estimates,
anything that returns a number to a user must make unmistakable what that number
is and is not. Uncertainty belongs in the design, not hidden behind it. A demo that
quietly overclaims is worse than no demo.

**Sequencing that works:** find the piece that needs only the earliest artefacts
and build it first — it gives the project something visible and satisfying long
before the substance is finished. Prefer **static-first**: precompute and serve
plain data, so there is no server to attack and no bill to pay. Add anything live
only when it earns its place, and only after a hostile-input pass.

---

## 8. Research and verification discipline

For any claim that will be built on:

- **Mark confidence on every fact**: verified directly / seen but not verified /
  recalled and unchecked / your own inference. Mixing these silently is how a
  project ends up built on a plausible-sounding fabrication.
- **Never invent a specific.** A URL, a price, a version, a date, a coverage range
  recalled from memory and presented as checked is worse than an admitted gap,
  because it fails silently and late.
- **Report what could not be verified**, and why, rather than filling the hole.
- **Distinguish a blocked check from a negative result.** If the environment
  prevented verification, that says nothing about the thing being verified.
- **Check the free option before paying**, and check whether someone has already
  built the thing before building it. A published, maintained artefact usually
  beats a private reimplementation, and finding one is often the single
  highest-value hour of the project.

---

## 9. Using agents

**Roles.** Idea generator, scout, architect, executor, tester, adversary, reviewer,
researcher, verifier, replicator, devil's advocate, simplifier, documenter,
teacher, curator. Switch deliberately between them even when played in sequence.

**Shapes worth assembling them into:**

| Shape | What it is | Use when |
|---|---|---|
| Fan-out | several researchers on *independent* questions | the unknowns do not depend on each other |
| Pipeline | each item passes through stages without waiting for others | many similar items, several steps each |
| Adversarial panel | N verifiers per finding, each told to *refute* | a wrong finding would be expensive |
| Diverse lenses | verifiers given *different* angles, not the same one | it can fail in more than one way |
| Judge panel | several independent attempts, scored, best synthesised | the solution space is wide |
| Loop until dry | keep going until N rounds find nothing new | the number of things to find is unknown |
| Completeness critic | a final agent asked only "what is missing?" | before declaring any survey finished |
| Clean-room replication | one agent rebuilds knowing only the inputs | reproducibility claims |

**Two moments justify a large parallel run:** discovery (mapping the option space
at the start) and adversarial audit (attacking a finished piece). Everything else
is usually faster as one focused pass.

**Every brief contains five things:** the *question* rather than the task; what
done looks like including the output shape; **an explicit budget**; what to do when
something cannot be verified (say so, do not fill it in); and what not to touch.

**Standing lessons.** Parallel agents share the session's budgets, network policy
and rate limits — a wide fan-out can leave later agents unable to verify anything.
A blocked request says nothing about the target. Read reports as evidence, not
truth: agents are confidently wrong in the same ways you are.

**Never delegate:** conceptual decisions, the project's narrative, or anything
where the owner's judgement is the input.

---

## 10. Versions, and the closing of a phase

**Ship versions like successive revisions of a paper**, each extending the previous
baseline rather than replacing it. Tag them. Keep a changelog a stranger can read.

**A branch is done when** it has a stated goal, a demonstrable result, tests or
checks covering what it introduced, an honest account of what went in and what was
deliberately postponed, and the owner's approval.

**At every phase boundary:** run the full technical pass; attack the work
deliberately before calling it finished; report what needs attention; and bring the
next set of branches.

**In the final phase the standard is not "it works" but "nothing here looks like a
workbench."** No leftover working files, no drafts, no clutter, tidy names, and no
visible traces of the process that built it. Judge it the way a first-time visitor
sees it. The ideas file **stays** — it is the visible roadmap of what could come
next, and it is part of what makes the project look alive rather than abandoned.

---

## 11. Anti-patterns

- Going deep on the first idea before the project has gone wide.
- Building a step that must be rewritten to add the next branch.
- A wide table with one column per method — the schema change that quietly stops
  the project from growing.
- Many started branches and none finished. Breadth is the goal; **unfinished**
  breadth is the failure mode. Every branch gets a definition of done before it
  starts.
- Losing an idea because there was no place to put it.
- Hiding a negative result instead of publishing it.
- Calling something reproducible without reproducing it from a clean state.
- Presenting recalled specifics as verified facts.
- Adding a ninth idea when the useful move is to attack the eight that exist.
- Treating the visible layer as decoration to be added at the end.
