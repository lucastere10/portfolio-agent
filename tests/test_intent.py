"""Intent classification offline (A5 + B0 + B1)."""

from __future__ import annotations

import pytest

from src.orchestration.intent import classify_intent
from src.tools.search import get_recommend_matches


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Oi, o que você faz?", "intro"),
        ("What kind of systems do you build?", "intro"),
        ("Você topa freela? Qual seu salário?", "boundary"),
        ("Me fala dos seus projetos", "overview"),
        ("Any personal projects I should see?", "recommend"),
        (
            "Gostaria de saber mais sobre seus projetos. Qual é o seu favorito?",
            "recommend",
        ),
        ("Me fale de um projeto seu interessante", "recommend"),
        ("Qual recomendação de projeto voce me daria?", "recommend"),
        ("Me fale de um projeto pessoal?", "recommend"),
        ("Recommend a personal project", "recommend"),
        ("Qual projeto te define melhor?", "domain"),
        ("Which project best represents your work?", "domain"),
        ("Quero uma trilha para aprender MLOps", "learning"),
        ("Walk me through a learning path for cloud architecture", "learning"),
        ("E sobre isso?", "follow_up"),
        ("Como você trabalha com agentes de IA?", "domain"),
        ("Tem algo com Stripe ou pagamentos?", "domain"),
        ("Como você resolveu cold start no Cloud Run?", "domain"),
        ("Tell me about your AI agents work", "domain"),
        ("How do you handle payment webhooks?", "domain"),
    ],
)
def test_classify_intent(query: str, expected: str):
    assert classify_intent(query) == expected


def test_recommend_matches_curated():
    matches = get_recommend_matches("um projeto interessante", limit=2)
    assert len(matches) == 2
    assert matches[0].id == "ai-agents-adk"


def test_recommend_personal_order():
    matches = get_recommend_matches("projeto pessoal", limit=2)
    assert matches[0].id == "quark"
    assert all(m.type == "personal_project" for m in matches)
