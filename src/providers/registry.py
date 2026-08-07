"""Model profiles and fallback candidates (code-owned, not env)."""

from __future__ import annotations

from src.providers.contract import GenerationContract, ModelProfile, ModelRef, parse_model_ref

GENERATION = GenerationContract(temperature=0.5, max_output_tokens=1024)

PROFILES: dict[str, ModelProfile] = {
    "openai:gpt-5.6-luna": ModelProfile(
        provider="openai",
        model_id="gpt-5.6-luna",
        token_limit_param="max_completion_tokens",
        # Reasoning / Luna family: only default temperature (1) is accepted.
        supports_temperature=False,
        # chat.completions + function tools requires reasoning_effort=none.
        reasoning_effort="none",
    ),
    "openai:gpt-4.1-mini": ModelProfile(
        provider="openai",
        model_id="gpt-4.1-mini",
        token_limit_param="max_tokens",
    ),
    "gemini:gemini-3.5-flash": ModelProfile(
        provider="gemini",
        model_id="gemini-3.5-flash",
        token_limit_param="max_output_tokens",
    ),
    "gemini:gemini-2.5-flash": ModelProfile(
        provider="gemini",
        model_id="gemini-2.5-flash",
        token_limit_param="max_output_tokens",
    ),
}

# Tried after the preferred LLM_MODEL (preferred is prepended and deduped).
FALLBACK_CANDIDATES: tuple[str, ...] = (
    "gemini:gemini-3.5-flash",
    "openai:gpt-4.1-mini",
)


def get_profile(ref: ModelRef | str) -> ModelProfile:
    """Lookup profile by ModelRef or ``provider:model_id`` key."""
    key = ref.key if isinstance(ref, ModelRef) else parse_model_ref(ref).key
    try:
        return PROFILES[key]
    except KeyError as exc:
        known = ", ".join(sorted(PROFILES))
        raise KeyError(
            f"Unknown model profile {key!r}. Register it in PROFILES. Known: {known}"
        ) from exc


def build_candidate_refs(preferred: ModelRef | str) -> list[ModelRef]:
    """
    Ordered chain: preferred first, then FALLBACK_CANDIDATES (deduped).

    Credentials filtering happens in the factory (skip missing API keys).
    """
    pref = preferred if isinstance(preferred, ModelRef) else parse_model_ref(preferred)
    # Validate preferred exists in registry early.
    get_profile(pref)

    seen: set[str] = set()
    ordered: list[ModelRef] = []
    for raw in (pref.key, *FALLBACK_CANDIDATES):
        ref = parse_model_ref(raw)
        if ref.key in seen:
            continue
        get_profile(ref)  # fail fast on bad fallback entries
        seen.add(ref.key)
        ordered.append(ref)
    return ordered
