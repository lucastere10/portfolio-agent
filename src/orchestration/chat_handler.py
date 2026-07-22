"""
Chat orchestration — bridge between FastAPI and the ADK agent.

Retrieve once per intent; intro/boundary skip catalog matches; overview is deterministic.
B0: sticky language (default pt), overview titles-only in PT, fuzzy name resolve.
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
from src.knowledge_base.loader import get_by_id
from src.orchestration.hints import (
    LAB_HINTS,
    PERSONAL_TYPE_HINTS,
    PROJECT_HINTS,
    SIGNATURE_SEARCH_QUERY,
)
from src.orchestration.intent import (
    Intent,
    classify_intent,
    is_short_follow_up,
    is_signature_project_query,
)
from src.providers.factory import has_llm_credentials
from src.session.service import get_session_store
from src.tools.name_resolve import enrich_query_with_resolved_name, resolve_catalog_id
from src.tools.search import (
    _wants_personal_overview,
    generate_learning_path,
    get_portfolio_overview_matches,
    get_recommend_matches,
    search_projects,
)

logger = logging.getLogger(__name__)

_MAX_INPUT_LEN = 500
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_OPENING_STRIP_RE = re.compile(
    r"^(claro|sure|of course|certainly)[,!.]?\s+",
    re.IGNORECASE,
)

_PT_MARKERS = {
    "quero", "ver", "gostaria", "mostrar", "sobre",
    "projeto", "projetos", "experiência", "experiencia", "trabalho",
    "tecnologia", "tecnologias", "aprender", "desenvolvimento",
    "mostre", "qual", "quais", "fazer", "obrigado", "boa", "olá", "oi",
    "você", "voce", "estou", "sou", "tenho", "pode", "ajuda", "fala",
    "conte", "explica", "agentes", "pagamento", "pagamentos",
    "trilha", "portfólio", "salário", "salario", "perdao", "perdão",
    "desculpa", "fale", "mais",
}

_EN_MARKERS = {
    "show", "want", "project", "projects", "experience", "about",
    "technology", "technologies", "learn", "learning", "thanks",
    "hello", "hi", "specialties", "contact", "profile", "help",
    "looking", "tell", "what", "which", "how", "explain",
    "walk", "through", "path", "cloud", "architecture", "systems",
    "build", "built", "handle", "webhooks", "personal",
}


def _sanitize(text: str) -> str:
    text = _CONTROL_CHARS_RE.sub("", text)
    return text[:_MAX_INPUT_LEN].strip()


def _detect_language(text: str) -> str:
    """Turn-level language guess. Tie / empty → pt (portfolio default)."""
    if any(c in text for c in "áéíóúàãõâêîôûçÁÉÍÓÚÀÃÕ"):
        return "pt"
    tokens = set(re.findall(r"[a-záéíóúàãõâêîôûç]+", text.lower()))
    pt_hits = len(tokens & _PT_MARKERS)
    en_hits = len(tokens & _EN_MARKERS)
    if en_hits > pt_hits:
        return "en"
    if pt_hits > en_hits:
        return "pt"
    return "pt"


def _language_signal_strength(text: str) -> str:
    """Return 'strong' if turn has clear lang markers, else 'weak'."""
    if any(c in text for c in "áéíóúàãõâêîôûçÁÉÍÓÚÀÃÕ"):
        return "strong"
    tokens = re.findall(r"[a-záéíóúàãõâêîôûç]+", text.lower())
    token_set = set(tokens)
    pt_hits = len(token_set & _PT_MARKERS)
    en_hits = len(token_set & _EN_MARKERS)
    if pt_hits == 0 and en_hits == 0:
        return "weak"
    if len(tokens) <= 3 and (pt_hits + en_hits) <= 1:
        return "weak"
    if pt_hits == en_hits:
        return "weak"
    return "strong"


def resolve_lang(turn_text: str, session_lang: str | None) -> str:
    """Sticky language: weak turns keep session (default pt)."""
    turn_lang = _detect_language(turn_text)
    if _language_signal_strength(turn_text) == "strong":
        return turn_lang
    if session_lang in ("pt", "en"):
        return session_lang
    return "pt"


def _strip_flattery_opening(text: str) -> str:
    stripped = _OPENING_STRIP_RE.sub("", text, count=1)
    return stripped if stripped else text


_INCOMPLETE_TAIL_WORDS = frozenset(
    {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "um",
        "uma",
        "o",
        "a",
        "os",
        "as",
        "e",
        "com",
        "para",
        "por",
        "que",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "with",
        "is",
        "are",
    }
)


def _ensure_complete_tail(text: str) -> str:
    """If the model was cut mid-sentence, mark it instead of ending on a preposition."""
    stripped = text.rstrip()
    if not stripped:
        return text
    if stripped[-1] in ".!?…\"')":
        return stripped
    last = stripped.split()[-1].lower().strip(",;:")
    if last in _INCOMPLETE_TAIL_WORDS or len(last) <= 2:
        return stripped + "…"
    if not stripped[-1].isalnum():
        return stripped
    return stripped + "…"


def _preferred_match_type(query: str) -> Optional[str]:
    lowered = query.lower()
    if any(h in lowered for h in PERSONAL_TYPE_HINTS):
        return "personal_project"
    if any(h in lowered for h in LAB_HINTS):
        return "lab"
    if any(h in lowered for h in PROJECT_HINTS):
        return "project"
    return None


def _select_primary_match(query: str, matches: list[ProjectMatch]) -> Optional[ProjectMatch]:
    if not matches:
        return None
    # Fuzzy / alias exact id wins if present in matches
    resolved = resolve_catalog_id(query)
    if resolved:
        for match in matches:
            if match.id == resolved:
                return match
    preferred = _preferred_match_type(query)
    if preferred:
        for match in matches:
            if match.type == preferred:
                return match
    # Signature: prefer featured work project
    if is_signature_project_query(query):
        for match in matches:
            entry = get_by_id(match.id)
            if entry and entry.type == "project" and entry.featured:
                return match
        for match in matches:
            if match.type == "project":
                return match
    return matches[0]


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
        # Strip language anchor we append for the model
        text = re.sub(
            r"\n\n\((Responda somente em português\.|Reply in English only\.)\)\s*$",
            "",
            text,
        ).strip()
        if text and len(text) > 8:
            topics.append(text)
        if len(topics) >= 2:
            break
    return topics


async def _contextualize_search_query(query: str, session_id: str) -> str:
    """Enrich short follow-ups with prior conversation topic for better search."""
    if not is_short_follow_up(query):
        return query

    prior = await _get_recent_user_topics(session_id)
    if not prior:
        return query

    if prior[0].lower().strip() == query.lower().strip():
        return query

    return f"{query} (context: {prior[0]})"


async def _fetch_matches(
    query: str,
    limit: int,
    intent: Intent,
) -> tuple[list[ProjectMatch], str]:
    if intent in ("intro", "boundary"):
        return [], f"no_match_{intent}"
    if intent == "learning":
        results = await asyncio.to_thread(generate_learning_path, query, limit)
        return results, "generate_learning_path"
    if intent == "overview":
        personal_only = _wants_personal_overview(query)
        results = await asyncio.to_thread(
            get_portfolio_overview_matches, limit, personal_only=personal_only
        )
        return results, "portfolio_overview"
    if intent == "recommend":
        results = await asyncio.to_thread(get_recommend_matches, query, min(limit, 2))
        return results, "recommend_curated"
    results = await asyncio.to_thread(search_projects, query, limit, "all")
    if not results and any(h in query.lower() for h in PROJECT_HINTS):
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
        msg = (
            "Por favor, envie uma mensagem válida."
            if lang == "pt"
            else "Please send a valid message."
        )
        return ChatResponse(
            message=msg,
            session_id=request.session_id or str(uuid.uuid4()),
            selected_project=None,
            selected_type=None,
            matches=[],
            tool_used="validation",
        )

    session_id = await session_store.get_or_create(request.session_id)
    session_lang = session_store.get_response_lang(session_id)
    lang = resolve_lang(raw_query, session_lang)
    session_store.set_response_lang(session_id, lang)

    intent = classify_intent(raw_query)

    search_query = await _contextualize_search_query(raw_query, session_id)
    if is_signature_project_query(raw_query):
        search_query = SIGNATURE_SEARCH_QUERY
        intent = "domain"
    else:
        search_query = enrich_query_with_resolved_name(search_query)

    # Re-classify after contextualization for follow-ups that became domain searches
    if intent == "follow_up" and search_query != raw_query:
        intent = classify_intent(search_query)
        if intent in ("intro", "boundary", "overview"):
            intent = "domain"

    limit = 6 if intent == "learning" else (2 if intent == "recommend" else 5)
    matches, tool_used = await _fetch_matches(search_query, limit, intent)

    # If fuzzy resolved an id but search missed, force it as primary match
    resolved_id = resolve_catalog_id(raw_query)
    if resolved_id and not any(m.id == resolved_id for m in matches):
        entry = get_by_id(resolved_id)
        if entry:
            forced = ProjectMatch(
                id=entry.id,
                type=entry.type,
                title=entry.title,
                score=99.0,
                slug=entry.slug,
            )
            matches = [forced, *matches][:limit]
            tool_used = "name_resolve"

    primary = _select_primary_match(raw_query, matches)
    ordered = (
        [primary, *[m for m in matches if m.id != primary.id]]
        if primary
        else matches
    )
    primary_id = primary.id if primary else None

    if intent in ("intro", "boundary") or not ordered:
        matches_context = ""
    elif intent == "overview" or tool_used.startswith("portfolio_overview"):
        matches_context = build_overview_context(ordered, lang, primary_id)
    else:
        matches_context = build_matches_context(ordered, lang, primary_id)

    state_delta = {
        "response_lang": lang,
        "matches_context": matches_context,
        "intent": intent,
    }

    if has_llm_credentials():
        try:
            agent_message = _language_anchored_message(raw_query, lang)
            response_text = await run_agent_turn(
                session_id=session_id,
                message=agent_message,
                state_delta=state_delta,
            )
            response_text = _strip_flattery_opening(response_text)
            response_text = _ensure_complete_tail(response_text)
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
        intent=intent,
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


def _language_anchored_message(query: str, lang: str) -> str:
    """Append a short language cue — Gemini often ignores buried system banners."""
    if lang == "pt":
        return f"{query}\n\n(Responda somente em português.)"
    return f"{query}\n\n(Reply in English only.)"


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
    return (
        "I'm having trouble responding right now. "
        "Could you rephrase or try again in a moment?"
    )
