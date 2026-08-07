"""
LLM provider factory — builds the routing BaseLlm from settings + registry.

Preferred model comes from LLM_MODEL; fallbacks live in registry.py.
"""

from __future__ import annotations

import logging
import os

from google.adk.models.base_llm import BaseLlm

from src.config import settings
from src.providers.contract import ModelRef, ProviderName, parse_model_ref
from src.providers.gemini_llm import GeminiPortfolioLlm
from src.providers.openai_llm import OpenAIPortfolioLlm
from src.providers.registry import build_candidate_refs, get_profile
from src.providers.router import PortfolioLlmRouter

logger = logging.getLogger(__name__)


def configure_provider_env() -> None:
    """
    Bridge PORTFOLIO_AGENT_* settings into env vars expected by SDKs.

    google-genai reads GOOGLE_API_KEY / GEMINI_API_KEY.
    OpenAI SDK reads OPENAI_API_KEY (also passed explicitly to our adapter).
    """
    if settings.gemini_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
        logger.info("Gemini key bridged to GOOGLE_API_KEY / GEMINI_API_KEY")
    else:
        logger.warning("PORTFOLIO_AGENT_GEMINI_API_KEY is empty")

    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        logger.info("OpenAI key bridged to OPENAI_API_KEY")
    else:
        logger.warning("PORTFOLIO_AGENT_OPENAI_API_KEY is empty")

    if settings.openai_base_url:
        os.environ["OPENAI_API_BASE"] = settings.openai_base_url.rstrip("/")
        logger.info("OpenAI base URL bridged to OPENAI_API_BASE")


def preferred_model_ref() -> ModelRef:
    return parse_model_ref(settings.llm_model)


def has_provider_credentials(provider: ProviderName) -> bool:
    if provider == "openai":
        return bool(settings.openai_api_key)
    return bool(settings.gemini_api_key)


def has_llm_credentials() -> bool:
    """Whether an API key is configured for the preferred provider."""
    try:
        ref = preferred_model_ref()
    except ValueError:
        return False
    return has_provider_credentials(ref.provider)


def _build_adapter(ref: ModelRef) -> BaseLlm:
    profile = get_profile(ref)
    if profile.provider == "openai":
        return OpenAIPortfolioLlm.from_profile(
            profile,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return GeminiPortfolioLlm.from_profile(profile)


def build_routing_llm() -> PortfolioLlmRouter:
    """
    Build the single BaseLlm used by LlmAgent.

    Chain: preferred (LLM_MODEL) + registry fallbacks, skipping missing keys.
    """
    configure_provider_env()
    preferred = preferred_model_ref()
    get_profile(preferred)

    adapters: list[BaseLlm] = []
    for ref in build_candidate_refs(preferred):
        if not has_provider_credentials(ref.provider):
            logger.warning(
                "Skipping LLM candidate %s — missing %s credentials",
                ref.key,
                ref.provider,
            )
            continue
        adapters.append(_build_adapter(ref))

    if not adapters:
        raise RuntimeError(
            f"No LLM candidates available for preferred {preferred.key!r}. "
            "Set PORTFOLIO_AGENT_OPENAI_API_KEY and/or PORTFOLIO_AGENT_GEMINI_API_KEY."
        )

    logger.info(
        "LLM router ready: preferred=%s candidates=%s",
        preferred.key,
        [getattr(a, "profile_key", a.model) for a in adapters],
    )
    return PortfolioLlmRouter(model=preferred.key, candidates=adapters)


def validate_model_available() -> None:
    """Fail fast on unknown preferred profile; warn if credentials missing."""
    preferred = preferred_model_ref()
    get_profile(preferred)
    if not has_provider_credentials(preferred.provider):
        raise RuntimeError(
            f"Preferred model {preferred.key} requires "
            f"PORTFOLIO_AGENT_{preferred.provider.upper()}_API_KEY"
        )
    # Ensure fallbacks in registry resolve (even if skipped for missing keys).
    build_candidate_refs(preferred)
