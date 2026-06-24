"""Chat API route."""

from fastapi import APIRouter

from src.domain.models import ChatRequest, ChatResponse
from src.orchestration.chat_handler import handle_chat

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Conversational portfolio agent endpoint.

    Accepts a natural-language message and returns an assistant reply plus
    structured project/lab recommendations for the frontend right panel.
    """
    return await handle_chat(request)
