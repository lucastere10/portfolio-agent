"""Semantic LLM contracts — provider-agnostic knobs and model identity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from google.genai import types

ProviderName = Literal["openai", "gemini"]
TokenLimitParam = Literal["max_tokens", "max_completion_tokens", "max_output_tokens"]


@dataclass(frozen=True)
class GenerationContract:
    """Product-level generation settings shared by all adapters."""

    temperature: float = 0.5
    max_output_tokens: int = 1024


@dataclass(frozen=True)
class ModelRef:
    """Parsed preference: ``provider:model_id``."""

    provider: ProviderName
    model_id: str

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model_id}"


@dataclass(frozen=True)
class ModelProfile:
    """Per-model API quirks — versioned in code, not env."""

    provider: ProviderName
    model_id: str
    token_limit_param: TokenLimitParam
    supports_temperature: bool = True
    # OpenAI chat.completions: required for some models when tools are used
    # (e.g. gpt-5.6-luna → "none"). None = omit the param.
    reasoning_effort: Literal["none", "low", "medium", "high"] | None = None

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model_id}"


def parse_model_ref(value: str) -> ModelRef:
    """Parse ``provider:model_id`` (e.g. ``openai:gpt-5.6-luna``)."""
    raw = (value or "").strip()
    if ":" not in raw:
        raise ValueError(
            f"Invalid LLM_MODEL {value!r}; expected 'provider:model_id' "
            "(e.g. 'openai:gpt-5.6-luna' or 'gemini:gemini-3.5-flash')"
        )
    provider, model_id = raw.split(":", 1)
    provider = provider.strip().lower()
    model_id = model_id.strip()
    if provider not in ("openai", "gemini"):
        raise ValueError(
            f"Unsupported LLM provider {provider!r}; expected 'openai' or 'gemini'"
        )
    if not model_id:
        raise ValueError(f"Invalid LLM_MODEL {value!r}; model_id is empty")
    return ModelRef(provider=provider, model_id=model_id)  # type: ignore[arg-type]


def generation_to_genai_config(contract: GenerationContract) -> types.GenerateContentConfig:
    """Map the semantic contract to ADK / google-genai GenerateContentConfig."""
    return types.GenerateContentConfig(
        temperature=contract.temperature,
        max_output_tokens=contract.max_output_tokens,
    )
