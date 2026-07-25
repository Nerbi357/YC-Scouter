"""File 2 must fail loudly *before* it spends anything.

The failures that matter here look identical from the outside — the run just dies
somewhere in the middle — so the preflight turns each into a named, actionable
error: a missing key, a revoked key, exhausted credits, a retired model.
"""

import pytest

from yc_scouter import config, preflight


class _Model:
    def __init__(self, mid):
        self.id = mid


class _Models:
    def __init__(self, ids, error=None):
        self._ids, self._error = ids, error

    def list(self, **kw):
        if self._error:
            raise self._error
        return type("Page", (), {"data": [_Model(i) for i in self._ids]})()


class _Messages:
    def __init__(self, error=None):
        self.error, self.calls = error, []

    def create(self, **kw):
        self.calls.append(kw)
        if self.error:
            raise self.error
        return type("Resp", (), {"content": [], "usage": None})()


class FakeClient:
    """Minimal stand-in for anthropic.Anthropic."""

    def __init__(
        self, ids=("claude-haiku-4-5", "claude-sonnet-4-5"), models_error=None, ping_error=None
    ):
        self.models = _Models(list(ids), models_error)
        self.messages = _Messages(ping_error)


def test_a_healthy_setup_passes_and_pings_once():
    client = FakeClient()
    report = preflight.check_claude(model=config.CLAUDE_MODEL, client=client)
    assert report.ok is True
    assert report.model == config.CLAUDE_MODEL
    assert len(client.messages.calls) == 1, "the preflight must cost exactly one tiny call"
    assert client.messages.calls[0]["max_tokens"] == 1


def test_a_retired_model_is_named_with_the_alternatives():
    client = FakeClient(ids=("claude-sonnet-4-5", "claude-opus-4-5"))
    with pytest.raises(preflight.PreflightError) as err:
        preflight.check_claude(model="claude-haiku-4-5", client=client)
    text = str(err.value)
    assert "claude-haiku-4-5" in text and "claude-sonnet-4-5" in text
    assert "config.py" in text, "the message must say where to change the model"
    assert client.messages.calls == [], "no spend once the model is known to be gone"


def test_a_revoked_key_is_reported_as_such():
    client = FakeClient(models_error=RuntimeError("authentication_error: invalid x-api-key"))
    with pytest.raises(preflight.PreflightError) as err:
        preflight.check_claude(model=config.CLAUDE_MODEL, client=client)
    assert "key" in str(err.value).lower()


def test_exhausted_credits_are_reported_as_such():
    client = FakeClient(ping_error=RuntimeError("Error code: 400 - credit balance is too low"))
    with pytest.raises(preflight.PreflightError) as err:
        preflight.check_claude(model=config.CLAUDE_MODEL, client=client)
    assert "credit" in str(err.value).lower()


def test_a_missing_key_is_caught_before_any_client_is_built(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(preflight.PreflightError, match="ANTHROPIC_API_KEY"):
        preflight.check_claude(model=config.CLAUDE_MODEL, api_key=None)


def test_an_unreachable_api_does_not_block_the_run():
    """A network blip must not stop a run that would otherwise work."""
    client = FakeClient(models_error=TimeoutError("connection timed out"))
    report = preflight.check_claude(model=config.CLAUDE_MODEL, client=client, strict=False)
    assert report.ok is False and "timed out" in report.warning


def test_mock_and_missing_providers_are_skipped():
    assert preflight.check("mock", model="whatever").ok is True
    assert preflight.check("mock", model="whatever").skipped is True
