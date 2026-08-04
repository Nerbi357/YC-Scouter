"""Identities: deciding when two records are the same company.

Every source names companies differently, so one place has to answer "is this the
same one". The tests pin the two failure modes that matter, in order of damage:

* **merging two different companies** — one publicly wrong profile costs more trust
  than fifty missing matches, so anything uncertain must stay unresolved;
* **splitting one company** into two profiles because a URL had `www.` in it.
"""

import pytest

from yc_scouter import identities


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.Genecis.com/about?x=1", "genecis.com"),
        ("http://genecis.com", "genecis.com"),
        ("genecis.com/", "genecis.com"),
        ("https://sub.genecis.co.uk:8443/", "sub.genecis.co.uk"),
        ("HTTPS://GENECIS.COM.", "genecis.com"),
    ],
)
def test_the_same_site_written_five_ways_is_one_domain(url, expected):
    assert identities.normalise_domain(url) == expected


@pytest.mark.parametrize("junk", ["", None, "   ", "not a url", "http://", "mailto:a@b.c"])
def test_junk_produces_no_domain_rather_than_a_wrong_one(junk):
    assert identities.normalise_domain(junk) is None


def test_different_companies_keep_different_domains():
    assert identities.normalise_domain("https://motion.dev") != identities.normalise_domain(
        "https://motion.com"
    )


def test_name_normalisation_is_shared_with_every_source():
    """One canonical spelling, so SEC and YC agree on what a name is."""
    assert identities.normalise_name("Motion, Inc.") == identities.normalise_name("MOTION INC")
    assert identities.normalise_name("Motion") != identities.normalise_name("Motion Capital")


def test_an_identity_carries_every_key_a_source_can_join_on():
    row = identities.identify({"id": 7, "name": "Genecis Bio", "website": "https://Genecis.com"})
    assert row["company_id"] == 7
    assert row["domain"] == "genecis.com"
    assert row["name_key"] == "genecis bio"


def test_a_company_without_a_website_still_gets_an_identity():
    row = identities.identify({"id": 7, "name": "Genecis Bio", "website": ""})
    assert row["company_id"] == 7 and row["domain"] is None and row["name_key"] == "genecis bio"


def test_a_shared_domain_resolves_and_a_shared_name_only_suggests():
    table = identities.build(
        [
            {"id": 1, "name": "Genecis Bio", "website": "https://genecis.com"},
            {"id": 2, "name": "Motion", "website": "https://motion.dev"},
        ]
    )

    strong = identities.resolve(table, domain="https://www.genecis.com/careers")
    assert strong.company_id == 1 and strong.basis == "domain"

    weak = identities.resolve(table, name="MOTION INC")
    assert weak.company_id == 2 and weak.basis == "name"
    assert weak.confidence < strong.confidence, "a name is weaker evidence than a domain"


def test_an_ambiguous_name_resolves_to_nothing():
    table = identities.build(
        [
            {"id": 1, "name": "Motion", "website": "https://motion.dev"},
            {"id": 2, "name": "Motion", "website": "https://motion.com"},
        ]
    )
    verdict = identities.resolve(table, name="Motion")
    assert verdict.company_id is None
    assert verdict.basis == "ambiguous", "two candidates must never collapse into one"
    assert verdict.candidates == [1, 2], "both stay visible for a human to settle"


def test_no_evidence_at_all_resolves_to_nothing():
    table = identities.build([{"id": 1, "name": "Genecis Bio", "website": "https://genecis.com"}])
    assert identities.resolve(table, name="Nobody").company_id is None
    assert identities.resolve(table).company_id is None
