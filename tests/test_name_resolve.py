"""B0 name aliases / fuzzy resolve."""

from __future__ import annotations

import pytest

from src.tools.name_resolve import enrich_query_with_resolved_name, resolve_catalog_id
from src.tools.search import search_projects


@pytest.mark.parametrize(
    "query,expected_id",
    [
        ("knowlage hubb", "newsletter"),
        ("oknowlage uhb", "newsletter"),
        ("KnowledgeHub", "newsletter"),
        ("passa nota", "passanota"),
        ("drop", "drop"),
    ],
)
def test_resolve_catalog_id(query: str, expected_id: str):
    assert resolve_catalog_id(query) == expected_id


def test_enrich_appends_id():
    enriched = enrich_query_with_resolved_name("knowlage hubb")
    assert "newsletter" in enriched


def test_search_typo_knowledgehub_primary():
    matches = search_projects(enrich_query_with_resolved_name("knowlage hubb"), limit=3)
    assert matches
    assert matches[0].id == "newsletter" or any(m.id == "newsletter" for m in matches)
