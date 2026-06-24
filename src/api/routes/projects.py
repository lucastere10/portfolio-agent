"""Projects and labs catalog API routes."""

from fastapi import APIRouter, HTTPException

from src.domain.models import ProjectDetail
from src.knowledge_base.loader import get_all, get_by_id

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectDetail])
async def list_projects() -> list[ProjectDetail]:
    """List all catalog entries (projects + labs)."""
    return [ProjectDetail(**e.model_dump()) for e in get_all()]


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str) -> ProjectDetail:
    """Get a single catalog entry by ID."""
    entry = get_by_id(project_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found in catalog.",
        )
    return ProjectDetail(**entry.model_dump())
