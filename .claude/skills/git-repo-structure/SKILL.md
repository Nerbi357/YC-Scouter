---
name: git-repo-structure
description: Keeps a repository structured and named so it reads as a finished product rather than someone's working desk. Use continuously while creating or moving files, naming things, choosing branches, or writing commit messages — not only at the end. Use when deciding where a new file belongs, when the root is filling up, before pushing anything, and before calling a project done. Use when writing a README, a folder name, or any text a first-time visitor will meet.
---

# Git repository structure

**What changes because of this skill:** without it, a repository reads as a
workbench — drafts left lying about, clutter in the root, a commit column full of
"wip" and "fix", numbers in the documentation that stopped being true two rebuilds
ago. With it, the landing page, the file listing and the commit column read as a
product someone built deliberately.

**Covers:** everything a person sees when they arrive at a repository — layout,
names, prose, commit subjects, and the hosting platform's own surface.
**Leaves out:** the quality of the code inside, which is review; and being able to
re-run the work, which is reproducibility. A web or product interface is a
neighbouring surface with its own rules, added later.

---

## 1. The standard

> In the final phase the bar is not "it works" but **"nothing here looks like a
> workbench."**

Judge the repository the way a first-time visitor sees it: the landing page, the
file listing, the README, the commit column beside each file. Whatever reads as
noise gets fixed. "It is only for me" is never a reason to leave a rough edge —
**every project is built to be a finished, professional product or solution**,
whoever it turns out to be for.

### Two stages, and the default is final

A repository is in one of two states, and knowing which one you are in settles
most arguments about whether a file belongs.

**Final** — the repository contains only what the product it delivers actually
needs. No working files, no scratch branches, no service artefacts, no drafts.
Anything a visitor could mistake for leftovers is gone, because it is.

**Working** — a temporary state where service files, working branches or
provisional names are permitted **because they buy something specific**. Each one
is justified, each one is minimal, and each one has a stated end.

> **Build as though the project were already final.** The working stage is a
> deliberate, bounded departure — not the normal condition that gets tidied up
> later.

That ordering matters because the alternative is what actually happens by default:
clutter accumulates as a byproduct, nobody decides to add it, and by the end
nobody can tell which files were meant. When a working-stage departure genuinely
pays — a scratch branch for something risky, a provisional name while the shape is
unsettled — say so out loud, say what ends it, and end it.

Entering the final stage is a real step, not a mood: working branches deleted,
service files removed, provisional names replaced, and the file listing read
straight through as a stranger would read it.

## 2. A minimal root

The landing page shows blocks — folders — plus only the files that must be there:
readme, dependency and packaging files, the entry point, licence, ignore rules.

**A new file goes into a block, never into the root.** When it is not obvious
where a file belongs, ask. A misplaced artefact is cheap to move now and expensive
to find later.

**Check platform constraints before moving anything.** Some paths are dictated —
CI workflow directories, host configuration, the dependency file — and moving them
silently breaks deployment.

## 3. Names

Names say what the thing is for, not what category it belongs to, and one thing
keeps one name everywhere it appears — folder, configuration, invocation. Human
names are lowercase-with-hyphens unless the platform pins a form (`README.md`,
`LICENSE`); service folders stay lowercase or dot-prefixed.

## 4. Commit subjects are part of the finished look

The repository page prints the subject of the last commit that touched each file,
next to that file, permanently. **Those lines are read far more often than the
diffs beneath them.** Write for that column:

- one short sentence in plain words, capitalised, no trailing period;
- no ticket codes, no `wip:` or `T4.3:` prefixes, no file names;
- ideally under about fifty characters;
- the detail goes in the body, which the listing never shows.

Machine-generated commits obey the same rule — a scheduled job's message is what a
visitor sees next to the folder it writes to.

Good: `Explain the world the data comes from` · `Drop the screenshots, tighten the
honesty section`
Bad: `wip` · `fix bug in app.py` · `T4.3: update`

## 5. Prose that does not go stale

**Keep drifting numbers out of descriptions.** A count that changes with every
rebuild — rows, tests, file sizes — must not appear where the text says what the
project *is*. It goes stale silently and ends up contradicting the other files.
Say "several thousand" and let the running system report the exact figure.

A **measurement keeps its number** as long as it carries the date or run it came
from: that is a fact about one moment and stays true forever.

**One document per job.** If two documents answer the same question, merge them. A
second document that re-answers an existing question is worse than no document,
because now they can disagree.

### The showcase and the working file

**The landing page shows the finished thing; working material lives in one
separate file.** The plan, the open questions, the rulings already made, drafts
waiting on a verdict, a queue of raw material — none of that belongs on the page
a first-time visitor reads. Describing a pile of unapproved drafts on the
showcase tells that visitor the project is unfinished, whatever the rest of the
page claims.

It is also the most reliable source of stale prose there is. A plan changes
weekly and a landing page is edited monthly, so a roadmap on the README is wrong
most of the time it is being read.

Keep it to **one** working file at the root, named for what it holds. It carries
what a person or a fresh session needs to resume the project — where things
stand, the plan, what has been decided — and the README points at it once,
for whoever maintains the project, rather than reproducing any of it.

## 6. The platform's own surface

A hosting platform adds tabs and panels the project never asked for — an empty
wiki, an empty project board, unused packages or deployments panels — and they are
part of what a first visitor sees. Switch off what the project does not use, fill
in what it does: the description, the link to the live thing, the topics. Mark a
finished state with a release, so the page reads as a product rather than a stream
of commits.

Some of this can only be done by the owner in the platform's interface. Hand over
the exact clicks and the exact text to paste (see the working agreement on
step-by-step instructions).

## 7. Hygiene that is not negotiable

- **Secrets never enter the repository** — not in code, not in notebooks, not in
  examples.
- **Deleting produced data needs a reason and the owner's word.** Dated outputs
  are an archive by default, and throwing one away is not reversible. But an
  archive of something that turned out useless is just clutter, and clutter is
  what the final stage exists to remove — so deletion is available, either because
  the owner approved it or because the necessity is plain and stated. What is not
  available is deleting it quietly.
- **Atomic commits**, each with tests and linters green, each explaining *why* in
  its body.
- **No commit mixes a mechanical reformat with a change of meaning** — the second
  cannot be reviewed when it is buried in the first.
- **A main branch that always equals what is deployed.** Whether a permanent
  working branch sits beside it is the owner's call; when there is only one
  branch, the checks carry the whole weight, and risky work gets a temporary
  branch deleted after merge.

## 8. Before calling anything finished

Run the pass in `references/FINAL_PASS.md`. It is the concrete checklist; this
file is the reasoning behind it.

---

## Owner preferences

- **Every project is a finished, professional product or solution**, regardless of
  who it is for. The universal success criteria: it does not break, it does what
  it was meant to do, it looks good and the repository is polished, and the owner
  has understood how it works and approved it.
- **He would rather have no working stage at all.** Service files and scratch
  branches are permitted when they earn their place, but the burden is on them —
  "it is temporary" is not a justification, it is a promise, and promises about
  cleaning up later are the ones least often kept.
- **The commit column is something he actively reads.** This rule entered the
  contract because he pointed out that the per-file commit subject on the
  repository page is part of how the project looks — not metadata.
- **One name everywhere** is his convention: a thing's folder, its configured
  name and the way it is invoked are the same lowercase-with-hyphens string, so
  nothing has an alias.
- **Ask where a file belongs** rather than guessing. He would rather answer a
  one-line question than find a stray file later.
- **Draft material never appears on the showcase.** This rule entered the skill
  when he found the review zone described on the README: raw material is working
  material, and working material has its own file.
- The finished state includes the platform surface — he considers an empty wiki
  tab or a blank About panel part of the product.
