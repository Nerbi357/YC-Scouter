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

## 2026-07-27 · worked · flagging a conflict instead of resolving it silently
What happened: installing `signal-capture` put a file in the root, which contradicts
the owner's own minimal-root rule. I installed it as the skill prescribes and named
the conflict in one line rather than choosing quietly. The ruling came back in six
words, and the rule is now settled rather than pending.
Verbatim: "оставь в корне, этому файлу можно" — *"leave it in the root, this file is
allowed"*.
Candidate: when two instructions collide, follow the more recent and specific one,
then surface the collision in a single line with the one-line undo. Cheaper than
either asking first or hiding it.
Confidence: medium — one instance, but it cost nothing and settled a standing rule.

## 2026-08-04 · caught · a run that failed 200 times before saying why
What happened: the first Form D spike returned HTTP 403 for all 200 companies. The
report recorded 200 errors — correctly *not* counting them as "no filings" — but it
had no idea why, because only the status code was kept, and it kept going after the
first refusal. The cause was ours: SEC refuses automated clients that do not declare
a contact address.
Source: mine.
Candidate: any client of an external service should (a) keep the body of a refusal,
not just its code, and (b) probe once before a batch, so a systematic block costs one
request instead of the whole run. Written into the module; worth generalising into a
skill.
Confidence: high — reproduced, and the fix is covered by tests.

## 2026-10-09 · caught · a cadence that depended on the owner produced nothing
What happened: on 2026-07-27 the owner chose a manual weekly refresh over a schedule
("давай пока регулярное обновление будет ручное, я сам буду запускать сбор данных
раз в неделю"). Ten weeks later: zero refreshes, and the one secret the Form D spike
needed was never set. I accepted the decision without naming its failure mode.
Source: mine — the decision was his, the silence about its risk was mine.
Candidate: when a plan step depends on the owner doing something routine, say the
base rate out loud and offer the automated version as the default, with the manual
one as the override. "Nothing scheduled depends on the owner" is now a design rule in
`SPEC.md` §13.
Confidence: high — one clean, dated instance.

## 2026-10-09 · worked · asking the owner what he actually does with the tool
What happened: question A4 of the interview ("what did you do with it in the last
month?") produced the most useful answer of the whole session.
Verbatim: "фактически сейчас единственное использование - это фильтр по категории и
потом перейти на рабочую ссылку" — *"in practice the only use now is the category
filter and then the outbound link"*.
Candidate: at every project start and every phase close, ask for the last concrete
use, not the intended one. It is the cheapest honest measurement of a product.
Confidence: high.
