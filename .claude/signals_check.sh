#!/usr/bin/env bash
# SessionStart hook: remind the session that this project keeps a signal log, and
# say how many entries are waiting when enough have piled up.
#
# Quiet by design. It prints one short line at the start of a session and nothing
# else, ever. If it cannot find anything it stays silent rather than guessing.
#
# Install: see ../references/INSTALL.md
set -uo pipefail

THRESHOLD="${SIGNALS_THRESHOLD:-20}"

# The log lives at the project root, in plain sight.
if [ -f "SIGNALS.md" ]; then
  SIGNALS_FILE="SIGNALS.md"
fi

if [ -z "${SIGNALS_FILE:-}" ]; then
  context="This project keeps a signal log of how the work goes. No SIGNALS.md exists yet — create SIGNALS.md at the project root the first time something is worth recording, following the signal-capture skill."
else
  # grep -c prints the count even when it is zero, but exits non-zero on no
  # match — so the fallback must not echo a second number into the capture.
  count=$(grep -c '^## [0-9]' "$SIGNALS_FILE" 2>/dev/null || true)
  count=${count:-0}
  context="This project keeps a signal log at $SIGNALS_FILE with $count entries. Keep recording per the signal-capture skill."
  if [ "$count" -ge "$THRESHOLD" ]; then
    context="$context There are $count unprocessed signals, at or past the threshold of $THRESHOLD — offer the owner a review pass at the next natural boundary, once, and take no for an answer."
  fi
fi

# Emit as additionalContext so it reaches the model rather than the terminal.
if command -v jq >/dev/null 2>&1; then
  jq -n --arg c "$context" \
    '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$c}}'
else
  # jq is not guaranteed to exist; escape by hand rather than fail the session.
  escaped=$(printf '%s' "$context" | sed 's/\\/\\\\/g; s/"/\\"/g')
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$escaped"
fi

exit 0
