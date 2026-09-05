"""Gemini BaseLlm adapter aligned to GenerationContract / ModelProfile."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from pydantic import PrivateAttr
from typing_extensions import override

from src.providers.contract import ModelProfile

logger = logging.getLogger(__name__)


class GeminiPortfolioLlm(BaseLlm):
    """
    Thin portfolio wrapper around ADK Gemini.

    Keeps a uniform adapter surface with OpenAIPortfolioLlm so the router
    only depends on BaseLlm. Generation knobs come from llm_request.config
    (sourced from GenerationContract on the LlmAgent).
    """

    model: str = "gemini-3.5-flash"
    profile_key: str = "gemini:gemini-3.5-flash"

    _delegate: Gemini | None = PrivateAttr(default=None)

    @classmethod
    def from_profile(cls, profile: ModelProfile) -> GeminiPortfolioLlm:
        return cls(model=profile.model_id, profile_key=profile.key)

    def _get_delegate(self) -> Gemini:
        if self._delegate is None:
            self._delegate = Gemini(model=self.model)
        return self._delegate

    @override
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if stream:
            raise NotImplementedError(
                "GeminiPortfolioLlm streaming is not enabled; use non-stream path"
            )

        # Ensure request model matches this candidate (ADK may leave preferred id).
        llm_request = llm_request.model_copy(update={"model": self.model})
        async for response in self._get_delegate().generate_content_async(
            llm_request, stream=False
        ):
            yield response
