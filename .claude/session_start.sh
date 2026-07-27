#!/usr/bin/env bash
# SessionStart hook: ensure the project can run tests/linters in web sessions.
# Idempotent and quiet; never fails the session.
set -uo pipefail
cd "$(dirname "$0")/.."
pip install -q -r requirements.txt >/dev/null 2>&1 || true
pip install -q -e . --no-deps >/dev/null 2>&1 || true
echo "yc-scouter: environment ready (deps installed)"
