"""Tests for enrichment: investability heuristic and open-source links."""

from yc_scouter import enrich, normalize


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


def test_links_added_and_url_encoded(sample_records):
    df = enrich.add_links(_df(sample_records))
    for col in enrich.LINK_BUILDERS:
        assert col in df.columns
    acme = df[df["slug"] == "acme-ai"].iloc[0]
    # "Acme AI" -> space encoded as '+'
    assert "Acme+AI" in acme["news_url"]
    assert acme["hn_url"].startswith("https://hn.algolia.com/?q=")


def test_links_only_open_sources_no_forbidden_domains(sample_records):
    df = enrich.add_links(_df(sample_records))
    joined = " ".join(str(v) for col in enrich.LINK_BUILDERS for v in df[col].tolist())
    assert "crunchbase" not in joined.lower()
    assert "linkedin" not in joined.lower()


def test_links_empty_name_yields_empty(sample_records):
    import pandas as pd

    df = pd.DataFrame({"slug": ["x"], "name": [""]})
    out = enrich.add_links(df)
    assert out.loc[0, "news_url"] == ""
