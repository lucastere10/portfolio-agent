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

from src.adk.instruction import warmup_instruction_cache
from src.adk.runtime import init_runner
from src.api.v1 import router as v1_router
from src.config import settings
from src.knowledge_base.indexes import build_indexes
from src.knowledge_base.loader import load_catalog, load_persona, load_profile, load_skills
from src.providers.factory import (
    configure_provider_env,
    has_llm_credentials,
    validate_model_available,
)
from src.session.service import init_session_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load knowledge, build indexes, initialize ADK runner."""
    configure_provider_env()

    if not settings.debug and not has_llm_credentials():
        raise RuntimeError(
            "LLM credentials are required in production "
            f"(provider={settings.llm_provider})"
        )

    catalog = load_catalog()
    profile = load_profile()
    persona = load_persona()
    skills = load_skills()
    indexes = build_indexes()
    warmup_instruction_cache()

    logger.info(
        "Knowledge base loaded: %d entries (%d projects, %d labs)",
        len(catalog),
        indexes.project_count,
        indexes.lab_count,
    )
    logger.info(
        "Profile: %s | Persona: %s | Skills: %d technologies",
        profile.get("name", "unknown"),
        "loaded" if persona else "missing",
        len(skills.get("technologies", [])),
    )

    init_session_service()

    try:
        validate_model_available()
    except Exception as exc:
        logger.warning("Model validation skipped or failed: %s", exc)

    init_runner()
    logger.info("Portfolio Agent ready (provider=%s)", settings.llm_provider)

    yield
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
