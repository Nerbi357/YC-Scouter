# SIGNALS — how the work goes

Raw observations about the collaboration, written when they happen, kept for a later
review of the skill library. A signal is material, not a decision: nothing here has
changed any rule yet. See `.claude/skills/signal-capture/SKILL.md`.

Kinds: `correction` · `friction` · `worked` · `gap` · `caught`.

---

## 2026-07-27 · worked · initiative
What happened: after finishing the repository-page cleanup I also pointed out that the
empty Wiki and Projects tabs were part of what a first visitor sees. The owner named
this the most valuable part of the collaboration, not the requested work itself.
Verbatim: "круто не только то, что ты разобрал что видит пользователь, но и предложил
улучшения, которые я тебя не спрашивал и о которых я вообще не думал, но которые очень
близки к тому, что мы делаем" — *"what is great is not only that you worked out what
the user sees, but that you proposed improvements I had not asked for and had not
thought about, yet which are very close to what we are doing"*.
Candidate: already written into `AI_INSTRUCTIONS.md` §5a as "look one step wider than
the question", with the three limits that keep it from becoming noise.
Confidence: high — his own words, unprompted.

## 2026-07-27 · correction · language of the guidance
What happened: asked to remove mentions of one specific language, I replaced them with
the phrase "the author's language". He rejected the replacement as worse than the
problem.
Verbatim: "так нет, стало хуже… просто аккуратно убери упоминания русского языка" —
*"no, it got worse… just remove the mentions cleanly"*.
Candidate: when asked to remove something, remove it. Substituting a paraphrase is a
new rule the owner did not ask for.
Confidence: high.

## 2026-07-27 · correction · unrequested visual work
What happened: I produced two dashboard screenshots for the README, verified they
looked right, and shipped them. He did not want them at all.
Verbatim: "мне не нравятся скриншоты, убери их из ReadMe" — *"I do not like the
screenshots, remove them from the README"*.
Candidate: a format choice (image vs text) is a conceptual fork and belongs in the
options round, even when the content itself was requested.
Confidence: medium — he had approved "screenshots" in the abstract, so the miss was in
not showing them before wiring them in.

## 2026-07-27 · caught · a guard that blocked correct work
What happened: earlier in the project the preflight check gated File 2 on the
provider's model listing, and an alias that is valid for calls but absent from the
listing stopped a run that would have worked.
Source: mine, not his.
Candidate: a guard that can block correct work needs the same adversarial thinking as
the thing it guards. Recorded in `PROJECT_MEMORY.md`.
Confidence: high — reproduced and fixed with a regression test.

## 2026-07-27 · friction · verification blocked by the sandbox
What happened: while researching data sources, the session's egress policy refused
`sec.gov`, `api.github.com` and `hn.algolia.com`. The risk was reporting those as
"unavailable" rather than "not checkable from here".
Source: mine.
Candidate: written into `AI_INSTRUCTIONS.md` §7a — a blocked check says nothing about
the target, and confidence marks travel with every fact.
Confidence: high.

## 2026-07-27 · gap · the project outgrew its own shape
What happened: the owner asked to expand a finished single-source tool into a
multi-source product with a public site, profiles, a feed and eventually accounts —
and supplied the `living-project` skill for it in the same message.
Verbatim: "я хочу, чтобы мы сделали проект так, чтобы мы могли все делать по шагам,
заранее продумывая все развилки" — *"I want the project built so that we can do
everything step by step, thinking the forks through in advance"*.
Candidate: none yet — the shape is now `living-project`'s job. Worth reviewing after
E0 whether the skill needed anything this project exposed.
Confidence: high.
