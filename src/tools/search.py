"""
Portfolio recommendation engine — weighted Jaccard scoring over pre-loaded catalog.

All catalog data is read from memory; no file I/O per request.
"""

from __future__ import annotations

import re
from typing import Optional

from src.domain.models import KBEntry, ProjectMatch
from src.knowledge_base.indexes import get_indexes
from src.knowledge_base.loader import get_all, get_by_id
from src.orchestration.hints import (
    BROWSE_PHRASES_EN,
    BROWSE_PHRASES_PT,
    OVERVIEW_PERSONAL_ORDER,
    PERSONAL_BROWSE_HINTS,
    RECOMMEND_CURATED_ORDER,
    RECOMMEND_PERSONAL_ORDER,
)

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
    "Artificial Life & Simulation": [
        "simulation", "simulação", "simulacao", "simulator", "simulador",
        "neuroevolution", "neuroevolução", "neuroevolucao", "genetic",
        "genética", "genetica", "algorithm", "algoritmo", "evolution",
        "evolução", "evolucao", "artificial", "life", "vida", "quark",
        "pixijs", "pixi", "emergent", "emergente", "creature", "criatura",
        "neural", "network", "rede", "neural", "alife", "ecosystem",
        "ecossistema", "predation", "predação", "predacao",
    ],
    "FinTech / Expense Management": [
        "passanota", "receipt", "receipts", "invoice", "invoices", "fiscal",
        "nota", "notas", "nf-e", "nfe", "expense", "expenses", "fintech",
        "supabase", "pgvector", "cupom", "cupons", "gasto", "gastos",
        "cost", "costs", "spend", "spending", "brazil", "brazilian",
        "controle", "despesa", "despesas", "nota-fiscal", "recibo",
    ],
    "Data Analytics / AI": [
        "drop", "analytics", "análise", "analise", "spreadsheet", "planilha",
        "csv", "excel", "xlsx", "json", "dataset", "datasets", "dados", "data",
        "dashboard", "dashboards", "chart", "charts", "gráfico", "grafico",
        "insights", "insight", "pandas", "django", "eda", "profiling",
        "data-quality", "quality", "qualidade", "ml-recommendation",
        "visualization", "visualização", "visualizacao", "spreadsheet",
    ],
    "Personalized AI & Technology Intelligence": [
        "newsletter", "newsletters", "knowledgehub", "knowledge", "hub",
        "rss", "feed", "feeds", "recommendation", "recommendations",
        "personalization", "personalized", "personalizado", "curation",
        "curate", "curadoria", "articles", "article", "artigos", "artigo",
        "intelligence", "inteligência", "inteligencia", "resend", "prisma",
        "enrichment", "embedding", "embeddings", "ranking", "weekly",
        "tech-intelligence", "content", "conteúdo", "conteudo",
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


_KNOWN_PHRASES = (
    "cold start",
    "cold-start",
    "cloud run",
    "dead letter",
    "dead-letter",
    "mcp toolbox",
    "vertex ai",
)

_EXPERIENCE_SIGNALS = (
    "resolvi",
    "resolveu",
    "resolvido",
    "como você",
    "como voce",
    "how did you",
    "how do you",
    "i solved",
    "i handled",
    "no meu case",
    "no meu projeto",
    "in my project",
    "in production",
    "em produção",
    "em producao",
)


def _field_as_text(value: str | list) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


def _query_phrases(query: str) -> list[str]:
    """Unigram bigrams from query + known ops phrases present in the query."""
    lowered = query.lower()
    tokens = [
        t
        for t in re.split(r"[^a-záéíóúàãõâêîôûç\d]+", lowered)
        if t and t not in _STOPWORDS
    ]
    phrases: list[str] = []
    for i in range(len(tokens) - 1):
        phrases.append(f"{tokens[i]} {tokens[i + 1]}")
    for known in _KNOWN_PHRASES:
        if known in lowered and known not in phrases:
            phrases.append(known)
    # normalize hyphen variants
    if "cold-start" in lowered and "cold start" not in phrases:
        phrases.append("cold start")
    return phrases


def _phrase_score(phrases: list[str], value: str | list, weight: float) -> float:
    if not phrases or not value:
        return 0.0
    text = _field_as_text(value).lower()
    if not text:
        return 0.0
    hits = sum(1 for p in phrases if p in text)
    if hits == 0:
        return 0.0
    return weight * min(hits, 3)


def _is_experience_query(query: str) -> bool:
    lowered = query.lower()
    return any(s in lowered for s in _EXPERIENCE_SIGNALS)


def _experience_type_bonus(query: str, entry: KBEntry) -> float:
    if not _is_experience_query(query):
        return 0.0
    if entry.type == "project":
        return 1.5
    if entry.type == "lab":
        return -0.5
    return 0.0


def _tag_index_bonus(query_tokens: set[str], entry: KBEntry) -> float:
    indexes = get_indexes()
    hits = 0
    for token in query_tokens:
        tagged = indexes.by_tag.get(token)
        if not tagged:
            continue
        if any(e.id == entry.id for e in tagged):
            hits += 1
        if hits >= 2:
            break
    return 0.35 * hits


def _intent_bonus(query: str, query_tokens: set[str], entry: KBEntry) -> float:
    """Boost entries when query intent clearly matches a domain (e.g. AI agents + GCP)."""
    lowered = query.lower()
    bonus = 0.0

    ai_signals = {"agente", "agentes", "agent", "agents", "ia", "ai", "llm", "adk", "mcp"}
    if query_tokens & ai_signals and "AI" in entry.domain:
        bonus += 1.5
    if query_tokens & {
        "pagamento",
        "pagamentos",
        "payment",
        "payments",
        "stripe",
        "pix",
        "fintech",
    }:
        if "Payment" in entry.domain:
            bonus += 1.5
    if query_tokens & {"mlops", "pipeline", "airflow", "drift"}:
        if "MLOps" in entry.domain or "Data" in entry.domain:
            bonus += 1.2

    sim_signals = {
        "quark",
        "simulation",
        "simulação",
        "simulacao",
        "neuroevolution",
        "evolution",
        "evolução",
        "evolucao",
        "artificial",
        "life",
        "alife",
        "genetic",
        "genética",
        "genetica",
        "pixijs",
        "emergent",
        "emergente",
    }
    if query_tokens & sim_signals and (
        "Simulation" in entry.domain or "Artificial" in entry.domain
    ):
        bonus += 2.0

    fintech_signals = {
        "passanota",
        "receipt",
        "receipts",
        "invoice",
        "invoices",
        "fiscal",
        "nota",
        "nf-e",
        "expense",
        "expenses",
        "fintech",
        "cupom",
        "spend",
        "gasto",
        "gastos",
        "despesa",
        "despesas",
        "recibo",
    }
    if query_tokens & fintech_signals and (
        "FinTech" in entry.domain or "Expense" in entry.domain
    ):
        bonus += 2.0

    analytics_signals = {
        "drop",
        "analytics",
        "análise",
        "analise",
        "spreadsheet",
        "planilha",
        "csv",
        "excel",
        "xlsx",
        "dataset",
        "datasets",
        "dados",
        "dashboard",
        "charts",
        "insights",
        "pandas",
        "django",
        "eda",
        "data-quality",
        "visualization",
        "visualização",
        "visualizacao",
    }
    if query_tokens & analytics_signals and (
        "Analytics" in entry.domain or "Data Analytics" in entry.domain
    ):
        bonus += 2.0

    newsletter_signals = {
        "newsletter",
        "newsletters",
        "knowledgehub",
        "rss",
        "feed",
        "feeds",
        "recommendation",
        "recommendations",
        "personalization",
        "personalized",
        "curation",
        "curate",
        "curadoria",
        "articles",
        "article",
        "ranking",
        "intelligence",
        "inteligência",
        "inteligencia",
        "weekly",
        "resend",
    }
    if query_tokens & newsletter_signals and (
        "Intelligence" in entry.domain or "Technology Intelligence" in entry.domain
    ):
        bonus += 2.0

    ai_phrases = (
        "agentes de ia",
        "agentes ia",
        "ai agents",
        "ai agent",
        "inteligência artificial",
    )
    if any(p in lowered for p in ai_phrases) and "AI" in entry.domain:
        bonus += 2.0

    # Ops phrase → production case
    if ("cold start" in lowered or "cold-start" in lowered) and entry.type == "project":
        blob = " ".join(
            [
                entry.summary,
                entry.context,
                _field_as_text(entry.challenges),
                entry.implementation,
            ]
        ).lower()
        if "cold start" in blob or "cold-start" in blob:
            bonus += 2.5

    bonus += _experience_type_bonus(query, entry)
    return bonus


def _score_entry(query: str, query_tokens: set[str], entry: KBEntry) -> float:
    if not query_tokens and not _query_phrases(query):
        return 0.0

    phrases = _query_phrases(query)
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
    score += _field_score(query_tokens, entry.implementation, 1.2)
    score += _field_score(query_tokens, entry.tradeoffs, 1.0)
    score += _field_score(query_tokens, entry.narrative, 1.0)
    decision_text = [f"{d.title} {d.reasoning}" for d in entry.decisions]
    score += _field_score(query_tokens, decision_text, 1.1)

    # Phrase hits on rich fields (high weight — fixes cold start vs cloud labs)
    score += _phrase_score(phrases, entry.challenges, 3.5)
    score += _phrase_score(phrases, entry.implementation, 2.5)
    score += _phrase_score(phrases, entry.learnings, 2.0)
    score += _phrase_score(phrases, decision_text, 2.0)
    score += _phrase_score(phrases, entry.summary, 1.5)
    score += _phrase_score(phrases, entry.context, 1.5)
    score += _phrase_score(phrases, entry.technologies, 1.2)

    score += _domain_bonus(query_tokens, entry.domain)
    score += _intent_bonus(query, query_tokens, entry)
    score += _tag_index_bonus(query_tokens, entry)

    if entry.featured:
        score *= 1.05

    return round(score, 4)


def _prefer_work_over_lab(
    query: str,
    scored: list[tuple[KBEntry, float]],
) -> list[tuple[KBEntry, float]]:
    """If experience query and lab barely leads a work case, promote the work entry."""
    if len(scored) < 2 or not _is_experience_query(query):
        return scored
    top_entry, top_score = scored[0]
    if top_entry.type != "lab" or top_score <= 0:
        return scored
    for i, (entry, score) in enumerate(scored[1:], start=1):
        if entry.type == "project" and score >= top_score * 0.85:
            # Swap to front
            rest = [scored[0]] + scored[1:i] + scored[i + 1 :]
            return [(entry, score)] + rest
    return scored


def domain_keyword_tokens() -> frozenset[str]:
    """All domain keyword tokens for intent / browse gating."""
    return frozenset(kw for keywords in _DOMAIN_KEYWORDS.values() for kw in keywords)


def is_portfolio_browse_query(query: str) -> bool:
    """Explicit portfolio listing only (B1) — no bare 'projeto' token shortcut."""
    lowered = query.lower().strip()
    if any(phrase in lowered for phrase in BROWSE_PHRASES_PT):
        return True
    if any(phrase in lowered for phrase in BROWSE_PHRASES_EN):
        return True
    return False


def _wants_personal_overview(query: str) -> bool:
    lowered = query.lower()
    return any(hint in lowered for hint in PERSONAL_BROWSE_HINTS)


def get_recommend_matches(query: str, limit: int = 2) -> list[ProjectMatch]:
    """Curated 1–2 entries for recommend intent (LLM narrates; no overview template)."""
    catalog = get_all()
    by_id = {e.id: e for e in catalog}
    lowered = query.lower()
    personal = any(h in lowered for h in PERSONAL_BROWSE_HINTS)
    order = RECOMMEND_PERSONAL_ORDER if personal else RECOMMEND_CURATED_ORDER
    ordered: list[KBEntry] = []
    for pid in order:
        if pid in by_id:
            ordered.append(by_id[pid])
        if len(ordered) >= limit:
            break
    return [
        ProjectMatch(id=e.id, type=e.type, title=e.title, score=1.0, slug=e.slug)
        for e in ordered
    ]


def get_portfolio_overview_matches(
    limit: int = 6,
    *,
    personal_only: bool = False,
) -> list[ProjectMatch]:
    """Return catalog overview matches with uniform score for browse queries."""
    catalog = get_all()
    by_id = {e.id: e for e in catalog}
    ordered: list[KBEntry] = []

    if personal_only:
        for pid in OVERVIEW_PERSONAL_ORDER:
            if pid in by_id:
                ordered.append(by_id[pid])
    else:
        for pid in OVERVIEW_PERSONAL_ORDER:
            if pid in by_id:
                ordered.append(by_id[pid])
        work = [
            e
            for e in catalog
            if e.type == "project" and e.id not in OVERVIEW_PERSONAL_ORDER
        ]
        work.sort(key=lambda e: (not e.featured, e.title))
        ordered.extend(work)
        labs = [e for e in catalog if e.type == "lab"]
        labs.sort(key=lambda e: e.title)
        ordered.extend(labs)

    return [
        ProjectMatch(id=e.id, type=e.type, title=e.title, score=1.0, slug=e.slug)
        for e in ordered[:limit]
    ]


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
    elif filter_type == "personal_project":
        catalog = [e for e in catalog if e.type == "personal_project"]

    query_tokens = _tokenize(query)
    scored = [(entry, _score_entry(query, query_tokens, entry)) for entry in catalog]
    scored = [(e, s) for e, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    scored = _prefer_work_over_lab(query, scored)

    return [
        ProjectMatch(id=e.id, type=e.type, title=e.title, score=s, slug=e.slug)
        for e, s in scored[:limit]
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
    personal = [m for m in all_matches if m.type == "personal_project"]

    path: list[ProjectMatch] = []
    for lab, proj in zip(labs, projects):
        path.append(lab)
        path.append(proj)

    tail = min(len(labs), len(projects))
    path.extend(labs[tail:])
    path.extend(projects[tail:])
    path.extend(personal)

    return path[:limit]
