"""ADK function tools backed by the in-memory knowledge catalog."""

from __future__ import annotations

from typing import Literal

from src.tools.search import generate_learning_path, get_project, search_projects


def search_portfolio(
    query: str,
    limit: int = 5,
    filter_type: Literal["all", "project", "lab"] = "all",
) -> list[dict]:
    """
    Search portfolio projects and labs by natural language query.

    Args:
        query: What the visitor is looking for (technology, domain, challenge).
        limit: Maximum number of results (default 5).
        filter_type: Filter by "project", "lab", or "all".

    Returns:
        Ranked matches with id, type, title, score, and slug.
    """
    results = search_projects(query, limit=limit, filter_type=filter_type)
    return [r.model_dump() for r in results]


def get_portfolio_item(project_id: str) -> dict:
    """
    Get full details for a specific project or lab by ID.

    Args:
        project_id: Catalog ID (e.g. "ai-agents-adk", "mcp-explorer").

    Returns:
        Full entry details or an error message if not found.
    """
    entry = get_project(project_id)
    if entry is None:
        return {"error": f"Item '{project_id}' not found in the portfolio catalog."}
    return entry.model_dump()


def build_learning_path(query: str, limit: int = 6) -> list[dict]:
    """
    Generate a structured learning path of labs and projects for a topic.

    Args:
        query: Learning goal or topic (e.g. "AI agents", "payment systems").
        limit: Maximum items in the path (default 6).

    Returns:
        Ordered list of labs and projects in recommended learning order.
    """
    results = generate_learning_path(query, limit=limit)
    return [r.model_dump() for r in results]
