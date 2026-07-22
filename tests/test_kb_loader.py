"""KB loader / schema regression (A5)."""

from __future__ import annotations

from src.domain.models import KBEntry
from src.knowledge_base.indexes import get_indexes
from src.knowledge_base.loader import get_all, get_by_id, get_labs, get_projects, load_catalog


def test_catalog_loads_and_validates():
    catalog = load_catalog()
    assert len(catalog) > 0
    for entry in catalog.values():
        assert isinstance(entry, KBEntry)
        assert entry.id
        assert entry.type in {"project", "lab", "personal_project"}


def test_catalog_counts_positive():
    assert len(get_projects()) >= 1
    assert len(get_labs()) >= 1
    assert len(get_all()) == len(load_catalog())


def test_ai_agents_adk_has_cold_start_fact():
    entry = get_by_id("ai-agents-adk")
    assert entry is not None
    blob = " ".join(entry.challenges).lower()
    assert "cold start" in blob or "cold-start" in blob


def test_indexes_coherent():
    indexes = get_indexes()
    catalog = load_catalog()
    assert indexes.project_count == len(get_projects())
    assert indexes.lab_count == len(get_labs())
    assert set(indexes.by_id) == set(catalog)
    assert len(indexes.by_tag) > 0
    assert len(indexes.by_domain) > 0
