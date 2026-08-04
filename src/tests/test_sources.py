"""The source registry — the test of whether this project can actually grow.

The claim the architecture makes is that adding a source touches nothing that
already exists. These tests hold it to that: a brand-new source is registered here,
inside the test, and everything downstream keeps working without a line changing
anywhere else.
"""

import pandas as pd
import pytest

from yc_scouter import facts, sources
from yc_scouter.sources import yc


@pytest.fixture
def companies():
    return pd.DataFrame(
        [
            {
                "id": 1,
                "name": "Genecis Bio",
                "website": "https://genecis.com",
                "yc_url": "https://www.ycombinator.com/companies/genecis-bio",
                "status": "Active",
                "stage": "Early",
                "team_size": 30,
                "is_hiring": True,
                "top_company": False,
                "batch": "Winter 2020",
                "industry": "Industrials",
            },
            {
                "id": 2,
                "name": "Nameless",
                "website": "",
                "yc_url": "",
                "status": "",
                "stage": "",
                "team_size": None,
                "is_hiring": False,
                "top_company": False,
                "batch": "Summer 2021",
                "industry": "",
            },
        ]
    )


def test_yc_is_registered_and_declares_what_it_covers():
    source = sources.get("yc")
    assert source.title and source.url
    assert "status" in source.covers and "team_size" in source.covers
    assert source.licence, "a source without stated terms cannot be published from"


def test_every_registered_source_can_be_listed_with_its_terms():
    listed = sources.all_sources()
    assert [s.id for s in listed] == sorted(s.id for s in listed)
    assert all(s.licence and s.url for s in listed)


def test_two_sources_cannot_share_an_id():
    with pytest.raises(ValueError, match="yc"):
        sources.register(sources.get("yc"))


def test_yc_turns_companies_into_facts_with_provenance(companies):
    rows = yc.to_facts(companies, observed_at="2026-07-27")
    store = facts.record(facts.empty(), rows)

    assert facts.latest(store, 1, "team_size") == "30"
    assert facts.latest(store, 1, "status") == "Active"
    first = next(r for r in facts.timeline(store, 1) if r["field"] == "status")
    assert first["source"] == "yc"
    assert first["source_url"].endswith("/companies/genecis-bio")


def test_empty_values_are_not_recorded_as_facts(companies):
    """An absent field is not an observation — recording it would fake coverage."""
    rows = yc.to_facts(companies, observed_at="2026-07-27")
    company_two = [r for r in rows if r["company_id"] == 2]
    assert {r["field"] for r in company_two} == {"batch", "checked"}, (
        "only the batch is known, plus the marker that the source was consulted"
    )


def test_a_company_with_no_link_still_gets_a_source_url(companies):
    rows = yc.to_facts(companies, observed_at="2026-07-27")
    assert all(r["source_url"] for r in rows), "provenance is never blank"


def test_rerunning_the_same_source_adds_nothing(companies):
    rows = yc.to_facts(companies, observed_at="2026-07-27")
    store = facts.record(facts.empty(), rows)
    size = len(store)

    later = yc.to_facts(companies, observed_at="2026-08-03")
    store = facts.record(store, later)

    assert len(store) == size, "an unchanged source must not grow the table"
    assert store["last_seen"].max() == "2026-08-03", "but it does refresh the confirmation"


def test_a_changed_field_appends_one_row_and_nothing_else(companies):
    store = facts.record(facts.empty(), yc.to_facts(companies, observed_at="2026-07-27"))
    size = len(store)

    grown = companies.copy()
    grown.loc[0, "team_size"] = 65
    store = facts.record(store, yc.to_facts(grown, observed_at="2026-08-03"))

    assert len(store) == size + 1
    assert facts.latest(store, 1, "team_size") == "65"


def test_a_new_source_needs_no_change_anywhere_else(companies):
    """The architecture's whole claim, exercised."""
    fake = sources.Source(
        id="zz-test",
        title="Test source",
        url="https://example.org",
        licence="none — test only",
        covers=("headcount",),
        emits=lambda df, observed_at: [
            {
                "company_id": int(row["id"]),
                "field": "headcount",
                "value": "7",
                "observed_at": observed_at,
                "source": "zz-test",
                "source_url": "https://example.org/1",
            }
            for _, row in df.iterrows()
        ],
    )
    sources.register(fake)
    try:
        store = facts.record(facts.empty(), yc.to_facts(companies, observed_at="2026-07-27"))
        store = facts.record(store, fake.emits(companies, observed_at="2026-07-27"))

        assert facts.latest(store, 1, "headcount") == "7"
        matrix = facts.coverage(
            store, company_ids=[1], sources=[s.id for s in sources.all_sources()]
        )
        assert matrix[(1, "yc")] == "covered" and matrix[(1, "zz-test")] == "covered"
    finally:
        sources.unregister("zz-test")

    assert "zz-test" not in [s.id for s in sources.all_sources()]


def test_replaying_the_archive_builds_a_history_and_is_repeatable(tmp_path, companies):
    """The dated files in data/ already are the history; folding them is idempotent."""
    from yc_scouter import pipeline

    early = tmp_path / "yc_dataset_base_2026-07-01.parquet"
    later = tmp_path / "yc_dataset_base_2026-07-20.parquet"
    companies.to_parquet(early, index=False)
    grown = companies.copy()
    grown.loc[0, "team_size"] = 65
    grown.to_parquet(later, index=False)

    target = tmp_path / "facts.parquet"
    store = pipeline.build_facts(data_dir=tmp_path, facts_path=target)
    again = pipeline.build_facts(data_dir=tmp_path, facts_path=target)

    assert len(again) == len(store), "replaying the same archive twice must add nothing"
    sizes = [r["value"] for r in facts.timeline(store, 1) if r["field"] == "team_size"]
    assert sizes == ["30", "65"], "the archive replayed into a real history"
