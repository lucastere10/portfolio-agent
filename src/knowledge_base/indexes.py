"""Pre-computed indexes built once at startup for fast lookups."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from src.domain.models import KBEntry
from src.knowledge_base.loader import get_all, get_labs, get_projects


@dataclass(frozen=True)
class CatalogIndexes:
    """In-memory indexes over the knowledge catalog."""

    by_id: dict[str, KBEntry]
    by_domain: dict[str, list[KBEntry]]
    by_tag: dict[str, list[KBEntry]]
    featured: list[KBEntry]
    technologies: set[str]
    project_count: int
    lab_count: int


@lru_cache(maxsize=1)
def build_indexes() -> CatalogIndexes:
    """Build search indexes from the loaded catalog."""
    catalog = get_all()
    by_domain: dict[str, list[KBEntry]] = {}
    by_tag: dict[str, list[KBEntry]] = {}
    technologies: set[str] = set()
    featured: list[KBEntry] = []

    for entry in catalog:
        by_domain.setdefault(entry.domain, []).append(entry)
        for tag in entry.tags:
            by_tag.setdefault(tag.lower(), []).append(entry)
        for tech in entry.technologies:
            technologies.add(tech)
        if entry.featured:
            featured.append(entry)

    return CatalogIndexes(
        by_id={e.id: e for e in catalog},
        by_domain=by_domain,
        by_tag=by_tag,
        featured=featured,
        technologies=technologies,
        project_count=len(get_projects()),
        lab_count=len(get_labs()),
    )


def get_indexes() -> CatalogIndexes:
    return build_indexes()
