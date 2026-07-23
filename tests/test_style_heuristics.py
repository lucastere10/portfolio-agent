"""Style heuristics and reply tail guard (A5 + B2)."""

from __future__ import annotations

from src.evaluation.style_checks import (
    anti_pattern_hits,
    count_list_items,
    detect_response_lang,
    has_anti_pattern,
    verbosity_ok,
)
from src.orchestration.chat_handler import _ensure_complete_tail
from src.knowledge_base.context import build_overview_context
from src.tools.search import get_portfolio_overview_matches


def test_anti_pattern_flags_flattery():
    bad = [
        "Ótima pergunta! Eu trabalho com agentes.",
        "Great question — here is my stack.",
        "Claro, posso ajudar com pagamentos.",
        "Sure, I built payment systems.",
    ]
    for text in bad:
        assert has_anti_pattern(text), text
        assert anti_pattern_hits(text)


def test_anti_pattern_allows_direct_replies():
    good = [
        "Trabalho com agentes de IA em produção no GCP.",
        "I built a payment platform with Stripe webhooks and idempotency.",
        "Alguns destaques: **Drop** — clean data; **Quark** — simulation.",
    ]
    for text in good:
        assert not has_anti_pattern(text), text


def test_detect_lang_pt_and_en():
    assert detect_response_lang("Eu trabalho com projetos de agentes.") == "pt"
    assert detect_response_lang("I build payment systems and cloud agents.") == "en"


def test_verbosity_and_list_helpers():
    assert verbosity_ok("short", 600)
    assert not verbosity_ok("x" * 601, 600)
    text = "- a\n- b\n1. c\n"
    assert count_list_items(text) >= 3


def test_ensure_complete_tail_incomplete_preposition():
    assert _ensure_complete_tail("PassaNota é uma plataforma de") == (
        "PassaNota é uma plataforma de…"
    )
    assert _ensure_complete_tail("I build reliable systems.") == (
        "I build reliable systems."
    )


def test_overview_context_is_guidance_not_canned_reply():
    matches = get_portfolio_overview_matches(limit=4)
    ctx = build_overview_context(matches, "pt", matches[0].id if matches else None)
    assert "MODO OVERVIEW" in ctx or "OVERVIEW" in ctx
    assert "Alguns destaques:" not in ctx
