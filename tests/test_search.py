"""Lexical retrieval primary matches (A5) — no LLM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.tools.search import search_projects

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "docs" / "baseline" / "golden-cases.json"


def _primary(query: str) -> str | None:
    matches = search_projects(query, limit=5)
    return matches[0].id if matches else None


def _standalone_primary_cases() -> list[tuple[str, str]]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    checks: list[tuple[str, str]] = []
    for case in data["cases"]:
        expected = case.get("expected_primary")
        if not expected:
            continue
        if case.get("family") == "follow_up":
            continue
        checks.append((case["message"], expected))
    return checks


@pytest.mark.parametrize("query,expected", _standalone_primary_cases())
def test_golden_primary(query: str, expected: str):
    assert _primary(query) == expected


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Como você resolveu cold start no Cloud Run?", "ai-agents-adk"),
        ("cold start Cloud Run", "ai-agents-adk"),
    ],
)
def test_cold_start_primary(query: str, expected: str):
    assert _primary(query) == expected


def test_signature_project_primary_is_featured_work():
    from src.orchestration.hints import SIGNATURE_SEARCH_QUERY

    matches = search_projects(SIGNATURE_SEARCH_QUERY, limit=5)
    assert matches
    assert matches[0].id == "ai-agents-adk"
