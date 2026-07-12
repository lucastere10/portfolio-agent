"""
Portfolio Agent — FastAPI entry point.

Thin HTTP layer over the Google ADK conversational agent.
Knowledge base and indexes are loaded once at startup.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1 import router as v1_router
from src.app_lifecycle import shutdown_bootstrap, start_bootstrap
from src.config import settings
from src.knowledge_base.indexes import build_indexes
from src.knowledge_base.loader import load_catalog
from src.providers.factory import has_llm_credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bind HTTP port immediately; finish heavy init in the background."""
    start_bootstrap(app)
    yield
    await shutdown_bootstrap(app)
    logger.info("Portfolio Agent stopped")


app = FastAPI(
    title="Portfolio Agent",
    version=settings.app_version,
    description=(
        "Conversational portfolio agent powered by Google ADK — "
        "semantic project and lab recommendations."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    startup_error = getattr(app.state, "agent_startup_error", None)
    if startup_error:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "version": settings.app_version,
                "llm_configured": False,
                "error": startup_error,
            },
        )

    if not getattr(app.state, "agent_ready", False):
        return JSONResponse(
            status_code=503,
            content={
                "status": "starting",
                "version": settings.app_version,
                "llm_configured": has_llm_credentials(),
            },
        )

    catalog = load_catalog()
    indexes = build_indexes()
    llm_configured = has_llm_credentials()
    body = {
        "status": "ok" if llm_configured else "degraded",
        "version": settings.app_version,
        "catalog_size": len(catalog),
        "projects": indexes.project_count,
        "labs": indexes.lab_count,
        "provider": settings.llm_provider,
        "llm_configured": llm_configured,
    }
    if not llm_configured:
        return JSONResponse(status_code=503, content=body)
    return body


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    content: dict[str, str] = {"error": "Internal server error"}
    if settings.debug:
        content["detail"] = str(exc)
    return JSONResponse(status_code=500, content=content)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
