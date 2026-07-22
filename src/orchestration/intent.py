"""Explicit chat intent classification (A3 + B0 signature + B1 recommend)."""

from __future__ import annotations

import re
from typing import Literal

from src.orchestration.hints import (
    BOUNDARY_HINTS,
    FOLLOW_UP_MARKERS,
    INTRO_GREETINGS,
    INTRO_PHRASES,
    LEARNING_HINTS,
    RECOMMEND_PHRASES,
    SHORT_FOLLOW_WORDS,
    SIGNATURE_PROJECT_PHRASES,
)
from src.tools.search import is_portfolio_browse_query

Intent = Literal[
    "intro",
    "boundary",
    "overview",
    "recommend",
    "learning",
    "follow_up",
    "domain",
    "other",
]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-záéíóúàãõâêîôûç]+", text.lower()))


def wants_learning_path(query: str) -> bool:
    tokens = _tokenize(query)
    lowered = query.lower()
    if "passo a passo" in lowered or "como aprender" in lowered:
        return True
    return bool(tokens & LEARNING_HINTS)


def is_signature_project_query(query: str) -> bool:
    lowered = query.lower()
    return any(p in lowered for p in SIGNATURE_PROJECT_PHRASES)


def is_recommend_query(query: str) -> bool:
    lowered = query.lower()
    return any(p in lowered for p in RECOMMEND_PHRASES)


def is_short_follow_up(query: str) -> bool:
    lowered = query.lower().strip()
    # Phrase markers need word-ish boundaries (avoid "Stripe ou" matching "e o")
    for marker in FOLLOW_UP_MARKERS:
        if " " in marker:
            if re.search(rf"(?<!\w){re.escape(marker)}(?!\w)", lowered):
                return True
        elif marker in lowered.split():  # single-token markers as whole words
            return True
        elif len(marker) > 3 and marker in lowered:
            return True
    tokens = re.findall(r"[a-záéíóúàãõâêîôûç]+", lowered)
    return len(tokens) <= 3 and bool(set(tokens) & SHORT_FOLLOW_WORDS)


def is_boundary_query(query: str) -> bool:
    lowered = query.lower()
    return any(h in lowered for h in BOUNDARY_HINTS)


def _has_strong_domain_signal(query: str) -> bool:
    from src.tools.search import domain_keyword_tokens

    return bool(_tokenize(query) & domain_keyword_tokens())


def is_intro_query(query: str) -> bool:
    lowered = query.lower().strip()
    if any(p in lowered for p in INTRO_PHRASES):
        return True
    tokens = _tokenize(query)
    if not tokens:
        return False
    if tokens <= INTRO_GREETINGS:
        return True
    if len(tokens) <= 3 and bool(tokens & INTRO_GREETINGS) and not _has_strong_domain_signal(
        query
    ):
        return True
    return False


def classify_intent(query: str) -> Intent:
    """Classify user query. Order is significant."""
    if is_boundary_query(query):
        return "boundary"
    if is_signature_project_query(query):
        return "domain"
    # Opinion / pick-one before browse (e.g. "seus projetos… favorito?")
    if is_recommend_query(query):
        return "recommend"
    if is_portfolio_browse_query(query):
        return "overview"
    if wants_learning_path(query):
        return "learning"
    if is_short_follow_up(query):
        return "follow_up"
    if is_intro_query(query):
        return "intro"
    if _has_strong_domain_signal(query):
        return "domain"
    return "other"
