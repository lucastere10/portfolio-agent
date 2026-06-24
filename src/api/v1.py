"""API v1 router aggregation."""

from fastapi import APIRouter, Depends

from src.api.deps import require_agent_ready
from src.api.routes.chat import router as chat_router
from src.api.routes.projects import router as projects_router
from src.api.routes.search import router as search_router

router = APIRouter(dependencies=[Depends(require_agent_ready)])
router.include_router(chat_router)
router.include_router(projects_router)
router.include_router(search_router)
