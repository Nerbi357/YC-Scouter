"""The facts layer: one row per observation, never one column per source.

This is the table the whole of v2 rests on, so these tests pin the properties that
make it worth having rather than the mechanics of storing rows:

* re-running a source does not duplicate what it already recorded — otherwise a
  weekly refresh doubles the table and every count becomes wrong;
* a **changed** value appends rather than overwrites — that is what makes a timeline
  possible without storing whole snapshots;
* nothing enters without provenance, because "where did this come from" is the
  product, not a nicety;
* an empty cell and an uncovered company are different states, and the table can
  always tell them apart.
"""

import pandas as pd
import pytest

from yc_scouter import facts


def _rows(**over):
    row = {
        "company_id": 1,
        "field": "team_size",
        "value": "30",
        "observed_at": "2026-07-01",
        "source": "yc",
        "source_url": "https://www.ycombinator.com/companies/genecis-bio",
    }
    row.update(over)
    return [row]


def test_an_empty_table_has_the_full_schema():
    empty = facts.empty()
    assert list(empty.columns) == list(facts.COLUMNS)
    assert len(empty) == 0


def test_recording_the_same_observation_twice_changes_nothing():
    """A weekly refresh re-reads everything; it must not grow the table."""
    store = facts.record(facts.empty(), _rows())
    again = facts.record(store, _rows(observed_at="2026-07-08"))

    assert len(again) == 1, "the same value from the same source is one fact"
    assert again.loc[0, "observed_at"] == "2026-07-01", "keep when it was first seen"
    assert again.loc[0, "last_seen"] == "2026-07-08", "and when it was last confirmed"


def test_a_changed_value_is_appended_so_the_history_survives():
    store = facts.record(facts.empty(), _rows())
    store = facts.record(store, _rows(value="65", observed_at="2026-07-20"))

    assert len(store) == 2
    assert facts.latest(store, 1, "team_size") == "65"
    history = facts.timeline(store, 1)
    assert [r["value"] for r in history] == ["30", "65"], "oldest first"


def test_two_sources_may_disagree_and_both_are_kept():
    store = facts.record(facts.empty(), _rows())
    store = facts.record(
        store,
        _rows(value="31", source="sec", source_url="https://www.sec.gov/x"),
    )
    assert len(store) == 2
    assert {r["source"] for r in facts.timeline(store, 1)} == {"yc", "sec"}


def test_a_fact_without_provenance_is_refused():
    for missing in ("source", "source_url", "observed_at"):
        bad = _rows()
        bad[0][missing] = ""
        with pytest.raises(facts.ProvenanceError, match=missing):
            facts.record(facts.empty(), bad)


def test_numbers_stay_usable_without_a_second_table():
    store = facts.record(facts.empty(), _rows(value="65"))
    assert store.loc[0, "value_num"] == 65.0
    text = facts.record(facts.empty(), _rows(field="status", value="Active"))
    assert pd.isna(text.loc[0, "value_num"]), "text must not become a number"


def test_the_timeline_of_a_company_carries_its_sources_and_links():
    store = facts.record(facts.empty(), _rows())
    store = facts.record(
        store,
        _rows(
            company_id=1,
            field="form_d_offering",
            value="3000000",
            observed_at="2026-05-04",
            source="sec",
            source_url="https://www.sec.gov/Archives/edgar/data/1/000.txt",
        ),
    )
    events = facts.timeline(store, 1)
    assert [e["observed_at"] for e in events] == ["2026-05-04", "2026-07-01"]
    assert all(e["source"] and e["source_url"] for e in events)
    assert facts.timeline(store, 999) == [], "an unknown company has an empty timeline"


def test_coverage_separates_no_value_from_not_looked_at():
    """The distinction that stops a blank from reading as 'raised nothing'."""
    store = facts.record(facts.empty(), _rows(company_id=1))
    store = facts.record(
        store,
        _rows(
            company_id=2,
            field="checked",
            value="",
            source="sec",
            source_url="https://www.sec.gov/x",
        ),
    )

    matrix = facts.coverage(store, company_ids=[1, 2, 3], sources=["yc", "sec"])
    assert matrix[(1, "yc")] == "covered"
    assert matrix[(1, "sec")] == "uncovered", "nobody asked SEC about company 1"
    assert matrix[(2, "sec")] == "covered", "asked, and the answer was nothing"
    assert matrix[(3, "yc")] == "uncovered"


def test_latest_returns_nothing_rather_than_guessing():
    store = facts.record(facts.empty(), _rows())
    assert facts.latest(store, 1, "status") is None
    assert facts.latest(store, 42, "team_size") is None


def test_facts_survive_a_round_trip_through_parquet(tmp_path):
    store = facts.record(facts.empty(), _rows())
    path = tmp_path / "facts.parquet"
    facts.save(store, path)
    back = facts.load(path)
    assert list(back.columns) == list(facts.COLUMNS)
    assert facts.latest(back, 1, "team_size") == "30"


def test_loading_a_missing_file_gives_an_empty_table_not_a_crash(tmp_path):
    assert len(facts.load(tmp_path / "nothing.parquet")) == 0
