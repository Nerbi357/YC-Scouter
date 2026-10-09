"""The data contract — what a refresh must satisfy before it is allowed to publish.

An unattended refresh is only safe if a broken one cannot reach the site. The
failure that matters is *silent*: a renamed source field, a half-empty rebuild, an
AI step that quietly skipped most companies. Each of those produces a dataset that
loads fine and lies. This module turns them into a failed run instead.

The rules are deliberately few and loud. A refresh that fails the contract commits
nothing and leaves the previous dataset as the newest — the site keeps showing data
that was true, with its date, rather than data that is fresh and wrong.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

#: Without these there is no company record at all.
REQUIRED_BASE = ("id", "name", "batch", "status", "website")
#: The AI stage adds these; a run that produced the file but not the fields is broken.
REQUIRED_AI = ("ai_description", "ai_risks", "ai_model")

#: A rebuild may legitimately shrink a little (companies removed upstream) or grow
#: (a new batch). Outside this band it is far more likely to be a broken fetch.
MIN_RATIO = 0.90
MAX_RATIO = 1.50

#: Below this share of companies with an AI description, the AI step did not run
#: the way it was meant to — a key failed mid-way, a model vanished, a cap hit.
MIN_AI_COVERAGE = 0.99


class ContractError(ValueError):
    """The dataset violates the contract; the run must not publish."""


def _violations_common(frame: pd.DataFrame, required: Iterable[str]) -> list[str]:
    out: list[str] = []
    missing = [c for c in required if c not in frame.columns]
    if missing:
        out.append(f"missing required columns: {', '.join(missing)}")
        return out  # the rest would only repeat this
    if len(frame) == 0:
        out.append("the dataset is empty")
        return out
    dupes = int(frame["id"].duplicated().sum())
    if dupes:
        out.append(f"{dupes} duplicate ids")
    for column in required:
        if frame[column].isna().all():
            out.append(f"column {column!r} is entirely empty")
    return out


def check_base(frame: pd.DataFrame, previous: pd.DataFrame | None = None) -> list[str]:
    """Violations in a Base dataset, compared with the previous one when given."""
    out = _violations_common(frame, REQUIRED_BASE)
    if any(v.startswith("missing required") or v == "the dataset is empty" for v in out):
        return out  # nothing else can be judged
    if previous is not None and len(previous):
        ratio = len(frame) / len(previous)
        if ratio < MIN_RATIO:
            out.append(
                f"row count fell to {len(frame)} from {len(previous)} "
                f"({ratio:.0%} of the previous run; floor {MIN_RATIO:.0%})"
            )
        elif ratio > MAX_RATIO:
            out.append(
                f"row count jumped to {len(frame)} from {len(previous)} "
                f"({ratio:.0%} of the previous run; ceiling {MAX_RATIO:.0%})"
            )
    return out


def check_ai(frame: pd.DataFrame, previous: pd.DataFrame | None = None) -> list[str]:
    """Violations in an AI dataset: everything in Base, plus the AI fields."""
    out = check_base(frame, previous)
    if out and out[0].startswith("missing required"):
        return out
    out += [v for v in _violations_common(frame, REQUIRED_AI) if v not in out]
    if "ai_description" in frame.columns and len(frame):
        filled = frame["ai_description"].fillna("").astype(str).str.strip().ne("")
        coverage = float(filled.mean())
        if coverage < MIN_AI_COVERAGE:
            out.append(f"AI coverage is {coverage:.1%}; the step must reach {MIN_AI_COVERAGE:.0%}")
        models = frame.loc[filled, "ai_model"].dropna().unique() if "ai_model" in frame else []
        if len(models) > 1:
            out.append(f"more than one model in one dataset: {', '.join(map(str, models))}")
    return out


def assert_contract(violations: list[str], *, stage: str) -> None:
    """Raise with every violation at once — one run should teach everything it can."""
    if violations:
        bullet = "\n  - ".join(violations)
        raise ContractError(f"the {stage} dataset fails its contract:\n  - {bullet}")
