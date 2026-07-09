"""Structured logging helpers for GCP Cloud Logging / BigQuery export."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def session_hash(session_id: str) -> str:
    """Return a truncated SHA-256 hash of the session ID for log correlation."""
    return hashlib.sha256(session_id.encode()).hexdigest()[:16]


def log_event(event: str, **fields: Any) -> None:
    """Emit a structured JSON log line parsed by Cloud Run into jsonPayload."""
    payload: dict[str, Any] = {
        "severity": "INFO",
        "message": "portfolio_event",
        "event": event,
        "service": "portfolio-agent",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    logger.info(json.dumps(payload, ensure_ascii=False))
