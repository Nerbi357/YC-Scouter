"""The Form D spike: can a YC company be found among SEC filers by name?

The point of the spike is a *number*, and a number is only worth having if the
counting is honest. These tests pin the three ways it could quietly lie: calling a
match exact when it is not, hiding an ambiguous result behind the first candidate,
and turning a failed request into a "no filings found".

Nothing here touches the network — every test drives a fake fetcher.
"""

import pytest

from yc_scouter import sec_edgar

# Two filers whose names are the same company name — the case that must never be
# resolved by picking one.
MULTI = """<?xml version="1.0" encoding="ISO-8859-1"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>MOTION INC (0001812216) (Filer)</title>
    <link href="/cgi-bin/browse-edgar?action=getcompany&amp;CIK=0001812216&amp;type=D"/>
  </entry>
  <entry>
    <title>Motion, LLC (0001999999) (Filer)</title>
    <link href="/cgi-bin/browse-edgar?action=getcompany&amp;CIK=0001999999&amp;type=D"/>
  </entry>
</feed>
"""

# One filer is the company; the rest merely start with the same word.
MIXED = """<?xml version="1.0" encoding="ISO-8859-1"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>MOTION INC (0001812216) (Filer)</title>
    <link href="/cgi-bin/browse-edgar?action=getcompany&amp;CIK=0001812216&amp;type=D"/>
  </entry>
  <entry>
    <title>MOTION CAPITAL PARTNERS LLC (0001999999) (Filer)</title>
    <link href="/cgi-bin/browse-edgar?action=getcompany&amp;CIK=0001999999&amp;type=D"/>
  </entry>
</feed>
"""

# A search that resolved to exactly one filer (a different shape entirely).
SINGLE = """<?xml version="1.0" encoding="ISO-8859-1"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <company-info>
    <cik>0001812216</cik>
    <conformed-name>GENECIS BIOINDUSTRIES INC</conformed-name>
  </company-info>
  <entry>
    <content type="text/xml">
      <filing-type>D</filing-type>
      <filing-date>2024-03-12</filing-date>
    </content>
  </entry>
</feed>
"""

EMPTY = """<?xml version="1.0" encoding="ISO-8859-1"?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>
"""


def test_legal_suffixes_do_not_decide_whether_a_company_matched():
    assert sec_edgar.normalise_name("Motion, Inc.") == sec_edgar.normalise_name("MOTION INC")
    assert sec_edgar.normalise_name("Genecis Bio LLC") == sec_edgar.normalise_name("genecis bio")
    assert sec_edgar.normalise_name("  Loop   Health  ") == "loop health"


def test_a_different_company_is_not_a_match():
    assert sec_edgar.normalise_name("Motion") != sec_edgar.normalise_name("Motion Capital")


def test_several_filers_share_a_name_and_that_is_reported_as_ambiguous():
    candidates = sec_edgar.parse_candidates(MULTI)
    assert [c["cik"] for c in candidates] == ["0001812216", "0001999999"]
    verdict = sec_edgar.classify("Motion", candidates)
    assert verdict.match == "ambiguous", "picking the first candidate would invent a fact"
    assert verdict.cik is None


def test_unrelated_filers_are_counted_but_do_not_block_a_match():
    """A name-prefix search returns neighbours; they are noise, not ambiguity.

    They are still counted, because a company whose name collides with twenty
    filers is exactly where a name-only match should not be trusted.
    """
    verdict = sec_edgar.classify("Motion", sec_edgar.parse_candidates(MIXED))
    assert verdict.match == "matched" and verdict.cik == "0001812216"
    assert verdict.others == 1, "the near-miss must stay visible in the report"


def test_one_filer_with_the_same_normalised_name_is_a_match():
    verdict = sec_edgar.classify("Motion Inc.", sec_edgar.parse_candidates(SINGLE))
    assert verdict.match == "none", "a different company must not count"

    single = sec_edgar.parse_candidates(SINGLE)
    assert single[0]["name"] == "GENECIS BIOINDUSTRIES INC"
    assert sec_edgar.classify("Genecis Bioindustries", single).match == "matched"
    assert sec_edgar.classify("Genecis Bioindustries", single).cik == "0001812216"


def test_no_filers_is_a_clean_negative():
    assert sec_edgar.parse_candidates(EMPTY) == []
    assert sec_edgar.classify("Whoever", []).match == "none"


def test_a_failed_request_is_an_error_not_a_negative():
    """The distinction the whole measurement rests on."""

    def boom(url, **kw):
        raise TimeoutError("connection timed out")

    report = sec_edgar.measure_coverage([{"id": 1, "name": "Motion"}], fetch=boom, pause=0)
    row = report["rows"][0]
    assert row["match"] == "error"
    assert "timed out" in row["note"]
    assert report["counts"]["error"] == 1
    assert report["counts"]["none"] == 0, "a blocked check must never be counted as absent"


def test_unparseable_xml_is_reported_rather_than_swallowed():
    report = sec_edgar.measure_coverage(
        [{"id": 1, "name": "Motion"}], fetch=lambda url, **kw: "<not xml", pause=0
    )
    assert report["rows"][0]["match"] == "error"


def test_the_report_counts_every_company_exactly_once():
    pages = {"Motion": MULTI, "Genecis Bioindustries": SINGLE, "Nobody": EMPTY}
    calls = []

    def fake(url, *, name=None, **kw):
        calls.append(name)
        return pages[name]

    companies = [
        {"id": 1, "name": "Motion"},
        {"id": 2, "name": "Genecis Bioindustries"},
        {"id": 3, "name": "Nobody"},
    ]
    report = sec_edgar.measure_coverage(companies, fetch=fake, pause=0)

    assert calls == ["Motion", "Genecis Bioindustries", "Nobody"]
    assert sum(report["counts"].values()) == 3
    assert report["counts"] == {"matched": 1, "ambiguous": 1, "none": 1, "error": 0}
    assert report["sample_size"] == 3
    assert {r["match"] for r in report["rows"]} == {"matched", "ambiguous", "none"}


def test_the_sample_is_deterministic_so_a_rerun_measures_the_same_companies():
    frame = [{"id": i, "name": f"C{i}"} for i in range(1000)]
    first = sec_edgar.take_sample(frame, 50)
    assert len(first) == 50
    assert first == sec_edgar.take_sample(list(reversed(frame)), 50), "order must not matter"
    assert len({c["id"] for c in first}) == 50


def test_the_sample_spans_the_whole_list_rather_than_its_head():
    frame = [{"id": i, "name": f"C{i}"} for i in range(1000)]
    ids = [c["id"] for c in sec_edgar.take_sample(frame, 10)]
    assert max(ids) > 800, "sampling only the first companies would bias the measurement"


def test_the_request_identifies_itself_as_sec_asks():
    seen = {}

    def fake(url, *, headers=None, **kw):
        seen["url"], seen["headers"] = url, headers or {}
        return EMPTY

    sec_edgar.measure_coverage([{"id": 1, "name": "X"}], fetch=fake, pause=0)
    assert "type=D" in seen["url"], "the search must be restricted to Form D"
    ua = seen["headers"].get("User-Agent", "")
    assert ua and "yc-scouter" in ua.lower(), "SEC asks every client to identify itself"
    assert "@" not in ua, "no personal address goes into a public repository"


def test_a_contact_can_be_supplied_without_being_committed(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "YC-Scouter research (someone@example.com)")
    assert sec_edgar.user_agent() == "YC-Scouter research (someone@example.com)"
    monkeypatch.delenv("SEC_USER_AGENT")
    assert "yc-scouter" in sec_edgar.user_agent().lower()


@pytest.mark.parametrize("size", [0, 1, 5])
def test_a_tiny_or_empty_sample_does_not_crash(size):
    frame = [{"id": i, "name": f"C{i}"} for i in range(5)]
    assert len(sec_edgar.take_sample(frame, size)) == min(size, 5)
