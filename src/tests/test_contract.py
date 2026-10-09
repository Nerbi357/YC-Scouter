"""The contract exists to catch the quiet failures; these tests are those failures."""

import pandas as pd
import pytest

from yc_scouter import contract


def _base(n=100, **over):
    frame = pd.DataFrame(
        {
            "id": range(n),
            "name": [f"C{i}" for i in range(n)],
            "batch": ["Winter 2024"] * n,
            "status": ["Active"] * n,
            "website": [f"https://c{i}.com" for i in range(n)],
        }
    )
    for k, v in over.items():
        frame[k] = v
    return frame


def _ai(n=100, coverage=1.0, model="claude-haiku-4-5"):
    frame = _base(n)
    filled = int(n * coverage)
    frame["ai_description"] = ["text"] * filled + [""] * (n - filled)
    frame["ai_risks"] = ["risk"] * n
    frame["ai_model"] = [model] * n
    return frame


def test_a_healthy_rebuild_passes():
    assert contract.check_base(_base(100), previous=_base(98)) == []
    assert contract.check_ai(_ai(100), previous=_ai(98)) == []


def test_a_renamed_source_field_is_caught_as_a_missing_column():
    broken = _base().rename(columns={"status": "state"})
    [violation] = contract.check_base(broken)
    assert "status" in violation


def test_a_half_empty_rebuild_is_refused():
    [violation] = contract.check_base(_base(40), previous=_base(100))
    assert "fell" in violation and "40" in violation


def test_an_implausible_jump_is_refused_too():
    """Twice the companies overnight is a duplicated fetch, not a boom."""
    [violation] = contract.check_base(_base(200), previous=_base(100))
    assert "jumped" in violation


def test_a_small_shrink_is_normal():
    assert contract.check_base(_base(95), previous=_base(100)) == []


def test_duplicate_ids_are_refused():
    frame = _base(10)
    frame.loc[9, "id"] = 0
    assert any("duplicate" in v for v in contract.check_base(frame))


def test_an_empty_dataset_is_refused_rather_than_published():
    assert contract.check_base(_base(0)) == ["the dataset is empty"]


def test_an_ai_step_that_quietly_skipped_companies_is_refused():
    violations = contract.check_ai(_ai(100, coverage=0.8))
    assert any("coverage is 80.0%" in v for v in violations)


def test_two_models_in_one_dataset_is_refused():
    frame = _ai(100)
    frame.loc[:49, "ai_model"] = "other-model"
    assert any("more than one model" in v for v in contract.check_ai(frame))


def test_the_first_run_has_nothing_to_compare_with_and_still_passes():
    assert contract.check_base(_base(100), previous=None) == []


def test_assert_reports_every_violation_at_once():
    frame = _base(40)
    frame.loc[39, "id"] = 0
    with pytest.raises(contract.ContractError) as err:
        contract.assert_contract(contract.check_base(frame, previous=_base(100)), stage="base")
    text = str(err.value)
    assert "duplicate" in text and "fell" in text
