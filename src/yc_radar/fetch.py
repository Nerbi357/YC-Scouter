"""Download and cache the public YC company dataset (yc-oss/api).

The data is a community-maintained JSON export of the official YC company
directory, rebuilt daily. We fetch it once and cache it under ``data/raw/`` so
repeated runs don't re-download unless the cache is stale or a refresh is forced.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

#: All publicly launched YC companies, one JSON array.
COMPANIES_URL = "https://yc-oss.github.io/api/companies/all.json"

DEFAULT_CACHE_PATH = Path("data/raw/yc_companies.json")
DEFAULT_MAX_AGE_HOURS = 24.0
_TIMEOUT_SECONDS = 60.0


def _cache_is_fresh(cache_path: Path, max_age_hours: float) -> bool:
    if not cache_path.exists():
        return False
    age_seconds = time.time() - cache_path.stat().st_mtime
    return age_seconds < max_age_hours * 3600


def fetch_companies(
    *,
    force_refresh: bool = False,
    cache_path: Path = DEFAULT_CACHE_PATH,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
    url: str = COMPANIES_URL,
) -> list[dict]:
    """Return the list of YC company records, using a local cache when fresh.

    Args:
        force_refresh: Ignore the cache and re-download.
        cache_path: Where the raw JSON is cached.
        max_age_hours: Cache is reused only if younger than this.
        url: Source endpoint (overridable for testing/mirrors).

    Raises:
        RuntimeError: On any network or HTTP failure, with a clear message.
    """
    cache_path = Path(cache_path)

    if not force_refresh and _cache_is_fresh(cache_path, max_age_hours):
        return json.loads(cache_path.read_text())

    try:
        response = httpx.get(url, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        records = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to fetch YC companies from {url}: {exc}") from exc

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(records))
    return records
