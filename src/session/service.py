"""
Session management abstraction.

The default implementation delegates to Google ADK's InMemorySessionService,
which stores conversation history in memory keyed by (app, user, session_id).

To migrate to Redis, implement BaseSessionService from google.adk.sessions
and swap the instance in init_session_service().
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from google.adk.sessions import InMemorySessionService
from google.adk.sessions.base_session_service import BaseSessionService

from src.config import settings

logger = logging.getLogger(__name__)

APP_NAME = settings.app_name


class SessionStore(ABC):
    """Application-level session facade (Redis-swappable)."""

    @abstractmethod
    async def get_or_create(self, session_id: Optional[str] = None) -> str:
        ...

    @abstractmethod
    def get_adk_service(self) -> BaseSessionService:
        ...

    @abstractmethod
    def get_response_lang(self, session_id: str) -> Optional[str]:
        ...

    @abstractmethod
    def set_response_lang(self, session_id: str, lang: str) -> None:
        ...


class AdkInMemorySessionStore(SessionStore):
    """In-memory session store backed by ADK's session service."""

    def __init__(self, adk_service: InMemorySessionService) -> None:
        self._adk = adk_service
        self._user_id = settings.default_user_id
        self._response_lang: dict[str, str] = {}

    def get_adk_service(self) -> BaseSessionService:
        return self._adk

    def get_response_lang(self, session_id: str) -> Optional[str]:
        return self._response_lang.get(session_id)

    def set_response_lang(self, session_id: str, lang: str) -> None:
        if lang in ("pt", "en"):
            self._response_lang[session_id] = lang

    async def get_or_create(self, session_id: Optional[str] = None) -> str:
        sid = (session_id or "").strip() or str(uuid.uuid4())
        existing = await self._adk.get_session(
            app_name=APP_NAME,
            user_id=self._user_id,
            session_id=sid,
        )
        if existing is None:
            await self._adk.create_session(
                app_name=APP_NAME,
                user_id=self._user_id,
                session_id=sid,
            )
            logger.debug("Created ADK session %s", sid)
        return sid


_session_store: Optional[SessionStore] = None


def init_session_service() -> SessionStore:
    """Initialize the global session store (call once at startup)."""
    global _session_store
    if _session_store is None:
        adk_service = InMemorySessionService()
        _session_store = AdkInMemorySessionStore(adk_service)
        logger.info("Session store initialized (in-memory via ADK)")
    return _session_store


def get_session_store() -> SessionStore:
    if _session_store is None:
        return init_session_service()
    return _session_store
