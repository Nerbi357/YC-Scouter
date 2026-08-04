"""Identities — the one place that decides whether two records are one company.

Every source spells companies differently: YC has a name and a website, SEC has a
filer name, GitHub has an organisation. Joining them is where a multi-source
project either earns trust or destroys it, so the rules live here and nowhere else.

**The domain is the strong key.** A company's own website is close to unique and
survives renaming. Names are weak: they collide, they carry legal suffixes, and
they change.

**Refusing to answer is a valid answer.** Two candidates for one name resolve to
*nothing*, with both kept visible for a person to settle. One publicly wrong merge —
two different companies fused into a single profile — costs more than fifty missing
matches, and it is the failure a visitor notices first.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any

#: Legal forms that say nothing about which company this is.
_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "co",
    "company",
    "plc",
    "pbc",
    "lp",
    "llp",
    "sa",
    "sas",
    "ab",
    "as",
    "oy",
    "bv",
    "nv",
    "gmbh",
    "ug",
    "srl",
    "spa",
    "pte",
    "pty",
    "kk",
    "holdings",
    "holding",
}
_PUNCT = re.compile(r"[^\w\s]+")
_SPACE = re.compile(r"\s+")
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)
#: A hostname worth trusting: at least one dot, letters in the last label.
_HOST = re.compile(r"^(?=.{1,253}$)([a-z0-9-]+\.)+[a-z]{2,}$")


def normalise_name(name: str | None) -> str:
    """Lowercase, drop punctuation and trailing legal forms.

    ``Motion, Inc.`` and ``MOTION INC`` are the same name; ``Motion`` and
    ``Motion Capital`` are not, and this must never merge them.
    """
    text = _SPACE.sub(" ", _PUNCT.sub(" ", str(name or ""))).strip().lower()
    words = text.split()
    while words and words[-1] in _SUFFIXES:
        words.pop()
    return " ".join(words)


def normalise_domain(url: str | None) -> str | None:
    """The host a URL points at, or ``None`` when there is not one.

    Returning ``None`` rather than a best guess matters: a wrong domain silently
    joins two unrelated companies, and nothing downstream would notice.
    """
    text = str(url or "").strip().lower()
    if not text or text.startswith("mailto:"):
        return None
    text = _SCHEME.sub("", text)
    host = text.split("/")[0].split("?")[0].split("#")[0].split("@")[-1]
    host = host.split(":")[0].rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host if _HOST.match(host) else None


def identify(company: Mapping[str, Any]) -> dict[str, Any]:
    """Every key a future source might join on, for one company."""
    return {
        "company_id": int(company["id"]),
        "name": str(company.get("name") or ""),
        "name_key": normalise_name(company.get("name")),
        "domain": normalise_domain(company.get("website")),
    }


def build(companies: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The identity table: one row per company, all its join keys."""
    return [identify(c) for c in companies]


@dataclass(frozen=True)
class Match:
    """What the evidence supports — including "not enough to say"."""

    company_id: int | None
    basis: str  # domain | name | ambiguous | none
    confidence: float = 0.0
    candidates: list[int] = dataclass_field(default_factory=list)


def resolve(
    table: Sequence[Mapping[str, Any]],
    *,
    domain: str | None = None,
    name: str | None = None,
) -> Match:
    """Find the company a domain or a name refers to, conservatively.

    A domain match is strong evidence; a name match is weak and is reported as
    such. Several candidates resolve to ``None`` with the candidates listed, so a
    person can settle it and the machine never invents the answer.
    """
    host = normalise_domain(domain)
    if host:
        hits = [r for r in table if r.get("domain") == host]
        if len(hits) == 1:
            return Match(int(hits[0]["company_id"]), "domain", 0.95)
        if len(hits) > 1:
            return Match(None, "ambiguous", 0.0, [int(r["company_id"]) for r in hits])

    key = normalise_name(name)
    if key:
        hits = [r for r in table if r.get("name_key") == key]
        if len(hits) == 1:
            return Match(int(hits[0]["company_id"]), "name", 0.6)
        if len(hits) > 1:
            return Match(None, "ambiguous", 0.0, [int(r["company_id"]) for r in hits])

    return Match(None, "none", 0.0)
