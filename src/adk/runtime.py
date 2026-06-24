"""ADK Runner lifecycle — initialized once at application startup."""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.runners import Runner
from google.genai import types

from src.adk.agent import create_portfolio_agent
from src.config import settings
from src.session.service import APP_NAME, get_session_store

logger = logging.getLogger(__name__)

_runner: Optional[Runner] = None


def init_runner() -> Runner:
    """Create the ADK Runner with in-memory session service."""
    global _runner
    if _runner is None:
        session_store = get_session_store()
        agent = create_portfolio_agent()
        _runner = Runner(
            app_name=APP_NAME,
            agent=agent,
            session_service=session_store.get_adk_service(),
            auto_create_session=True,
        )
        logger.info("ADK Runner initialized for agent '%s'", agent.name)
    return _runner


def get_runner() -> Runner:
    if _runner is None:
        return init_runner()
    return _runner


async def run_agent_turn(
    *,
    session_id: str,
    message: str,
    state_delta: dict,
) -> str:
    """
    Execute one conversational turn via the ADK Runner.

    Returns the final assistant text. Raises on ADK failure so callers
    can log and handle appropriately.
    """
    runner = get_runner()
    user_id = settings.default_user_id
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
        state_delta=state_delta,
    ):
        if not event.content:
            continue
        chunk = "".join(
            part.text for part in (event.content.parts or []) if part.text
        )
        if not chunk:
            continue
        # Keep the last final text response (after any tool calls complete).
        if event.is_final_response():
            response_text = chunk
        elif not response_text:
            response_text = chunk

    result = response_text.strip()
    if not result:
        raise RuntimeError("ADK agent returned an empty response")

    return result
