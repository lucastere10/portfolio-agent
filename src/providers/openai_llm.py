"""OpenAI BaseLlm adapter with per-model token-limit parameter mapping."""

from __future__ import annotations

import copy
import json
import logging
from functools import cached_property
from typing import Any, AsyncGenerator, Literal

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from pydantic import PrivateAttr
from typing_extensions import override

from src.providers.contract import ModelProfile
from src.providers.registry import GENERATION

logger = logging.getLogger(__name__)


def _to_openai_role(
    role: str | None,
) -> Literal["system", "user", "assistant", "tool"]:
    if role in ("model", "assistant"):
        return "assistant"
    if role == "system":
        return "system"
    if role == "tool":
        return "tool"
    return "user"


def _part_to_openai_content(part: types.Part) -> str | dict[str, Any]:
    if part.thought and part.text:
        return f"Thought: {part.text}"
    if part.text:
        return part.text

    if part.inline_data:
        import base64

        mime_type = part.inline_data.mime_type
        data = part.inline_data.data
        if isinstance(data, bytes):
            encoded = base64.b64encode(data).decode("utf-8")
        else:
            encoded = str(data)
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
        }

    if part.file_data and part.file_data.file_uri and part.file_data.file_uri.startswith(
        "http"
    ):
        return {
            "type": "image_url",
            "image_url": {"url": part.file_data.file_uri},
        }

    return ""


def _content_to_openai_messages(content: types.Content) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    role = _to_openai_role(content.role)
    tool_calls: list[dict[str, Any]] = []
    content_parts: list[str | dict[str, Any]] = []

    for part in content.parts or []:
        if part.function_call:
            tool_calls.append(
                {
                    "id": part.function_call.id or "",
                    "type": "function",
                    "function": {
                        "name": part.function_call.name,
                        "arguments": (
                            json.dumps(part.function_call.args)
                            if part.function_call.args
                            else "{}"
                        ),
                    },
                }
            )
        elif part.function_response:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": part.function_response.id or "",
                    "content": (
                        json.dumps(part.function_response.response)
                        if part.function_response.response is not None
                        else ""
                    ),
                }
            )
        else:
            content_parts.append(_part_to_openai_content(part))

    processed_parts: list[dict[str, Any]] = []
    for c in content_parts:
        if isinstance(c, str) and c:
            processed_parts.append({"type": "text", "text": c})
        elif isinstance(c, dict):
            processed_parts.append(c)

    has_images = any(p.get("type") == "image_url" for p in processed_parts)
    if not has_images:
        content_val: Any = "\n".join(
            p["text"] for p in processed_parts if p["type"] == "text"
        )
    else:
        content_val = processed_parts

    if role == "assistant" and (content_val or tool_calls):
        msg: dict[str, Any] = {"role": "assistant"}
        if content_val:
            msg["content"] = content_val
        if tool_calls:
            msg["tool_calls"] = tool_calls
        messages.append(msg)
    elif role == "user" and content_val:
        messages.append({"role": "user", "content": content_val})
    elif role == "system" and content_val:
        if isinstance(content_val, list):
            text_only = "\n".join(
                p["text"] for p in content_val if p["type"] == "text"
            )
            messages.append({"role": "system", "content": text_only})
        else:
            messages.append({"role": "system", "content": content_val})

    return messages


def _update_type_string(value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            _update_type_string(item)
        return
    if not isinstance(value, dict):
        return
    schema_type = value.get("type")
    if isinstance(schema_type, str):
        value["type"] = schema_type.lower()
    for dict_key in (
        "$defs",
        "defs",
        "dependentSchemas",
        "patternProperties",
        "properties",
    ):
        child_dict = value.get(dict_key)
        if isinstance(child_dict, dict):
            for child_value in child_dict.values():
                _update_type_string(child_value)
    for single_key in (
        "additionalProperties",
        "additional_properties",
        "contains",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedProperties",
    ):
        child_value = value.get(single_key)
        if isinstance(child_value, (dict, list)):
            _update_type_string(child_value)
    for list_key in (
        "allOf",
        "all_of",
        "anyOf",
        "any_of",
        "oneOf",
        "one_of",
        "prefixItems",
    ):
        child_list = value.get(list_key)
        if isinstance(child_list, list):
            _update_type_string(child_list)


def _function_declaration_to_openai_tool(
    function_declaration: types.FunctionDeclaration,
) -> dict[str, Any]:
    if not function_declaration.name:
        raise ValueError("FunctionDeclaration must have a name.")

    if function_declaration.parameters_json_schema:
        parameters = copy.deepcopy(function_declaration.parameters_json_schema)
        _update_type_string(parameters)
    else:
        properties: dict[str, Any] = {}
        required_params: list[str] = []
        if function_declaration.parameters:
            if function_declaration.parameters.properties:
                for key, value in function_declaration.parameters.properties.items():
                    properties[key] = value.model_dump(by_alias=True, exclude_none=True)
            if function_declaration.parameters.required:
                required_params = list(function_declaration.parameters.required)
        parameters = {"type": "object", "properties": properties}
        if required_params:
            parameters["required"] = required_params
        _update_type_string(parameters)

    return {
        "type": "function",
        "function": {
            "name": function_declaration.name,
            "description": function_declaration.description or "",
            "parameters": parameters,
        },
    }


def _response_to_llm_response(response: ChatCompletion) -> LlmResponse:
    choice = response.choices[0]
    message = choice.message
    parts: list[types.Part] = []
    if message.content:
        parts.append(types.Part.from_text(text=message.content))

    if message.tool_calls:
        for tool_call in message.tool_calls:
            args: dict[str, Any] = {}
            if tool_call.function.arguments:
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse tool call arguments as JSON.")
            part = types.Part.from_function_call(
                name=tool_call.function.name, args=args
            )
            part.function_call.id = tool_call.id
            parts.append(part)

    usage = response.usage
    return LlmResponse(
        content=types.Content(role="model", parts=parts),
        usage_metadata=(
            types.GenerateContentResponseUsageMetadata(
                prompt_token_count=usage.prompt_tokens,
                candidates_token_count=usage.completion_tokens,
                total_token_count=usage.total_tokens,
            )
            if usage
            else None
        ),
    )


def build_openai_kwargs(
    *,
    model_id: str,
    profile: ModelProfile,
    llm_request: LlmRequest,
    default_max_tokens: int = GENERATION.max_output_tokens,
) -> dict[str, Any]:
    """Build Chat Completions kwargs with profile-aware token limit param."""
    messages: list[dict[str, Any]] = []
    if llm_request.config and llm_request.config.system_instruction:
        system = llm_request.config.system_instruction
        if not isinstance(system, str):
            # ADK may pass Content / list-like; OpenAI expects a string.
            system = str(system)
        messages.append({"role": "system", "content": system})

    for content in llm_request.contents or []:
        messages.extend(_content_to_openai_messages(content))

    tools: list[dict[str, Any]] = []
    if (
        llm_request.config
        and llm_request.config.tools
        and llm_request.config.tools[0].function_declarations
    ):
        tools = [
            _function_declaration_to_openai_tool(tool)
            for tool in llm_request.config.tools[0].function_declarations
        ]

    max_tokens = default_max_tokens
    if llm_request.config and llm_request.config.max_output_tokens is not None:
        max_tokens = llm_request.config.max_output_tokens

    kwargs: dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "tools": tools if tools else None,
        "tool_choice": "auto" if tools else None,
    }

    token_param = profile.token_limit_param
    if token_param == "max_completion_tokens":
        kwargs["max_completion_tokens"] = max_tokens
    elif token_param == "max_tokens":
        kwargs["max_tokens"] = max_tokens
    else:
        # Gemini-style name should not appear for OpenAI profiles.
        kwargs["max_completion_tokens"] = max_tokens

    if llm_request.config:
        if (
            profile.supports_temperature
            and getattr(llm_request.config, "temperature", None) is not None
        ):
            kwargs["temperature"] = llm_request.config.temperature
        if getattr(llm_request.config, "top_p", None) is not None:
            kwargs["top_p"] = llm_request.config.top_p
        if getattr(llm_request.config, "stop_sequences", None):
            kwargs["stop"] = llm_request.config.stop_sequences

    if profile.reasoning_effort is not None:
        kwargs["reasoning_effort"] = profile.reasoning_effort

    return kwargs


class OpenAIPortfolioLlm(BaseLlm):
    """Portfolio OpenAI adapter — maps GenerationContract via ModelProfile."""

    model: str = "gpt-4.1-mini"
    profile_key: str = "openai:gpt-4.1-mini"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    token_limit_param: str = "max_tokens"
    supports_temperature: bool = True
    reasoning_effort: str | None = None

    _client: Any = PrivateAttr(default=None)

    @classmethod
    def from_profile(
        cls,
        profile: ModelProfile,
        *,
        api_key: str,
        base_url: str,
    ) -> OpenAIPortfolioLlm:
        return cls(
            model=profile.model_id,
            profile_key=profile.key,
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            token_limit_param=profile.token_limit_param,
            supports_temperature=profile.supports_temperature,
            reasoning_effort=profile.reasoning_effort,
        )

    @property
    def profile(self) -> ModelProfile:
        return ModelProfile(
            provider="openai",
            model_id=self.model,
            token_limit_param=self.token_limit_param,  # type: ignore[arg-type]
            supports_temperature=self.supports_temperature,
            reasoning_effort=self.reasoning_effort,  # type: ignore[arg-type]
        )

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key or None, base_url=self.base_url)
        return self._client

    @override
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if stream:
            raise NotImplementedError(
                "OpenAIPortfolioLlm streaming is not enabled; use non-stream path"
            )

        kwargs = build_openai_kwargs(
            model_id=self.model,
            profile=self.profile,
            llm_request=llm_request,
        )
        response = await self._get_client().chat.completions.create(**kwargs)
        yield _response_to_llm_response(response)
