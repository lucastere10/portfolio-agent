"""
Chat orchestration — bridge between FastAPI and the ADK agent.

Always runs recommendation search for structured panel data, then delegates
the conversational reply to the ADK agent with rich portfolio context.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from typing import Optional

from src.observability.logging import log_event, session_hash

from src.adk.runtime import run_agent_turn
from src.config import settings
from src.domain.models import ChatRequest, ChatResponse, ProjectMatch
from src.knowledge_base.context import build_matches_context, build_overview_context
from src.providers.factory import has_llm_credentials
from src.session.service import get_session_store
from src.tools.search import (
    _wants_personal_overview,
    generate_learning_path,
    get_portfolio_overview_matches,
    is_portfolio_browse_query,
    search_projects,
)

logger = logging.getLogger(__name__)

_MAX_INPUT_LEN = 500
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_PT_MARKERS = {
    "quero", "ver", "gostaria", "mostrar", "para", "com", "sobre",
    "projeto", "projetos", "experiência", "experiencia", "trabalho",
    "tecnologia", "tecnologias", "aprender", "desenvolvimento",
    "mostre", "qual", "quais", "como", "fazer", "obrigado", "boa", "olá", "oi",
    "você", "voce", "estou", "sou", "tenho", "pode", "ajuda", "me", "fala",
    "conte", "explica", "agentes", "pagamento", "pagamentos",
}

_EN_MARKERS = {
    "show", "want", "project", "projects", "experience", "about",
    "technology", "technologies", "learn", "learning", "thanks",
    "hello", "hi", "specialties", "contact", "profile", "help",
    "looking", "tell", "what", "which", "how", "explain",
}

_LEARNING_HINTS = {
    "trilha", "trilhas", "learning", "aprender", "roadmap", "path",
    "jornada", "sequencia", "sequência", "passo a passo", "progressão",
    "progressao", "estudar", "como aprender",
}

_PROJECT_HINTS = ("projeto", "projetos", "project", "projects", "case", "work", "portfolio")
_LAB_HINTS = ("lab", "labs", "demo", "simulador", "simulator", "explore", "explorer")
_PERSONAL_HINTS = (
    "quark", "passanota", "drop", "pessoal", "personal", "open-source", "open source", "side project",
    "side-project", "artificial life", "vida artificial", "neuroevolution",
    "neuroevolução", "neuroevolucao", "simulation", "simulação", "simulacao",
    "genetic", "genética", "genetica", "evolution", "evolução", "evolucao",
    "pixijs", "emergent", "emergente", "nota fiscal", "receipt", "receipts",
    "expense", "expenses", "fintech", "cupom", "nf-e", "nota-fiscal",
    "dados", "spreadsheet", "csv", "analytics", "dashboard", "insights", "planilha",
    "newsletter", "knowledgehub", "rss", "curation", "curadoria", "personalization",
    "personalizado", "recommendation", "recomendação", "recomendacao",
)

_FOLLOW_UP_MARKERS = (
    "e sobre", "e o", "e a", "esse", "essa", "isso", "desse", "deste", "desta",
    "mais", "detalhe", "detalhes", "continua", "também", "tambem", "outro",
)

_SHORT_FOLLOW_WORDS = {
    "e", "sim", "não", "nao", "ok", "certo", "entendi", "isso", "esse", "essa",
}


def _sanitize(text: str) -> str:
    text = _CONTROL_CHARS_RE.sub("", text)
    return text[:_MAX_INPUT_LEN].strip()


def _detect_language(text: str) -> str:
    if any(c in text for c in "áéíóúàãõâêîôûç"):
        return "pt"
    tokens = set(re.findall(r"[a-záéíóúàãõâêîôûç]+", text.lower()))
    pt_hits = len(tokens & _PT_MARKERS)
    en_hits = len(tokens & _EN_MARKERS)
    return "pt" if pt_hits >= en_hits else "en"


def _wants_learning_path(query: str) -> bool:
    tokens = set(re.findall(r"[a-záéíóúàãõâêîôûç]+", query.lower()))
    return bool(tokens & _LEARNING_HINTS)


def _preferred_match_type(query: str) -> Optional[str]:
    lowered = query.lower()
    if any(h in lowered for h in _PERSONAL_HINTS):
        return "personal_project"
    if any(h in lowered for h in _LAB_HINTS):
        return "lab"
    if any(h in lowered for h in _PROJECT_HINTS):
        return "project"
    return None


def _select_primary_match(query: str, matches: list[ProjectMatch]) -> Optional[ProjectMatch]:
    if not matches:
        return None
    preferred = _preferred_match_type(query)
    if preferred:
        for match in matches:
            if match.type == preferred:
                return match
    return matches[0]


def _is_short_follow_up(query: str) -> bool:
    lowered = query.lower().strip()
    if any(marker in lowered for marker in _FOLLOW_UP_MARKERS):
        return True
    tokens = re.findall(r"[a-záéíóúàãõâêîôûç]+", lowered)
    return len(tokens) <= 3 and bool(set(tokens) & _SHORT_FOLLOW_WORDS)


async def _get_recent_user_topics(session_id: str) -> list[str]:
    """Pull recent user messages from ADK session for search contextualization."""
    store = get_session_store()
    adk = store.get_adk_service()
    session = await adk.get_session(
        app_name=settings.app_name,
        user_id=settings.default_user_id,
        session_id=session_id,
    )
    if not session:
        return []

    topics: list[str] = []
    for event in reversed(session.events):
        if not event.content or event.content.role != "user":
            continue
        text = "".join(
            p.text for p in (event.content.parts or []) if p.text
        ).strip()
        if text and len(text) > 8:
            topics.append(text)
        if len(topics) >= 2:
            break
    return topics


async def _contextualize_search_query(query: str, session_id: str) -> str:
    """Enrich short follow-ups with prior conversation topic for better search."""
    if not _is_short_follow_up(query):
        return query

    prior = await _get_recent_user_topics(session_id)
    if not prior:
        return query

    # Skip if the prior message is the same as current
    if prior[0].lower().strip() == query.lower().strip():
        return query

    return f"{query} (context: {prior[0]})"


async def _fetch_matches(query: str, limit: int, learning: bool) -> tuple[list[ProjectMatch], str]:
    if learning:
        results = await asyncio.to_thread(generate_learning_path, query, limit)
        return results, "generate_learning_path"
    if is_portfolio_browse_query(query):
        personal_only = _wants_personal_overview(query)
        results = await asyncio.to_thread(
            get_portfolio_overview_matches, limit, personal_only=personal_only
        )
        return results, "portfolio_overview"
    results = await asyncio.to_thread(search_projects, query, limit, "all")
    if not results and any(h in query.lower() for h in _PROJECT_HINTS):
        results = await asyncio.to_thread(
            get_portfolio_overview_matches, limit, personal_only=True
        )
        return results, "portfolio_overview_fallback"
    return results, "search_projects"


async def handle_chat(request: ChatRequest) -> ChatResponse:
    """Main chat handler invoked by the FastAPI route."""
    t_start = time.monotonic()
    session_store = get_session_store()

    raw_query = _sanitize(request.message)
    if not raw_query:
        lang = _detect_language(request.message or "")
        msg = "Por favor, envie uma mensagem válida." if lang == "pt" else "Please send a valid message."
        return ChatResponse(
            message=msg,
            session_id=request.session_id or str(uuid.uuid4()),
            selected_project=None,
            selected_type=None,
            matches=[],
            tool_used="validation",
        )

    lang = _detect_language(raw_query)
    session_id = await session_store.get_or_create(request.session_id)

    search_query = await _contextualize_search_query(raw_query, session_id)
    learning = _wants_learning_path(raw_query)
    limit = 6 if learning else 5
    matches, tool_used = await _fetch_matches(search_query, limit, learning)

    primary = _select_primary_match(search_query, matches)
    ordered = (
        [primary, *[m for m in matches if m.id != primary.id]]
        if primary
        else matches
    )
    primary_id = primary.id if primary else None
    if tool_used.startswith("portfolio_overview"):
        matches_context = build_overview_context(ordered, lang, primary_id)
    else:
        matches_context = build_matches_context(ordered, lang, primary_id)

    state_delta = {
        "response_lang": lang,
        "matches_context": matches_context,
    }

    if has_llm_credentials():
        try:
            response_text = await run_agent_turn(
                session_id=session_id,
                message=raw_query,
                state_delta=state_delta,
            )
            tool_used = "adk_agent"
        except Exception as exc:
            logger.exception("ADK agent failed for session %s: %s", session_id[:8], exc)
            log_event(
                "chat_error",
                session_id=session_hash(session_id),
                error_type=type(exc).__name__,
                lang=lang,
                query_preview=raw_query[:120],
            )
            response_text = _minimal_fallback(lang, primary)
            tool_used = "llm_error_fallback"
    else:
        response_text = _minimal_fallback(lang, primary)
        tool_used = "no_api_key"

    total_ms = int((time.monotonic() - t_start) * 1000)
    log_event(
        "chat_turn",
        session_id=session_hash(session_id),
        lang=lang,
        query_len=len(raw_query),
        query_preview=raw_query[:120],
        response_len=len(response_text),
        response_preview=response_text[:120],
        tool_used=tool_used,
        match_ids=[m.id for m in ordered[:3]],
        match_count=len(ordered),
        selected_project=primary_id,
        latency_ms=total_ms,
    )

    return ChatResponse(
        message=response_text,
        session_id=session_id,
        selected_project=primary.id if primary else None,
        selected_type=primary.type if primary else None,
        matches=ordered,
        tool_used=tool_used,
    )


def _minimal_fallback(lang: str, primary: ProjectMatch | None) -> str:
    """Last-resort fallback when the LLM is unavailable — short, not a template loop."""
    if lang == "pt":
        if primary:
            return (
                f"Estou com dificuldade para gerar uma resposta agora, mas o case mais "
                f"relevante para o que você perguntou é **{primary.title}** — "
                f"veja os detalhes no painel à direita."
            )
        return (
            "Estou com dificuldade para responder agora. "
            "Pode reformular sua pergunta ou tentar de novo em instantes?"
        )
    if primary:
        return (
            f"I'm having trouble generating a response right now, but the most relevant "
            f"case for your question is **{primary.title}** — see the details in the right panel."
        )
    return "I'm having trouble responding right now. Could you rephrase or try again in a moment?"
