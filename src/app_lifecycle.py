"""Application lifecycle and readiness state."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from src.adk.instruction import warmup_instruction_cache
from src.adk.runtime import init_runner
from src.config import settings
from src.knowledge_base.indexes import build_indexes
from src.knowledge_base.loader import load_catalog, load_persona, load_profile, load_skills
from src.providers.factory import (
    configure_provider_env,
    has_llm_credentials,
    validate_model_available,
)
from src.session.service import init_session_service

logger = logging.getLogger(__name__)


async def bootstrap_agent(app) -> None:
    """Load knowledge base and initialize ADK in the background."""
    try:
        configure_provider_env()

        if not settings.debug and not has_llm_credentials():
            raise RuntimeError(
                "LLM credentials are required in production "
                f"(provider={settings.llm_provider}). "
                "Set PORTFOLIO_AGENT_GEMINI_API_KEY via Secret Manager."
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
        app.state.agent_ready = True
        logger.info("Portfolio Agent ready (provider=%s)", settings.llm_provider)
    except Exception as exc:
        app.state.agent_startup_error = str(exc)
        logger.exception("Portfolio Agent startup failed: %s", exc)


def start_bootstrap(app) -> asyncio.Task[None]:
    app.state.agent_ready = False
    app.state.agent_startup_error = None
    task = asyncio.create_task(bootstrap_agent(app))
    app.state.bootstrap_task = task
    return task


async def shutdown_bootstrap(app) -> None:
    task = getattr(app.state, "bootstrap_task", None)
    if task is None:
        return

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
