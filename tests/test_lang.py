"""B0 sticky language + default pt."""

from __future__ import annotations

from src.orchestration.chat_handler import (
    _detect_language,
    _strip_flattery_opening,
    resolve_lang,
)


def test_detect_tie_defaults_to_pt():
    assert _detect_language("xyz abc") == "pt"
    assert _detect_language("knowlage hubb") == "pt"


def test_resolve_lang_sticky_on_weak_signal():
    assert resolve_lang("knowlage hubb", "pt") == "pt"
    assert resolve_lang("knowlage hubb", "en") == "en"
    assert resolve_lang("drop", None) == "pt"
    assert resolve_lang("perdao, o drop", "pt") == "pt"


def test_resolve_lang_strong_overrides_session():
    assert resolve_lang("Tell me about your AI agents work", "pt") == "en"
    assert resolve_lang("Me fala dos seus projetos", "en") == "pt"


def test_strip_flattery_opening():
    assert _strip_flattery_opening("Claro. Eu trabalho com agentes.") == (
        "Eu trabalho com agentes."
    )
    assert _strip_flattery_opening("Sure, I build payment systems.") == (
        "I build payment systems."
    )
    assert _strip_flattery_opening("Trabalho com agentes.") == "Trabalho com agentes."
