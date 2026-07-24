"""Tests for the YC dataset fetcher. Network is always mocked."""

import json

import pytest

from yc_scouter import fetch


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise fetch.httpx.HTTPStatusError("boom", request=None, response=None)


def test_fetch_downloads_and_writes_cache(tmp_path, monkeypatch):
    calls = {"n": 0}
    sample = [{"id": 1, "name": "Acme", "slug": "acme"}]

    def fake_get(url, timeout=None):
        calls["n"] += 1
        return _FakeResponse(sample)

    monkeypatch.setattr(fetch.httpx, "get", fake_get)
    cache = tmp_path / "yc_companies.json"

    result = fetch.fetch_companies(cache_path=cache)

    assert result == sample
    assert calls["n"] == 1
    assert json.loads(cache.read_text()) == sample


def test_fetch_reuses_fresh_cache(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_get(url, timeout=None):
        calls["n"] += 1
        return _FakeResponse([{"id": 2}])

    monkeypatch.setattr(fetch.httpx, "get", fake_get)
    cache = tmp_path / "yc_companies.json"
    cache.write_text(json.dumps([{"id": 99, "name": "Cached"}]))

    result = fetch.fetch_companies(cache_path=cache)

    assert result == [{"id": 99, "name": "Cached"}]
    assert calls["n"] == 0  # network not touched


def test_force_refresh_bypasses_cache(tmp_path, monkeypatch):
    def fake_get(url, timeout=None):
        return _FakeResponse([{"id": 3, "name": "Fresh"}])

    monkeypatch.setattr(fetch.httpx, "get", fake_get)
    cache = tmp_path / "yc_companies.json"
    cache.write_text(json.dumps([{"id": 99}]))

    result = fetch.fetch_companies(cache_path=cache, force_refresh=True)

    assert result == [{"id": 3, "name": "Fresh"}]


def test_network_error_raises_clear_message(tmp_path, monkeypatch):
    def fake_get(url, timeout=None):
        raise fetch.httpx.ConnectError("no network")

    monkeypatch.setattr(fetch.httpx, "get", fake_get)
    cache = tmp_path / "yc_companies.json"

    with pytest.raises(RuntimeError, match="Failed to fetch"):
        fetch.fetch_companies(cache_path=cache)
