"""
Portfolio recommendation engine — weighted Jaccard scoring over pre-loaded catalog.

All catalog data is read from memory; no file I/O per request.
"""

from __future__ import annotations

import re
from typing import Optional

from src.domain.models import KBEntry, ProjectMatch
from src.knowledge_base.loader import get_all, get_by_id

_STOPWORDS = {
    "a", "as", "o", "os", "e", "em", "de", "do", "da", "dos", "das",
    "um", "uma", "para", "por", "com", "que", "se", "na", "no", "nas",
    "nos", "ao", "aos", "quero", "ver", "gostaria", "me", "você", "eu",
    "como", "sobre", "mais", "muito", "bem", "favor", "mostrar", "mostre",
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with",
    "is", "are", "was", "were", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "i", "want", "show", "see", "like",
    "can", "you", "my", "what", "tell", "about",
}

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "AI Agents": [
        "ia", "ai", "agente", "agentes", "agent", "agents", "automação",
        "automacao", "llm", "gpt", "vertex", "adk", "inteligência",
        "inteligencia", "artificial", "machine", "learning", "ml", "nlp",
        "orquestração", "orquestracao", "orchestration", "generativo",
        "generative", "mcp",
    ],
    "Cloud Architecture": [
        "cloud", "nuvem", "gcp", "google", "run", "bigquery", "pubsub",
        "kubernetes", "k8s", "serverless", "escalabilidade", "scale",
        "infra", "infraestrutura", "arquitetura", "architecture",
    ],
    "Payment Systems": [
        "pagamento", "pagamentos", "payment", "payments", "stripe", "pix",
        "fintech", "assinatura", "checkout", "billing", "cobrar",
        "cobranca", "transação", "transacao", "financial", "financeiro",
        "cartão", "cartao", "card", "mtls",
    ],
    "Backend Engineering": [
        "backend", "api", "microsserviço", "microservice", "queue", "fila",
        "email", "rabbit", "rabbitmq", "servidor", "server", "rest", "http",
        "servico", "serviço", "fastapi", "dotnet", "csharp",
    ],
    "Computer Vision": [
        "visão", "visao", "vision", "câmera", "camera", "yolo", "opencv",
        "detecção", "deteccao", "computer", "imagem", "image", "video",
        "tracking", "rastreamento",
    ],
    "MLOps & Data Pipelines": [
        "mlops", "ml", "dag", "pipeline", "drift", "modelo", "model",
        "training", "treino", "deploy", "deployment", "monitoramento",
        "monitoring", "machine", "learning", "airflow", "bigquery",
    ],
    "CI/CD": [
        "ci", "cd", "deploy", "pipeline", "retry", "failure", "dlq",
        "sre", "observabilidade", "observability", "confiabilidade",
        "reliability", "resilience", "incident",
    ],
}


def _tokenize(text: str) -> set[str]:
    tokens = set(re.split(r"[^a-záéíóúàãõâêîôûç\d]+", text.lower()))
    return tokens - _STOPWORDS - {""}


def _field_score(query_tokens: set[str], value: str | list, weight: float) -> float:
    if not value:
        return 0.0
    text = " ".join(str(v) for v in value) if isinstance(value, list) else str(value)
    field_tokens = _tokenize(text)
    if not field_tokens:
        return 0.0
    overlap = len(query_tokens & field_tokens)
    if overlap == 0:
        return 0.0
    return weight * overlap / (len(query_tokens) + len(field_tokens) - overlap + 1)


def _domain_bonus(query_tokens: set[str], domain: str) -> float:
    keywords = _DOMAIN_KEYWORDS.get(domain, [])
    if not keywords:
        return 0.0
    hits = len(query_tokens & set(keywords))
    return 0.45 * (hits / len(keywords)) if hits else 0.0


def _intent_bonus(query: str, query_tokens: set[str], entry: KBEntry) -> float:
    """Boost entries when query intent clearly matches a domain (e.g. AI agents + GCP)."""
    lowered = query.lower()
    bonus = 0.0

    ai_signals = {"agente", "agentes", "agent", "agents", "ia", "ai", "llm", "adk", "mcp"}
    if query_tokens & ai_signals and "AI" in entry.domain:
        bonus += 1.5
    if query_tokens & {"pagamento", "pagamentos", "payment", "payments", "stripe", "pix", "fintech"}:
        if "Payment" in entry.domain:
            bonus += 1.5
    if query_tokens & {"mlops", "pipeline", "airflow", "drift"}:
        if "MLOps" in entry.domain or "Data" in entry.domain:
            bonus += 1.2

    ai_phrases = ("agentes de ia", "agentes ia", "ai agents", "ai agent", "inteligência artificial")
    if any(p in lowered for p in ai_phrases) and "AI" in entry.domain:
        bonus += 2.0

    return bonus


def _score_entry(query: str, query_tokens: set[str], entry: KBEntry) -> float:
    if not query_tokens:
        return 0.0

    score = 0.0
    score += _field_score(query_tokens, entry.title, 4.0)
    score += _field_score(query_tokens, entry.tagline, 3.0)
    score += _field_score(query_tokens, entry.summary, 2.5)
    score += _field_score(query_tokens, entry.domain, 2.0)
    score += _field_score(query_tokens, entry.technologies, 2.0)
    score += _field_score(query_tokens, entry.demonstrates, 2.0)
    score += _field_score(query_tokens, entry.tags, 2.0)
    score += _field_score(query_tokens, entry.categories, 1.8)
    score += _field_score(query_tokens, entry.context, 1.5)
    score += _field_score(query_tokens, entry.challenges, 1.0)
    score += _field_score(query_tokens, entry.learnings, 1.0)
    score += _domain_bonus(query_tokens, entry.domain)
    score += _intent_bonus(query, query_tokens, entry)

    if entry.featured:
        score *= 1.05

    return round(score, 4)


def search_projects(
    query: str,
    limit: int = 10,
    filter_type: str = "all",
) -> list[ProjectMatch]:
    """Search the in-memory catalog and return ranked matches."""
    if not query or not query.strip():
        return []

    catalog = get_all()
    if filter_type == "project":
        catalog = [e for e in catalog if e.type == "project"]
    elif filter_type == "lab":
        catalog = [e for e in catalog if e.type == "lab"]

    query_tokens = _tokenize(query)
    scored = [(entry, _score_entry(query, query_tokens, entry)) for entry in catalog]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        ProjectMatch(id=e.id, type=e.type, title=e.title, score=s, slug=e.slug)
        for e, s in scored[:limit]
        if s > 0
    ]


def get_project(project_id: str) -> Optional[KBEntry]:
    """Retrieve a catalog entry by ID."""
    return get_by_id(project_id)


def generate_learning_path(query: str, limit: int = 8) -> list[ProjectMatch]:
    """Build an interleaved lab → project learning path for a topic."""
    all_matches = search_projects(query, limit=20, filter_type="all")
    if not all_matches:
        return []

    labs = [m for m in all_matches if m.type == "lab"]
    projects = [m for m in all_matches if m.type == "project"]

    path: list[ProjectMatch] = []
    for lab, proj in zip(labs, projects):
        path.append(lab)
        path.append(proj)

    tail = min(len(labs), len(projects))
    path.extend(labs[tail:])
    path.extend(projects[tail:])

    return path[:limit]
