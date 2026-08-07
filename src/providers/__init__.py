"""LLM provider adapters, contracts, and routing."""

from src.providers.contract import (
    GenerationContract,
    ModelProfile,
    ModelRef,
    generation_to_genai_config,
    parse_model_ref,
)
from src.providers.factory import (
    build_routing_llm,
    configure_provider_env,
    has_llm_credentials,
    validate_model_available,
)
from src.providers.registry import FALLBACK_CANDIDATES, GENERATION, PROFILES, get_profile

__all__ = [
    "FALLBACK_CANDIDATES",
    "GENERATION",
    "GenerationContract",
    "ModelProfile",
    "ModelRef",
    "PROFILES",
    "build_routing_llm",
    "configure_provider_env",
    "generation_to_genai_config",
    "get_profile",
    "has_llm_credentials",
    "parse_model_ref",
    "validate_model_available",
]
