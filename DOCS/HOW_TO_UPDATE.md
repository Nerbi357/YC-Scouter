# How to update & maintain YC Scouter

This is your **final-phase checklist**. In normal use you press two buttons every
few months. This file lists the few things that need occasional attention, with
concrete steps. Keep it open when you do maintenance.

## Routine: refresh the data (the normal case)

1. **GitHub → Actions → "Build Dataset (File 1)" → Run workflow.** Rebuilds the
   full Base (all companies 2020→now) and commits the dated files. No keys needed.
2. **GitHub → Actions → "Build AI Summary (File 2)" → Run workflow** (choose
   `claude` or `groq`). Adds `ai_description`/`ai_risks` for **new** companies only.
   Needs `ANTHROPIC_API_KEY` (or `GROQ_API_KEY`) in repo Secrets.
3. The dashboard redeploys automatically on the commit. Your notes are untouched
   (they live in an external store keyed by company `id`).

> Prefer Colab? Open the two notebooks and Run all, with the top switch set to
> `drive` or `download`. Same result; the buttons just do it server-side.

## The third button — measure Form D coverage (a spike, not a refresh)

**Actions → "Measure Form D coverage (spike)" → Run workflow.** Free, needs no key,
and writes nothing to any dataset: it asks SEC EDGAR how many companies from the
newest dataset can be found among Form D filers, and commits one report to
`data/spikes/`.

- **Sample size** is an input; 200 is the default and takes a couple of minutes.
- **Set the repository secret `SEC_USER_AGENT`** to a string containing a contact
  address, e.g. `YC-Scouter research (you@example.com)`. This is not optional in
  practice: the first run (2026-08-04) was refused with HTTP 403 for every company
  because SEC declines automated clients that do not declare a contact. The run now
  detects that on its first request, stops, and says so — it never reports a refusal
  as "no filings".
- The four outcomes mean exactly what they say: *matched* is one filer with that
  name (evidence, not proof of identity), *ambiguous* is several filers (never
  resolved by choosing one), *none* is no filer at all, and *error* is a failed
  request — **which says nothing about the company**.

It is a measurement, not part of the routine: once the question it answers is
settled, this button and its notebook go away.

## The preflight: File 2 tells you what is wrong before it spends

File 2 checks the AI provider **before** the loop over companies starts, with a
single one-token request: is the key present, is it accepted, is there credit left,
and does the configured model still answer. That one call is deliberately the whole
test — it exercises exactly what the run will. The four classic failures become a
named message on the first line of the log, for example:

```
Preflight failed: the model 'claude-haiku-4-5' is not available any more. Pick a
current one and change the model constant in src/yc_scouter/config.py.
Available now: claude-opus-5, claude-sonnet-4-5-20250929, ...
```

> The provider's *model listing* is **not** used as the gate. Aliases such as
> `claude-haiku-4-5` are valid for calls but need not appear in the listing, which
> carries the dated snapshots (`claude-haiku-4-5-20251001`). Gating on the listing
> once blocked a run that would have worked; the listing is now only used to enrich
> the message when a model really is gone.

So a broken run stops in ~10 seconds with an instruction instead of dying halfway
through a few thousand companies. A network blip is only a warning and never blocks
a run that would otherwise work. (Pass `check_first=False` to `build_ai` to skip it.)

**Turn on GitHub's own alerting once:** GitHub → your avatar → **Settings →
Notifications → Actions** → *Send notifications for failed workflows only*. Then any
failed button run reaches you by email without anyone watching the Actions tab.

## Things to watch (and exactly what to do)

| When | Symptom | What YOU do |
|---|---|---|
| **Anthropic credits run low** | File 2 fails with `402 insufficient_credits` | Top up at platform.claude.com; File 2 is resumable (re-run continues via cache). Set a usage alert. |
| **Model retired** (~every 6–12 mo) | `model not found` / 404 | Edit **one line** in `src/yc_scouter/config.py` (`CLAUDE_MODEL` or `GROQ_MODEL`). Note: a new model = new `prompt_version`-independent `model_id`, so those companies re-summarize once. |
| **Groq key rotated / limit** (if you use Groq) | `401` or `429` | Regenerate the key at console.groq.com, update the `GROQ_API_KEY` Secret. Free tier ~1,000 req/day, so a cold backfill spreads over a few days. |
| **Dependencies drift / break** | install error, or behavior changed after months | Re-lock: `uv pip compile pyproject.toml --generate-hashes -o requirements.txt`, then run `pytest` and commit. This is the reproducibility anchor. |
| **yc-oss source changed** | File 1 fetch/normalize error | Check `https://yc-oss.github.io/api/companies/all.json` is up and its fields; adjust `src/yc_scouter/normalize.py` if a field was renamed. |
| **Streamlit app "sleeping"** | first visit is slow (~15 s) | Normal for the free tier after 12 h idle; just click to wake. |
| **Notes must survive hosting** | notes vanished after a redeploy | Notes must be in **Google Sheets** (see `DOCS/HOW_TO_DEPLOY_DASHBOARD.md`), not a local CSV. Verify once after setup. |

## Change the AI prompt (and refresh all descriptions on purpose)

Edit `SYSTEM_PROMPT` / `PROMPT_TEMPLATE` in `src/yc_scouter/ai.py`. The
`prompt_version` fingerprint changes automatically, so the next File 2 run
re-summarizes every company under the new prompt (old results are kept in the
cache, never overwritten).

## Rotate / change an API key (steps)

1. Create the new key (platform.claude.com or console.groq.com).
2. GitHub → repo → **Settings → Secrets and variables → Actions** → update
   `ANTHROPIC_API_KEY` / `GROQ_API_KEY`.
3. For local/Colab runs, set the key as a Colab secret / shell variable.
4. Re-run File 2. Done — no code change needed (keys are never in code).

## Migrate old notes (one-off, if you had slug-keyed notes)

```python
from yc_scouter import user_data
user_data.migrate_slug_to_id("old_user_data.csv", "data/yc_dataset_base_<date>.parquet")
```
Maps your old slug-keyed notes to the immutable `id`, backs up the old file to
`*.slug.bak`, and writes the new store.

## Let an AI agent do the maintenance for you

Open the repo in Claude Code and paste one of these:

- **Refresh model after a deprecation:** "The model `<old-id>` is deprecated.
  Update the model constant in `src/yc_scouter/config.py` to `<new-id>`, run the
  tests, and commit. Explain the cost impact of the one-time re-summarization."
- **Re-lock dependencies:** "Recompile `requirements.txt` from `pyproject.toml`
  with hashes, run `pytest`, and commit if green. List any version bumps."
- **General checkup:** "Read `DOCS/HOW_TO_UPDATE.md`. Check for deprecated models,
  drifted deps, and yc-oss schema changes. Report what needs my attention."
