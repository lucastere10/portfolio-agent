"""Offline style / language heuristics shared by baseline and pytest (A5)."""

from __future__ import annotations

import re

ANTI_PATTERN_RE = re.compile(
    r"ótima pergunta|otima pergunta|great question|que interessante|"
    r"^(claro|sure|of course|certainly)[,!]?\s|"
    r"that's interesting|excelente pergunta",
    re.IGNORECASE | re.MULTILINE,
)

PT_MARKERS = {
    "você",
    "voce",
    "projeto",
    "projetos",
    "trabalho",
    "olá",
    "oi",
    "sou",
    "faço",
    "faco",
}
EN_MARKERS = {
    "you",
    "project",
    "projects",
    "work",
    "hello",
    "i",
    "build",
    "built",
    "systems",
}


def has_anti_pattern(text: str) -> bool:
    return bool(ANTI_PATTERN_RE.search(text))


def anti_pattern_hits(text: str) -> list[str]:
    return ANTI_PATTERN_RE.findall(text)


def count_list_items(text: str) -> int:
    bullets = len(re.findall(r"(?m)^\s*[-*•]\s+", text))
    numbered = len(re.findall(r"(?m)^\s*\d+[.)]\s+", text))
    return bullets + numbered


def detect_response_lang(text: str) -> str:
    if any(c in text for c in "áéíóúàãõâêîôûçÁÉÍÓÚÀÃÕ"):
        return "pt"
    tokens = set(re.findall(r"[a-záéíóúàãõâêîôûç]+", text.lower()))
    pt_hits = len(tokens & PT_MARKERS)
    en_hits = len(tokens & EN_MARKERS)
    if pt_hits == 0 and en_hits == 0:
        return "unknown"
    return "pt" if pt_hits >= en_hits else "en"


def verbosity_ok(text: str, threshold: int) -> bool:
    return len(text) <= threshold
