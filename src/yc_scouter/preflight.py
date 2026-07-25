"""Fail fast, before File 2 spends anything.

Four things break an AI run, and from the outside they all look the same — the job
dies somewhere in the middle of a few thousand companies:

* the API key is missing from the environment / repository secrets,
* the key was revoked or rotated,
* the account is out of credits,
* the configured model was retired (they usually are, every 6-12 months).

This module checks all four *before* the loop starts, costs one token, and turns
each into a named error that says what to do. Anything it cannot decide (a network
blip, an unexpected response shape) is reported as a warning and never blocks a run
that would otherwise work.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from . import config


class PreflightError(RuntimeError):
    """A problem that will certainly break the run — reported before any spend."""


@dataclass
class Report:
    """Outcome of a preflight check (also used for the run summary)."""

    ok: bool
    provider: str
    model: str
    skipped: bool = False
    warning: str = ""


#: Substrings providers use for the four failures we can act on.
_KEY_WORDS = ("authentication", "invalid x-api-key", "invalid api key", "unauthorized", "401")
_CREDIT_WORDS = ("credit balance", "insufficient_quota", "insufficient credits", "402", "billing")
_MODEL_WORDS = ("model_not_found", "not_found_error", "unknown model", "404")


def _classify(exc: Exception, provider: str, model: str) -> str | None:
    """A human instruction for a known failure, or None when unrecognised."""
    text = str(exc).lower()
    env = "ANTHROPIC_API_KEY" if provider == "claude" else "GROQ_API_KEY"
    if any(w in text for w in _KEY_WORDS):
        return (
            f"the {provider} API key was rejected. Create a new key and update the "
            f"{env} secret (GitHub: Settings -> Secrets and variables -> Actions)."
        )
    if any(w in text for w in _CREDIT_WORDS):
        return (
            f"the {provider} account is out of credits. Top it up; the run is resumable, "
            "so re-running afterwards only pays for what is still missing."
        )
    if any(w in text for w in _MODEL_WORDS):
        return (
            f"the model '{model}' is not available any more. Pick a current one and change "
            "the model constant in src/yc_scouter/config.py."
        )
    return None


def _listed_models(client) -> list[str]:
    """Model ids the account can see, or ``[]`` when the listing is unavailable."""
    try:
        return [m.id for m in client.models.list(limit=100).data]
    except Exception:
        return []


def check_claude(
    *,
    model: str = config.CLAUDE_MODEL,
    api_key: str | None = None,
    client: object | None = None,
    strict: bool = True,
) -> Report:
    """Verify the key, the credits and the model with **one real call**.

    The single one-token request is the ground truth: it exercises the key, the
    balance and the model together, exactly as the run will. A model *listing* is
    deliberately not used as the gate — aliases like ``claude-haiku-4-5`` are valid
    for calls but need not appear in the listing, which is only the dated snapshots.
    Gating on the listing once blocked a run that would have worked perfectly; the
    listing is now used only to enrich the message when a model really is gone.

    ``strict`` makes an *undiagnosable* failure (e.g. a timeout) a warning instead
    of an error, so a flaky network never blocks a run.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if client is None and not key:
        raise PreflightError(
            "ANTHROPIC_API_KEY is not set. Add it to the repository secrets "
            "(Settings -> Secrets and variables -> Actions) or export it locally."
        )
    if client is None:  # pragma: no cover - needs the real SDK
        import anthropic

        client = anthropic.Anthropic(api_key=key)

    try:
        client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as exc:
        hint = _classify(exc, "claude", model)
        if hint:
            available = _listed_models(client) if "model" in hint else []
            extra = f" Available now: {', '.join(sorted(available)[:8])}." if available else ""
            raise PreflightError(f"Preflight failed: {hint}{extra}") from exc
        if strict:
            raise PreflightError(f"Preflight call failed: {exc}") from exc
        return Report(False, "claude", model, warning=str(exc))

    return Report(True, "claude", model)


def check_groq(
    *,
    model: str = config.GROQ_MODEL,
    api_key: str | None = None,
    client: object | None = None,
    strict: bool = True,
) -> Report:
    """The same question for Groq, asked the same way: one real one-token call."""
    key = api_key or os.environ.get("GROQ_API_KEY")
    if client is None and not key:
        raise PreflightError(
            "GROQ_API_KEY is not set. Add it to the repository secrets or export it locally."
        )
    if client is None:  # pragma: no cover - needs the real SDK
        from groq import Groq

        client = Groq(api_key=key)

    try:
        client.chat.completions.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as exc:
        hint = _classify(exc, "groq", model)
        if hint:
            available = _listed_models(client) if "model" in hint else []
            extra = f" Available now: {', '.join(sorted(available)[:8])}." if available else ""
            raise PreflightError(f"Preflight failed: {hint}{extra}") from exc
        if strict:
            raise PreflightError(f"Preflight call failed: {exc}") from exc
        return Report(False, "groq", model, warning=str(exc))

    return Report(True, "groq", model)


def check(
    provider: str, *, model: str, api_key: str | None = None, client=None, strict: bool = True
) -> Report:
    """Preflight for the chosen provider; ``mock`` (offline) is skipped."""
    if provider == "mock":
        return Report(True, provider, model, skipped=True)
    if provider == "groq":
        return check_groq(model=model, api_key=api_key, client=client, strict=strict)
    return check_claude(model=model, api_key=api_key, client=client, strict=strict)
