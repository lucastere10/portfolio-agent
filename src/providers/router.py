"""LLM router: preferred adapter first; fallback only on exception."""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from pydantic import PrivateAttr
from typing_extensions import override

logger = logging.getLogger(__name__)


def _error_status(exc: BaseException) -> int | None:
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    return status if isinstance(status, int) else None


def _error_payload(exc: BaseException) -> dict[str, Any] | None:
    """Best-effort extract of provider error dict (OpenAI body / genai details)."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        # OpenAI SDK: body may be the inner error object or {"error": {...}}
        if "error" in body and isinstance(body["error"], dict):
            return body["error"]
        return body
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        err = details.get("error")
        if isinstance(err, dict):
            return err
        return details
    return None


def format_provider_error(exc: BaseException) -> str:
    """Human-readable one-liner for logs (type, status, param, message)."""
    status = _error_status(exc)
    payload = _error_payload(exc) or {}
    message = (
        payload.get("message")
        or getattr(exc, "message", None)
        or str(exc)
    )
    # Avoid dumping huge traces into the one-liner.
    if isinstance(message, str) and len(message) > 400:
        message = message[:400] + "…"

    parts = [type(exc).__name__]
    if status is not None:
        parts.append(f"status={status}")
    code = payload.get("code")
    if code:
        parts.append(f"code={code}")
    param = payload.get("param")
    if param:
        parts.append(f"param={param}")
    parts.append(f"message={message!r}")
    return " | ".join(parts)


def is_retryable(exc: BaseException) -> bool:
    """
    Whether the router should try the next candidate.

    Retries on transport/rate-limit/server errors and client 400s (e.g. bad
    parameter mapping). Auth without a key is skipped before the call; if a
    key is present but another vendor is available, still try the next.
    """
    status = _error_status(exc)

    if status in (401, 403):
        # Still allow cross-provider fallback (different vendor credentials).
        return True
    if status == 400:
        return True
    if status in (408, 429) or (isinstance(status, int) and status >= 500):
        return True

    name = type(exc).__name__
    if name in (
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "APIStatusError",
        "BadRequestError",
        "ClientError",
        "ServerError",
        "TimeoutError",
        "ConnectError",
    ):
        return True

    return False


class PortfolioLlmRouter(BaseLlm):
    """
    Single BaseLlm for LlmAgent — tries candidates in order inside one ADK turn.

    Happy path: one HTTP call. Fallback never recreates Runner/session.
    """

    model: str = "openai:gpt-5.6-luna"
    _candidates: list[BaseLlm] = PrivateAttr(default_factory=list)

    def __init__(self, *, model: str, candidates: list[BaseLlm], **kwargs):
        super().__init__(model=model, **kwargs)
        if not candidates:
            raise ValueError("PortfolioLlmRouter requires at least one candidate")
        object.__setattr__(self, "_candidates", list(candidates))

    @property
    def candidates(self) -> list[BaseLlm]:
        return self._candidates

    @override
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        last_exc: BaseException | None = None
        total = len(self._candidates)

        for index, llm in enumerate(self._candidates):
            label = getattr(llm, "profile_key", None) or getattr(llm, "model", type(llm).__name__)
            try:
                async for response in llm.generate_content_async(llm_request, stream=stream):
                    yield response
                if index > 0:
                    logger.info(
                        "LLM fallback succeeded with candidate %s "
                        "(after %d failed attempt(s))",
                        label,
                        index,
                    )
                return
            except Exception as exc:
                last_exc = exc
                is_last = index == total - 1
                retryable = is_retryable(exc)
                detail = format_provider_error(exc)
                next_label = None
                if not is_last:
                    nxt = self._candidates[index + 1]
                    next_label = getattr(nxt, "profile_key", None) or getattr(
                        nxt, "model", type(nxt).__name__
                    )

                if is_last or not retryable:
                    logger.error(
                        "LLM candidate %s failed and will not fall back "
                        "(retryable=%s, last=%s, remaining=%d): %s",
                        label,
                        retryable,
                        is_last,
                        total - index - 1,
                        detail,
                        exc_info=True,
                    )
                    raise

                logger.warning(
                    "LLM candidate %s failed; falling back to %s "
                    "(%d of %d remaining). Detail: %s",
                    label,
                    next_label,
                    total - index - 1,
                    total,
                    detail,
                )

        assert last_exc is not None
        raise last_exc
