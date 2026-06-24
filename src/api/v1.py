"""API v1 router aggregation."""

from fastapi import APIRouter

from src.api.routes.chat import router as chat_router
from src.api.routes.projects import router as projects_router
from src.api.routes.search import router as search_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(projects_router)
router.include_router(search_router)
