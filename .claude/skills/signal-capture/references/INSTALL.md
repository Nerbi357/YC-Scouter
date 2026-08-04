# Installing signal capture into a project

The skill works on its own — a session that reads `SKILL.md` will keep the log.
The hook makes it reliable rather than remembered, which matters because a skill
is a request and a hook is a guarantee.

Both steps are optional and independent. Do the first; do the second when the
project is one you will come back to.

---

## 1. The skill

Copy this whole folder into the project:

```
<project>/.claude/skills/signal-capture/
```

That is all. The session picks it up on its next start.

If the project is not a Claude Code project, or the session has no repository
access, paste the contents of `SKILL.md` at the start of the conversation instead.
The skill is written to work either way.

## 2. The hook

The hook injects one short line at the start of every session: that this project
keeps a signal log, how many entries are in it, and — once the count crosses a
threshold — that a review is worth offering.

Copy the script and make it executable:

```bash
mkdir -p .claude/hooks
cp .claude/skills/signal-capture/scripts/signals_check.sh .claude/hooks/
chmod +x .claude/hooks/signals_check.sh
```

Then add this to `.claude/settings.json`, merging with anything already there:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/signals_check.sh" }
        ]
      }
    ]
  }
}
```

Commit both. The hook then travels with the repository, which matters for cloud
and web sessions — those read the repository's own `.claude/`, never anything on
a personal machine.

### Setting the threshold

Twenty entries by default, set high on purpose: a review earns its cost when there
is enough material for patterns to show, and three signals produce three opinions
rather than one finding.

Set `SIGNALS_THRESHOLD` in the environment to change it. Better still, decide it
once with the owner when the skill is installed — a project doing heavy unfamiliar
work generates signals fast and may want a lower number; a routine one may want no
count-based offer at all, leaving only the phase and project boundaries.

### What the hook deliberately does not do

It does not prompt after every turn. That was considered and rejected: a reminder
that fires after "fix that typo" as readily as after a real correction gets
ignored within a day, and then the mechanism is worse than nothing because it
looks like it is working.

---

## 3. Checking it works

Start a session and ask what it knows about signals in this project. It should
mention the log and the count without being told. If it does not:

- confirm the script is executable and the path in `settings.json` is right;
- run `bash .claude/hooks/signals_check.sh` by hand — it should print one line of
  JSON;
- start Claude Code with `--debug` to see hook parse errors.

The script is written to stay silent rather than fail: a missing file, a missing
`jq`, or an unreadable log all produce a sensible line rather than an error. A
session must never break because of a bookkeeping hook.

---

## 4. Taking the signals to the library

When a review is due, bring `SIGNALS.md` to a session that has the skill library
available, and ask for a review pass. Processed entries can then be cleared from
the project's file — the change each one produced is in the skill it touched, and
the discussion is in the pull request that applied it.

Nothing in the project decides what changes. That judgement is the owner's, and it
happens where the skills live.
