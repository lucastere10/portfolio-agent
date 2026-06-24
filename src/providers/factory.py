"""
LLM provider abstraction for Google ADK.

Selects Gemini or OpenAI via configuration and configures the runtime environment.
Swap providers by changing LLM_PROVIDER without touching agent code.
"""

from __future__ import annotations

import logging
import os
from typing import Union

from google.adk.models.base_llm import BaseLlm
from google.adk.models.registry import LLMRegistry

from src.config import settings

logger = logging.getLogger(__name__)


def configure_provider_env() -> None:
    """
    Bridge PORTFOLIO_AGENT_* settings into env vars expected by ADK SDKs.

    google-genai (Gemini) reads GOOGLE_API_KEY or GEMINI_API_KEY — not our
    PORTFOLIO_AGENT_GEMINI_API_KEY. OpenAI via LiteLLM reads OPENAI_API_KEY.
    """
    if settings.gemini_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
        logger.info("Gemini key bridged from PORTFOLIO_AGENT_GEMINI_API_KEY to GOOGLE_API_KEY")
    else:
        logger.warning("PORTFOLIO_AGENT_GEMINI_API_KEY is empty")

    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        logger.info("OpenAI key bridged from PORTFOLIO_AGENT_OPENAI_API_KEY to OPENAI_API_KEY")
    else:
        logger.warning("PORTFOLIO_AGENT_OPENAI_API_KEY is empty")

    if settings.openai_base_url:
        os.environ["OPENAI_API_BASE"] = settings.openai_base_url.rstrip("/")
        logger.info("OpenAI base URL bridged to OPENAI_API_BASE")


def resolve_model() -> Union[str, BaseLlm]:
    """
    Return the ADK model identifier for the configured provider.

    Gemini models resolve via the built-in Gemini class.
    OpenAI models resolve via the OpenAILlm integration (gpt-* pattern).
    """
    configure_provider_env()

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            logger.warning("OpenAI provider selected but PORTFOLIO_AGENT_OPENAI_API_KEY is empty")
        logger.info("ADK model provider: OpenAI (%s)", settings.openai_model)
        return settings.openai_model

    if not settings.gemini_api_key:
        logger.warning("Gemini provider selected but PORTFOLIO_AGENT_GEMINI_API_KEY is empty")

    logger.info("ADK model provider: Gemini (%s)", settings.gemini_model)
    return settings.gemini_model


def has_llm_credentials() -> bool:
    """Whether an API key is configured for the active provider."""
    if settings.llm_provider == "openai":
        return bool(settings.openai_api_key)
    return bool(settings.gemini_api_key)


def validate_model_available() -> None:
    """Resolve the model at startup to fail fast on misconfiguration."""
    model = resolve_model()
    if isinstance(model, str):
        LLMRegistry.resolve(model)
