# Final pass

The concrete checklist. Read `SKILL.md` for why any of it matters.

Run this before calling a phase or a project finished, and before any push that
changes what a visitor sees. Report what was found rather than fixing everything
silently — a name change or a moved file is visible, and visible changes are the
owner's call.

---

## Look at it the way a stranger does

Open the repository page and stop. Before reading anything you already know:

- [ ] Does the first screen say what this is and what a person could do with it?
- [ ] Is there a link to the live thing, if there is one?
- [ ] Does the root show blocks, or does it show a pile of files?
- [ ] Does the commit column read as sentences, or as `wip` / `fix` / `update`?
- [ ] Is there anything here that is obviously a leftover — a draft, a scratch
      file, a `test2.py`, an untitled notebook?

## The root

- [ ] Only readme, dependency and packaging files, entry point, licence, ignore
      rules, and folders.
- [ ] Every other file lives in a block.
- [ ] Nothing was moved that the platform pins in place (CI directories, host
      configuration, the dependency file).
- [ ] Names are consistent — one lowercase-with-hyphens name per thing;
      machinery stays lowercase or dot-prefixed.

## Prose

- [ ] No count that changes on rebuild appears in a description of what the
      project *is*.
- [ ] Every measurement that keeps its number carries its date or run.
- [ ] No two documents answer the same question.
- [ ] No plan, open question or queue of drafts on the landing page — working
      material sits in the one working file.
- [ ] The README's first paragraph would make sense to someone who has never
      heard of the project.
- [ ] Links resolve. Internal links still point at files that exist.

## Commits

- [ ] Subjects are plain sentences, capitalised, no trailing period, no prefixes
      or ticket codes, ideally under about fifty characters.
- [ ] Detail is in the body, not crammed into the subject.
- [ ] No commit mixes a reformat with a change of meaning.
- [ ] Machine-generated commits follow the same rule.

## Platform surface

- [ ] Unused tabs and panels switched off (wiki, projects, packages, deployments).
- [ ] Description filled in.
- [ ] Link to the live thing set.
- [ ] Topics set.
- [ ] A release marks the finished state, if the project has reached one.
- [ ] Anything only the owner can do in the interface is handed over as exact
      clicks and exact text to paste.

## Hygiene

- [ ] No secrets anywhere — code, notebooks, examples, commit history.
- [ ] No produced data deleted; dated outputs kept as an archive.
- [ ] Tests and linters green on the branch that will be pushed.
- [ ] The main branch equals what is deployed.
- [ ] Temporary branches from risky work are gone.

---

## Reporting what you found

Sort by what a visitor notices first, not by what is easiest to fix. A stale
number in the README outranks an untidy folder name three levels down, because
one is read and the other is not.

Fix outright errors and report them. Anything visible — a rename, a moved file,
different wording in something a reader meets — is a proposal, not a change.
