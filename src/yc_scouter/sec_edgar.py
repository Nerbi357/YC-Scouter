"""SEC EDGAR — can a YC company be found among Form D filers by name?

**This module exists to answer one question with a number**, before anything is
built on the answer. Form D is the closest thing to real funding data that is free
and official: a US company raising a private round files it, and the filing carries
the issuer, the date and the offering amount. What is *not* known is how many YC
companies can actually be tied to a filing — so this module measures that on a
sample, and the plan follows the measurement rather than the hope.

**The naive version on purpose.** Matching is by name, normalised only for legal
suffixes and punctuation. It will miss companies that renamed, that file under a
holding company, or that never filed at all. That failure rate *is* the result: it
is what justifies (or refutes) building real entity resolution afterwards.

**Three rules the counting obeys**, because a measurement that flatters itself is
worse than none:

* several filers matching a name is **ambiguous**, never "the first one";
* a request that failed is an **error**, never "no filings" — a blocked check says
  nothing about the target;
* every company in the sample lands in exactly one bucket.

Access notes (from SEC's developer guidance): the browse-edgar company search is
open, needs no key, and asks every client to identify itself in the User-Agent and
to stay under roughly ten requests a second. The default agent here names the
project and its repository — a personal address never goes into a public
repository; set ``SEC_USER_AGENT`` in the environment to supply one at run time.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from . import identities

SEARCH_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
    "&company={name}&type=D&dateb=&owner=include&count=40&output=atom"
)

DEFAULT_USER_AGENT = "YC-Scouter/2.0 (+https://github.com/Nerbi357/YC-Scouter)"

SOURCE_NOTE = "SEC EDGAR browse-edgar company search, forms=D"
METHOD_NOTE = "exact name match after normalising punctuation and legal suffixes"

_PUNCT = re.compile(r"[^\w\s]+")
_SPACE = re.compile(r"\s+")
#: "NAME (0001812216) (Filer)" — the title browse-edgar puts on each match.
_TITLE = re.compile(r"^(?P<name>.+?)\s*\((?P<cik>\d{6,10})\)")


def user_agent() -> str:
    """What we tell SEC we are. Overridable so a contact never gets committed."""
    return os.environ.get("SEC_USER_AGENT") or DEFAULT_USER_AGENT


#: One canonical name normaliser for the whole project — SEC and YC must agree on
#: what a name is, or they will never join.
normalise_name = identities.normalise_name


def take_sample(companies: Sequence[dict], size: int) -> list[dict]:
    """A deterministic spread across the whole list, not its head.

    Deterministic so a rerun measures the same companies (a moving sample would
    make two runs incomparable), and spread out so the number is not an artefact of
    the oldest batch.
    """
    rows = sorted(companies, key=lambda c: int(c["id"]))
    if size <= 0 or not rows:
        return []
    if size >= len(rows):
        return rows
    step = len(rows) / size
    return [rows[int(i * step)] for i in range(size)]


class Blocked(RuntimeError):
    """The service refused us — which says nothing about the companies."""


def _fetch(url: str, *, headers: dict[str, str] | None = None, **_: Any) -> str:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # The status code alone is not a diagnosis. SEC explains its refusals in the
        # body ("Your Request Originates from an Undeclared Automated Tool"), and
        # without that text a run reports 403 two hundred times and teaches nothing.
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover - the body is a bonus, never required
            detail = ""
        detail = _SPACE.sub(" ", re.sub(r"<[^>]+>", " ", detail)).strip()[:300]
        raise Blocked(f"HTTP {exc.code}: {detail or exc.reason}") from exc


def declares_a_contact(agent: str | None = None) -> bool:
    """SEC asks automated clients to name themselves *and* a contact address."""
    return "@" in (agent if agent is not None else user_agent())


def probe(*, fetch: Callable[..., str] = _fetch) -> tuple[bool, str]:
    """One request, to learn whether the service will talk to us at all.

    Two hundred identical refusals are two hundred wasted requests and one lost
    afternoon. This asks once and reports what came back, so a blocked run stops
    being mistaken for a company that never filed.
    """
    url = SEARCH_URL.format(name=urllib.parse.quote("Stripe"))
    try:
        fetch(url, headers=_headers(), name="Stripe")
        return True, "ok"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _headers() -> dict[str, str]:
    return {"User-Agent": user_agent(), "Accept": "application/atom+xml, text/xml, */*"}


def parse_candidates(xml_text: str) -> list[dict[str, str]]:
    """Filers found in a browse-edgar Atom response.

    Two shapes come back and both are handled: a list of ``<entry>`` titles when
    several filers matched, and a single ``<company-info>`` block when the search
    resolved to one. Anything else raises, so the caller records an error rather
    than a false negative.
    """
    root = ET.fromstring(xml_text)
    out: list[dict[str, str]] = []

    for info in root.iter():
        tag = info.tag.rsplit("}", 1)[-1]
        if tag != "company-info":
            continue
        cik = name = ""
        for child in info:
            child_tag = child.tag.rsplit("}", 1)[-1]
            if child_tag == "cik":
                cik = (child.text or "").strip()
            elif child_tag == "conformed-name":
                name = (child.text or "").strip()
        if cik and name:
            out.append({"cik": cik, "name": name})

    if out:
        return out

    for entry in root.iter():
        if entry.tag.rsplit("}", 1)[-1] != "entry":
            continue
        for child in entry:
            if child.tag.rsplit("}", 1)[-1] != "title":
                continue
            found = _TITLE.match((child.text or "").strip())
            if found:
                out.append({"cik": found.group("cik"), "name": found.group("name").strip()})
    return out


@dataclass(frozen=True)
class Verdict:
    """One company's outcome. ``cik`` is set only when a single filer matched."""

    match: str  # matched | ambiguous | none | error
    cik: str | None = None
    candidates: int = 0
    #: Filers the search returned that are *not* this company. A high number means
    #: the name is common, and a name-only match there deserves less trust.
    others: int = 0


def classify(name: str, candidates: Iterable[dict[str, str]]) -> Verdict:
    """Decide what a set of filers means for this company — conservatively."""
    wanted = normalise_name(name)
    everything = list(candidates)
    hits = [c for c in everything if normalise_name(c.get("name", "")) == wanted]
    others = len(everything) - len(hits)
    if not hits:
        return Verdict("none", None, 0, others)
    if len(hits) > 1:
        # Two filers with the same name is exactly the case that produces a
        # publicly wrong profile. Refuse to choose.
        return Verdict("ambiguous", None, len(hits), others)
    return Verdict("matched", hits[0].get("cik"), 1, others)


def measure_coverage(
    companies: Sequence[dict],
    *,
    fetch: Callable[..., str] = _fetch,
    pause: float = 0.15,
    today: str | None = None,
) -> dict[str, Any]:
    """Look every company up and count the outcomes.

    ``pause`` keeps the request rate well under SEC's limit; tests pass 0.
    """
    rows: list[dict[str, Any]] = []
    counts = {"matched": 0, "ambiguous": 0, "none": 0, "error": 0}

    ok, detail = probe(fetch=fetch)
    if not ok:
        # Stop before spending two hundred requests on the same refusal. The report
        # says "blocked", never "none" — a service that will not answer has told us
        # nothing at all about these companies.
        return {
            "generated_at": today or dt.date.today().isoformat(),
            "source": SOURCE_NOTE,
            "method": METHOD_NOTE,
            "user_agent": user_agent(),
            "status": "blocked",
            "blocked_reason": detail,
            "hint": (
                "SEC refuses undeclared automated clients. Set SEC_USER_AGENT to a "
                "string containing a contact address, e.g. 'YC-Scouter research "
                "(you@example.com)', and run again."
                if not declares_a_contact()
                else "The request was refused even with a declared contact — check the "
                "hint text above before changing anything else."
            ),
            "sample_size": 0,
            "counts": counts,
            "rows": [],
        }

    for company in companies:
        name = str(company.get("name", "")).strip()
        url = SEARCH_URL.format(name=urllib.parse.quote(name))
        note = ""
        try:
            body = fetch(url, headers=_headers(), name=name)
            verdict = classify(name, parse_candidates(body))
        except Exception as exc:  # network, XML, anything — never a silent "none"
            verdict, note = Verdict("error"), f"{type(exc).__name__}: {exc}"
        counts[verdict.match] += 1
        rows.append(
            {
                "id": company.get("id"),
                "name": name,
                "match": verdict.match,
                "cik": verdict.cik,
                "candidates": verdict.candidates,
                "others": verdict.others,
                "note": note,
            }
        )
        if pause:
            time.sleep(pause)

    return {
        "generated_at": today or dt.date.today().isoformat(),
        "source": SOURCE_NOTE,
        "method": METHOD_NOTE,
        "user_agent": user_agent(),
        "status": "measured",
        "sample_size": len(rows),
        "counts": counts,
        "rows": rows,
    }
