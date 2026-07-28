"""Central configuration and constants — the single source of truth.

Both notebooks (File 1 / File 2) and the dashboard import from here, so model
IDs, token budgets, prices, paths, and the dated-filename convention live in one
place. Changing a model or a token cap is a one-line edit here.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

# --------------------------------------------------------------------- providers
#: Default LLM provider for File 2 (the notebook switch can override).
PROVIDER_DEFAULT = "claude"

#: Cheapest capable Anthropic model for the summaries.
CLAUDE_MODEL = "claude-haiku-4-5"
#: A generally-available Groq model (kept as an opt-in alternative).
GROQ_MODEL = "llama-3.3-70b-versatile"

# ------------------------------------------------------------------ token budget
#: How much of ``long_description`` we send (input is the cheap side).
MAX_DESC_CHARS = 2200
#: Output cap per company (richer description + 1-2 short risks).
MAX_TOKENS = 430
#: Planning estimate only — NOT a runtime cap. The summarizer prints a running
#: cost estimate but never auto-halts.
AI_BUDGET_TARGET_USD = 9.0

#: USD per 1M tokens, (input, output), by model id.
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "llama-3.3-70b-versatile": (0.59, 0.79),
}


def estimate_cost(in_tokens: int, out_tokens: int, model: str) -> float:
    """Estimated USD for the given token counts under ``model``'s price."""
    pin, pout = PRICES.get(model, (0.0, 0.0))
    return in_tokens / 1_000_000 * pin + out_tokens / 1_000_000 * pout


# -------------------------------------------------------------------- data paths
#: Folder 1 — where dated datasets live (repo-relative).
DATA_DIR = Path("data")
CACHE_DIR = DATA_DIR / "cache"

_STAGES = ("base", "ai")
_EXTS = ("parquet", "xlsx")


def dated_path(stage: str, date: str | dt.date, ext: str, *, out_dir: Path = DATA_DIR) -> Path:
    """Build ``<out_dir>/yc_dataset_<stage>_<YYYY-MM-DD>.<ext>`` (ASCII, ISO date)."""
    if stage not in _STAGES:
        raise ValueError(f"stage must be one of {_STAGES}, got {stage!r}")
    if ext not in _EXTS:
        raise ValueError(f"ext must be one of {_EXTS}, got {ext!r}")
    iso = date.isoformat() if isinstance(date, dt.date) else str(date)
    return Path(out_dir) / f"yc_dataset_{stage}_{iso}.{ext}"


def latest_dated(stage: str, ext: str, *, out_dir: Path = DATA_DIR) -> Path | None:
    """Newest dated file for ``stage``/``ext`` (ISO names sort chronologically)."""
    matches = sorted(Path(out_dir).glob(f"yc_dataset_{stage}_*.{ext}"))
    return matches[-1] if matches else None


def today_iso(today: dt.date | None = None) -> str:
    """Today's date as ``YYYY-MM-DD`` (injectable for tests)."""
    return (today or dt.date.today()).isoformat()


# ------------------------------------------------------------------ batch window
def target_years(start: int = 2020, *, today: dt.date | None = None) -> tuple[int, ...]:
    """Years to keep: ``start`` .. current year (right boundary = now)."""
    current = (today or dt.date.today()).year
    return tuple(range(start, current + 1))


# ------------------------------------------------------------------- ai identity
def prompt_version(system_prompt: str, prompt_template: str) -> str:
    """Stable 12-hex fingerprint of the prompt, part of the AI cache key."""
    digest = hashlib.sha256((system_prompt + prompt_template).encode("utf-8"))
    return digest.hexdigest()[:12]
