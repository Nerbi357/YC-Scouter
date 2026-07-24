"""Tests for the Google Sheets backend's pure config guard (no network)."""

from yc_scouter import gsheets


class _Secrets(dict):
    """Mimic st.secrets' .get access."""


def test_is_configured_true_when_both_present():
    s = _Secrets(gcp_service_account={"client_email": "x@y.iam"}, gsheets={"spreadsheet": "id"})
    assert gsheets.is_configured(s) is True


def test_is_configured_false_when_missing():
    assert gsheets.is_configured(_Secrets()) is False
    assert gsheets.is_configured(_Secrets(gcp_service_account={"a": 1})) is False
    assert gsheets.is_configured({}) is False
