"""Tests for enrichment: investability heuristic and open-source links."""

from yc_radar import enrich, normalize


def _df(sample_records):
    return normalize.normalize(sample_records)


def test_investability_maps_each_status(sample_records):
    df = enrich.add_investability(_df(sample_records))
    by_slug = df.set_index("slug")["investability"]
    assert by_slug["delta-public"] == enrich.INVESTABILITY["Public"]
    assert by_slug["betahealth"] == enrich.INVESTABILITY["Acquired"]
    assert by_slug["acme-ai"] == enrich.INVESTABILITY["Active"]


def test_investability_unknown_status_is_safe():
    import pandas as pd

    df = pd.DataFrame({"slug": ["x"], "status": ["Weird"]})
    out = enrich.add_investability(df)
    assert out.loc[0, "investability"] == enrich.INVESTABILITY_UNKNOWN
