"""Semantic search API route."""

from fastapi import APIRouter

from src.domain.models import SearchRequest, SearchResponse
from src.tools.search import search_projects

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Search the portfolio catalog by natural language query."""
    results = search_projects(
        query=request.query,
        limit=request.limit,
        filter_type=request.filter_type,
    )
    return SearchResponse(query=request.query, results=results, total=len(results))
