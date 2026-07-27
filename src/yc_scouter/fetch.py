"""Download the public YC company dataset (yc-oss/api).

The data is a community-maintained JSON export of the official YC directory,
rebuilt daily. File 1 re-scrapes **fresh on every run** (the project's
reproducibility is about code logic, not frozen data), so by default this always
downloads. A local cache is written when ``cache_path`` is given and can be reused
with ``use_cache=True`` for offline development only.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

#: All publicly launched YC companies, one JSON array.
COMPANIES_URL = "https://yc-oss.github.io/api/companies/all.json"

DEFAULT_CACHE_PATH = Path("data/raw/yc_companies.json")
_TIMEOUT_SECONDS = 60.0


def fetch_companies(
    *,
    url: str = COMPANIES_URL,
    cache_path: Path | None = None,
    use_cache: bool = False,
    timeout: float = _TIMEOUT_SECONDS,
) -> list[dict]:
    """Return the list of YC company records, downloading fresh by default.

    Args:
        url: Source endpoint (overridable for testing/mirrors).
        cache_path: If given, the downloaded JSON is written here.
        use_cache: Dev-only — if True and ``cache_path`` exists, reuse it and skip
            the network. Off by default so runs always re-scrape.
        timeout: HTTP timeout in seconds.

    Raises:
        RuntimeError: On any network or HTTP failure, with a clear message.
    """
    if use_cache and cache_path is not None and Path(cache_path).exists():
        return json.loads(Path(cache_path).read_text())

    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        records = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to fetch YC companies from {url}: {exc}") from exc

    if cache_path is not None:
        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(records))
    return records
