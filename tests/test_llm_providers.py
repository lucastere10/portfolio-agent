"""Unit tests for LLM contracts, profiles, OpenAI kwargs, and router."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from typing_extensions import override

from src.providers.contract import parse_model_ref
from src.providers.openai_llm import build_openai_kwargs
from src.providers.registry import (
    FALLBACK_CANDIDATES,
    build_candidate_refs,
    get_profile,
)
from src.providers.router import (
    PortfolioLlmRouter,
    format_provider_error,
    is_retryable,
)


def test_parse_model_ref_ok() -> None:
    ref = parse_model_ref("openai:gpt-5.6-luna")
    assert ref.provider == "openai"
    assert ref.model_id == "gpt-5.6-luna"
    assert ref.key == "openai:gpt-5.6-luna"


def test_parse_model_ref_invalid() -> None:
    with pytest.raises(ValueError):
        parse_model_ref("gpt-5.6-luna")
    with pytest.raises(ValueError):
        parse_model_ref("anthropic:claude")


def test_get_profile_known() -> None:
    profile = get_profile("openai:gpt-5.6-luna")
    assert profile.token_limit_param == "max_completion_tokens"
    profile_legacy = get_profile("openai:gpt-4.1-mini")
    assert profile_legacy.token_limit_param == "max_tokens"


def test_get_profile_unknown() -> None:
    with pytest.raises(KeyError):
        get_profile("openai:does-not-exist")


def test_build_candidate_refs_dedupes_preferred() -> None:
    refs = build_candidate_refs("gemini:gemini-3.5-flash")
    keys = [r.key for r in refs]
    assert keys[0] == "gemini:gemini-3.5-flash"
    assert keys.count("gemini:gemini-3.5-flash") == 1
    assert "openai:gpt-4.1-mini" in keys
    for fb in FALLBACK_CANDIDATES:
        assert fb in keys or fb == keys[0]


def test_build_openai_kwargs_max_completion_tokens() -> None:
    profile = get_profile("openai:gpt-5.6-luna")
    assert profile.supports_temperature is False
    assert profile.reasoning_effort == "none"
    request = LlmRequest(
        contents=[
            types.Content(role="user", parts=[types.Part.from_text(text="hi")]),
        ],
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=640,
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name="get_portfolio_item",
                            description="Get item",
                            parameters_json_schema={
                                "type": "object",
                                "properties": {"item_id": {"type": "string"}},
                            },
                        )
                    ]
                )
            ],
        ),
    )
    kwargs = build_openai_kwargs(
        model_id=profile.model_id,
        profile=profile,
        llm_request=request,
    )
    assert kwargs["max_completion_tokens"] == 640
    assert "max_tokens" not in kwargs
    # Luna rejects non-default temperature — omit the param entirely.
    assert "temperature" not in kwargs
    assert kwargs["reasoning_effort"] == "none"
    assert kwargs["tools"]


def test_build_openai_kwargs_max_tokens() -> None:
    profile = get_profile("openai:gpt-4.1-mini")
    request = LlmRequest(
        contents=[
            types.Content(role="user", parts=[types.Part.from_text(text="hi")]),
        ],
        config=types.GenerateContentConfig(max_output_tokens=320),
    )
    kwargs = build_openai_kwargs(
        model_id=profile.model_id,
        profile=profile,
        llm_request=request,
    )
    assert kwargs["max_tokens"] == 320
    assert "max_completion_tokens" not in kwargs


class _FakeLlm(BaseLlm):
    model: str = "fake"
    profile_key: str = "fake:model"
    fail: bool = False
    calls: int = 0

    @override
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.calls += 1
        if self.fail:
            err = Exception("boom")
            err.status_code = 500  # type: ignore[attr-defined]
            raise err
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=f"ok:{self.model}")],
            )
        )


def test_router_happy_path_single_call() -> None:
    primary = _FakeLlm(model="primary", profile_key="openai:primary", fail=False)
    backup = _FakeLlm(model="backup", profile_key="gemini:backup", fail=False)
    router = PortfolioLlmRouter(model="openai:primary", candidates=[primary, backup])

    async def _run() -> list[LlmResponse]:
        return [
            r
            async for r in router.generate_content_async(LlmRequest(contents=[]))
        ]

    chunks = asyncio.run(_run())
    assert len(chunks) == 1
    assert chunks[0].content.parts[0].text == "ok:primary"
    assert primary.calls == 1
    assert backup.calls == 0


def test_router_fallback_on_retryable() -> None:
    primary = _FakeLlm(model="primary", profile_key="openai:primary", fail=True)
    backup = _FakeLlm(model="backup", profile_key="gemini:backup", fail=False)
    router = PortfolioLlmRouter(model="openai:primary", candidates=[primary, backup])

    async def _run() -> list[LlmResponse]:
        return [
            r
            async for r in router.generate_content_async(LlmRequest(contents=[]))
        ]

    chunks = asyncio.run(_run())
    assert chunks[0].content.parts[0].text == "ok:backup"
    assert primary.calls == 1
    assert backup.calls == 1


def test_router_propagates_when_all_fail() -> None:
    primary = _FakeLlm(model="primary", profile_key="openai:primary", fail=True)
    backup = _FakeLlm(model="backup", profile_key="gemini:backup", fail=True)
    router = PortfolioLlmRouter(model="openai:primary", candidates=[primary, backup])

    async def _run() -> None:
        async for _ in router.generate_content_async(LlmRequest(contents=[])):
            pass

    with pytest.raises(Exception, match="boom"):
        asyncio.run(_run())


def test_is_retryable_status_codes() -> None:
    e400 = MagicMock()
    e400.status_code = 400
    assert is_retryable(e400)

    e500 = MagicMock()
    e500.status_code = 500
    assert is_retryable(e500)

    assert not is_retryable(ValueError("nope"))


def test_format_provider_error_includes_param_and_message() -> None:
    class BadRequestError(Exception):
        status_code = 400
        body = {
            "message": "Unsupported value: 'temperature' does not support 0.5",
            "type": "invalid_request_error",
            "param": "temperature",
            "code": "unsupported_value",
        }

    err = BadRequestError("boom")
    text = format_provider_error(err)
    assert "BadRequestError" in text
    assert "status=400" in text
    assert "param=temperature" in text
    assert "unsupported_value" in text
    assert "temperature" in text
