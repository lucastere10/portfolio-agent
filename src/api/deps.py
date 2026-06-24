"""Shared FastAPI dependencies."""

from fastapi import HTTPException, Request


async def require_agent_ready(request: Request) -> None:
    startup_error = getattr(request.app.state, "agent_startup_error", None)
    if startup_error:
        raise HTTPException(status_code=503, detail="Agent startup failed")

    if not getattr(request.app.state, "agent_ready", False):
        raise HTTPException(status_code=503, detail="Agent is starting")
