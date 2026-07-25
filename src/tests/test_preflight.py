"""File 2 must fail loudly *before* it spends anything — and never fail wrongly.

The failures that matter look identical from the outside (the run just dies), so the
preflight turns each into a named, actionable error: a missing key, a revoked key,
exhausted credits, a retired model.

The equally important half is the false positive: gating on the provider's *model
listing* once blocked a run that would have worked, because an alias like
``claude-haiku-4-5`` is valid for calls but the listing only carries the dated
snapshot ``claude-haiku-4-5-20251001``. One real call is the ground truth.
"""

import pytest

from yc_scouter import config, preflight


class _Model:
    def __init__(self, mid):
        self.id = mid


class _Models:
    def __init__(self, ids, error=None):
        self._ids, self._error = ids, error
        self.calls = 0

    def list(self, **kw):
        self.calls += 1
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
        self,
        ids=("claude-haiku-4-5-20251001", "claude-opus-5"),
        models_error=None,
        ping_error=None,
    ):
        self.models = _Models(list(ids), models_error)
        self.messages = _Messages(ping_error)


def test_a_healthy_setup_passes_on_one_tiny_call():
    client = FakeClient()
    report = preflight.check_claude(model=config.CLAUDE_MODEL, client=client)
    assert report.ok is True
    assert report.model == config.CLAUDE_MODEL
    assert len(client.messages.calls) == 1, "the preflight must cost exactly one tiny call"
    assert client.messages.calls[0]["max_tokens"] == 1


def test_an_alias_missing_from_the_listing_is_not_an_error():
    """The regression that broke a real run: alias valid, listing shows snapshots."""
    client = FakeClient(ids=("claude-haiku-4-5-20251001", "claude-opus-4-8", "claude-opus-5"))
    report = preflight.check_claude(model="claude-haiku-4-5", client=client)
    assert report.ok is True
    assert client.models.calls == 0, "the listing must not be consulted when the call works"


def test_a_retired_model_is_named_with_the_alternatives():
    client = FakeClient(
        ids=("claude-opus-5", "claude-sonnet-4-5-20250929"),
        ping_error=RuntimeError("404 not_found_error: model: claude-haiku-4-5"),
    )
    with pytest.raises(preflight.PreflightError) as err:
        preflight.check_claude(model="claude-haiku-4-5", client=client)
    text = str(err.value)
    assert "claude-haiku-4-5" in text and "claude-opus-5" in text
    assert "config.py" in text, "the message must say where to change the model"


def test_a_revoked_key_is_reported_as_such():
    client = FakeClient(ping_error=RuntimeError("authentication_error: invalid x-api-key"))
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
    client = FakeClient(ping_error=TimeoutError("connection timed out"))
    report = preflight.check_claude(model=config.CLAUDE_MODEL, client=client, strict=False)
    assert report.ok is False and "timed out" in report.warning


def test_an_unlistable_account_still_passes_when_the_call_works():
    client = FakeClient(models_error=RuntimeError("listing not permitted"))
    assert preflight.check_claude(model=config.CLAUDE_MODEL, client=client).ok is True


def test_mock_and_missing_providers_are_skipped():
    assert preflight.check("mock", model="whatever").ok is True
    assert preflight.check("mock", model="whatever").skipped is True
