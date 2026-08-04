"""The source registry — where a new data source attaches.

A source is a small declaration plus one function. Registering it is the only
place its existence is written down: nothing else in the project holds a list of
sources, so **adding one touches nothing that already exists**. That property is
the whole reason the layers below are shaped the way they are.

Each source states its terms up front. A source whose licence forbids commercial
use, or whose data cannot be republished, is still usable — but only if that is
recorded next to it rather than discovered later.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class Source:
    """One place data comes from, and what it is allowed to be used for."""

    #: Short stable key. It is written into every fact this source produces.
    id: str
    title: str
    #: Where a human can go to check the source itself.
    url: str
    #: Terms in plain words: what may be done with the data, and what may not.
    licence: str
    #: The fields it can supply — the honest answer to "what do you cover".
    covers: tuple[str, ...]
    #: ``(frame, observed_at) -> rows`` in the facts schema.
    emits: Callable[[pd.DataFrame, str], list[dict[str, Any]]]


_REGISTRY: dict[str, Source] = {}


def register(source: Source) -> Source:
    """Add a source. A clashing id is refused rather than silently overwritten."""
    if source.id in _REGISTRY:
        raise ValueError(f"a source with id {source.id!r} is already registered")
    _REGISTRY[source.id] = source
    return source


def unregister(source_id: str) -> None:
    """Remove a source — used by tests, and when a source is retired."""
    _REGISTRY.pop(source_id, None)


def get(source_id: str) -> Source:
    """The source with this id, or a clear error naming what is available."""
    try:
        return _REGISTRY[source_id]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY)) or "none"
        raise KeyError(f"unknown source {source_id!r}; registered: {known}") from None


def all_sources() -> Sequence[Source]:
    """Every registered source, in a stable order."""
    return [_REGISTRY[key] for key in sorted(_REGISTRY)]


from . import yc  # noqa: E402,F401  — importing it registers it

__all__ = ["Source", "all_sources", "get", "register", "unregister", "yc"]
