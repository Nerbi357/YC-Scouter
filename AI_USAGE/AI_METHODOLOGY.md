# How YC Scouter was built with an AI agent

A concrete account of one project: what the AI actually did, the real prompts and
the constraints written into them, what the cost controls were, how the work was
verified, and which failures shaped the result. It is written for a reader who
wants to see the method applied rather than described in the abstract.

*The portable version of the method — the rules an agent should follow on any
project — lives in [`../FOR_AI/AI_INSTRUCTIONS.md`](../FOR_AI/AI_INSTRUCTIONS.md).
The skills that were used are listed in [`SKILLS_USED.md`](SKILLS_USED.md).*

---

## 1. What the AI did, and what it did not

| Done by the owner | Done by the agent |
|---|---|
| The idea, the scope, every product decision | Implementation, tests, documentation drafts |
| Which data source, which model, what budget | The pipeline, the cache, the dashboard |
| Every user-visible decision (filters, card layout, wording) | Everything invisible: structure, naming, refactoring |
| Approval of each phase | Verification, measurement, adversarial audits |

The agent never chose what the product *is*. It chose how to build what had been
agreed, and it was expected to report anything it decided on its own.

## 2. The pipeline the agent built

Two runnable units and a reader, deliberately separated:

```
File 1  collect  → dated Base   (free, repeatable, no keys)
File 2  enrich   → dated AI     (costs money, needs a key, resumable)
app.py  read     → dashboard    (never fetches, never pays)
```

The separation is the point. Collection can be re-run any time at zero cost;
enrichment is where money is spent, so it is a separate button with its own guard
rails; the dashboard is a pure reader and therefore cannot break the data or spend
anything.

## 3. The prompts, verbatim

Everything the model is asked lives in one module (`src/yc_scouter/ai.py`). Two
fields per company, nothing else.

**System prompt:**

```
You are a venture analyst. Using ONLY the facts provided, return a single JSON
object with:
  "description": 6-7 sentences — what the company does, the core idea, what is
                 distinctive, its strengths, and useful factual details.
  "risks": 1-2 short, concrete risks worth checking.
Do NOT invent facts, numbers, funding, valuations, traction, or metrics.
Return JSON only.
```

**User prompt** — the company's own published fields, nothing else:

```
Name: {name}
One-liner: {one_liner}
Industry: {industry} / {subindustry}
Tags: {tags}
Status: {status} | Team size: {team_size} | Batch: {batch} | Stage: {stage}
Description: {long_description truncated to MAX_DESC_CHARS}
```

### Why each constraint is there

| Constraint | Reason |
|---|---|
| **"Using ONLY the facts provided"** | The dataset must never contain a number the source does not publish. This is the difference between a tool and a rumour generator. |
| **Exactly two output fields** | Every extra field is money and another place for the model to speculate. The one-liner is not generated at all — YC's own is better and free. |
| **`"risks"` = 1–2, short, concrete** | An open-ended request produces generic filler ("competition is fierce"). A bounded one produces something worth checking. |
| **JSON only, named keys** | Parsed defensively: a model may return a list where a string is expected, so list values are joined on the way in rather than stored as a Python repr. |
| **`temperature = 0`** | Same input, same output — a dataset is reproducible from its inputs. |
| **`MAX_DESC_CHARS = 2200`** | A character cap on the input *is* a cost cap: ≈ 780 input tokens per company. |
| **`MAX_TOKENS = 430`** | Enough for both fields with headroom, ≈ 260 output tokens. |
| **One model per run, recorded in the output** | Any row can be traced back to what produced it. |

## 4. Cost control: the cache is the design

Every result is stored under a three-part key:

```
(company_id, model_id, prompt_version)
prompt_version = sha256(SYSTEM_PROMPT + USER_TEMPLATE)[:12]
```

Consequences, all of them deliberate:

- a **re-run pays only for companies that are new** — the last full run of 4040
  companies cost ≈ $7.14; the refresh that followed it cost ≈ $0.005 for 3 new
  companies;
- a **crash mid-run is harmless** — the next run resumes from the cache;
- **editing a prompt re-summarises everything on purpose**, because the fingerprint
  changes, and old results are kept rather than overwritten;
- **switching models re-summarises once**, and the dataset records which model
  produced each row.

The summarizer prints a running cost estimate and never halts on a budget: the
owner is told the number and decides.

Before spending anything, a **preflight** checks that the key exists, that it is
accepted, that there is credit, and that the configured model still exists — the
four failures that otherwise all look identical from the outside ("the job died
halfway through"). It costs one token.

## 5. How the work was verified

Three layers, because each one is blind to something:

1. **Unit tests** (161, network and LLM mocked, so a run costs nothing) — logic,
   edge cases, and one regression test per bug ever found.
2. **Notebook smokes** — the real notebooks executed headlessly against a fixture,
   so a broken notebook fails in CI rather than in Colab.
3. **Browser checks** — the real app driven in a real browser against the real
   4040-row dataset, asserting what a user would notice: this element is clickable,
   the card matches the row that was clicked, a note typed into the UI reached
   storage.

Layer 3 exists because of a specific failure: a CSS change moved an export control
onto the tab bar and made **all four tabs unclickable**, while every unit test
stayed green. Unit tests cannot see a button covered by another element.

## 6. The adversarial audit

Before the project was called finished, several agents attacked the dashboard in
parallel with different lenses — correctness, data integrity, access, resilience —
each blind to what the others were doing. Every candidate finding was reproduced
independently before anything was fixed, and fixes were ordered by blast radius.

The ten confirmed critical findings, as an illustration of what this kind of pass
actually catches:

| What was found | Why it mattered |
|---|---|
| A failed read of the notes store made the next save write emptiness over it | Every note lost, silently |
| The store was cleared *before* the new content was written | A crash in between left it blank |
| A blank or misspelled owner password made every visitor an owner | Strangers could edit the owner's data |
| One duplicated id in the dataset produced two identical widget keys | The whole dashboard died |
| A missing column after a rebuild raised an error inside a chart | Blank crash page instead of a message |
| The selected table row was remembered by *position* | After a filter change the card opened a different company |
| Two companies sharing a name broke the comparison view | 108 such rows existed in the live data |
| Searching for `[` returned all 4037 companies | List columns come back as arrays; the search matched the array's repr |
| An unknown team size counted as zero | Companies passed an explicit "up to N" filter they should not |
| The shared sheet was read on every rerun | A network round-trip per keystroke |

Each fix landed as its own commit with a test that fails without it.

## 7. Measurement, including the negative result

Performance work was done by measurement, not intuition, on the real dataset.

- Opening a company card: **1.10 s → 0.40 s**. Two causes: a redundant rerun (the
  table widget had already rerun the script) and the fact that every click
  repainted all four tabs. The table and the card now render in a single fragment.
- The card list: **~350 interactive elements → 132** by putting per-card note
  editors behind a button; the tab renders in 0.8 s.
- **A change that did not work:** paginating the bulk notes editor was expected to
  be the big win and measured **1.06 s → 1.12 s** — nothing. It was reverted, and
  an ablation showed the real cost was elsewhere (chart building ≈ 0.36 s, card
  expanders ≈ 0.16 s, the editor ≈ 0.03 s). The negative result is recorded in the
  project's plan so nobody retries it.

Pure data work across the whole page is ~75 ms; almost all of a rerun is the
framework serialising elements to the browser. That is the kind of fact that only a
measurement produces — and it changed what was worth optimising.

## 8. Failures worth remembering

Told plainly, because they shaped the rules:

- The hosted environment ran a **newer pandas** than the pinned local one; two
  crashes followed (booleans arriving as strings from the spreadsheet, text written
  into a column inferred as float). Fix: tolerant coercion at the boundary, and
  testing against the newer version.
- A CSS tweak intended to move a control **made the navigation unusable**; it was
  caught by the audit, not by tests, and led to layer 3 above.
- Two workflow runs failed with a **zero-job startup failure** — a platform outage
  coinciding with a repository rename, not a code fault. Re-running the same file
  succeeded unchanged. Diagnosing "not our bug" is part of the job.
- An early version keyed personal notes by the company **slug**; slugs change when
  a company is renamed, which orphans notes. Everything was migrated to the
  immutable id, and that is now the first rule of the playbook.

## 9. What the reader can take away

1. Separate what is free and repeatable from what costs money.
2. Key user data to something that cannot change.
3. Make the cache — not willpower — the cost control.
4. Forbid invention explicitly in the prompt, and bound the input to bound the cost.
5. Verify where the user actually is, not only where the tests are.
6. Attack your own work before calling it done, and reproduce a finding before
   fixing it.
7. Measure, publish the negative results, and never optimise by intuition.
