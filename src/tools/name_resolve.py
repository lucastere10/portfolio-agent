"""Resolve catalog entry ids from typos / aliases (B0) — lexical, no embeddings."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from src.knowledge_base.loader import get_all

# Canonical id → accepted spellings / nicknames (lowercase)
_ALIASES: dict[str, tuple[str, ...]] = {
    "newsletter": (
        "knowledgehub",
        "knowledge hub",
        "knowledge-hub",
        "knowlage",
        "knowlage hub",
        "knowlage hubb",
        "oknowlage",
        "oknowlage uhb",
        "khub",
    ),
    "passanota": (
        "passa nota",
        "passa-nota",
        "passanotta",
        "pasanota",
    ),
    "drop": ("drop analytics",),
    "quark": ("quark sim", "quark simulation"),
    "ai-agents-adk": (
        "adk",
        "ai agents",
        "agentes adk",
        "agentes de ia",
    ),
    "mcp-explorer": ("mcp", "mcp explorer", "mcp lab"),
    "payment-integration-platform": (
        "stripe",
        "payment platform",
        "plataforma de pagamento",
    ),
}

_FUZZY_THRESHOLD = 0.72


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-záéíóúàãõâêîôûç0-9\s\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def resolve_catalog_id(query: str) -> str | None:
    """Return a catalog entry id if the query looks like a (typo'd) name."""
    normalized = _normalize(query)
    if not normalized or len(normalized) < 3:
        return None

    for entry_id, aliases in _ALIASES.items():
        for alias in aliases:
            if alias == normalized or alias in normalized or normalized in alias:
                return entry_id

    catalog = get_all()
    best_id: str | None = None
    best_ratio = 0.0
    for entry in catalog:
        candidates = {
            _normalize(entry.id.replace("-", " ")),
            _normalize(entry.id),
            _normalize(entry.title),
            _normalize(entry.slug.split("/")[-1] if entry.slug else ""),
        }
        for cand in candidates:
            if not cand:
                continue
            ratio = SequenceMatcher(None, normalized, cand).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_id = entry.id
            # also compare compact forms (no spaces)
            compact_q = normalized.replace(" ", "").replace("-", "")
            compact_c = cand.replace(" ", "").replace("-", "")
            if compact_q and compact_c:
                r2 = SequenceMatcher(None, compact_q, compact_c).ratio()
                if r2 > best_ratio:
                    best_ratio = r2
                    best_id = entry.id

    if best_id and best_ratio >= _FUZZY_THRESHOLD:
        return best_id
    return None


def enrich_query_with_resolved_name(query: str) -> str:
    """If query resolves to a catalog id, append it to strengthen lexical search."""
    resolved = resolve_catalog_id(query)
    if not resolved:
        return query
    if resolved.replace("-", " ") in query.lower() or resolved in query.lower():
        return query
    return f"{query} {resolved}"
