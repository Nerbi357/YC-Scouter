"""Shared test fixtures."""

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_records() -> list[dict]:
    """Raw YC records with real field names (see fixtures/companies_sample.json)."""
    return json.loads((FIXTURES / "companies_sample.json").read_text())
