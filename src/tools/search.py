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

    sim_signals = {
        "quark", "simulation", "simulação", "simulacao", "neuroevolution",
        "evolution", "evolução", "evolucao", "artificial", "life", "alife",
        "genetic", "genética", "genetica", "pixijs", "emergent", "emergente",
    }
    if query_tokens & sim_signals and (
        "Simulation" in entry.domain or "Artificial" in entry.domain
    ):
        bonus += 2.0

    fintech_signals = {
        "passanota", "receipt", "receipts", "invoice", "invoices", "fiscal",
        "nota", "nf-e", "expense", "expenses", "fintech", "cupom", "spend",
        "gasto", "gastos", "despesa", "despesas", "recibo",
    }
    if query_tokens & fintech_signals and (
        "FinTech" in entry.domain or "Expense" in entry.domain
    ):
        bonus += 2.0

    analytics_signals = {
        "drop", "analytics", "análise", "analise", "spreadsheet", "planilha",
        "csv", "excel", "xlsx", "dataset", "datasets", "dados", "dashboard",
        "charts", "insights", "pandas", "django", "eda", "data-quality",
        "visualization", "visualização", "visualizacao",
    }
    if query_tokens & analytics_signals and (
        "Analytics" in entry.domain or "Data Analytics" in entry.domain
    ):
        bonus += 2.0

    newsletter_signals = {
        "newsletter", "newsletters", "knowledgehub", "rss", "feed", "feeds",
        "recommendation", "recommendations", "personalization", "personalized",
        "curation", "curate", "curadoria", "articles", "article", "ranking",
        "intelligence", "inteligência", "inteligencia", "weekly", "resend",
    }
    if query_tokens & newsletter_signals and (
        "Intelligence" in entry.domain or "Technology Intelligence" in entry.domain
    ):
        bonus += 2.0

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


_BROWSE_PHRASES_PT = (
    "meus projetos",
    "seus projetos",
    "meu projeto",
    "seu projeto",
    "todos os projetos",
    "todos projetos",
    "quais projetos",
    "que projetos",
    "liste os projetos",
    "listar projetos",
    "listar os projetos",
    "fale sobre os projetos",
    "falar sobre os projetos",
    "falar sobre projetos",
    "fale sobre projetos",
    "conte sobre os projetos",
    "conte sobre projetos",
    "mostre os projetos",
    "mostrar os projetos",
    "mostre seus projetos",
    "seu portfolio",
    "seu portfólio",
    "meu portfolio",
    "meu portfólio",
)

_BROWSE_PHRASES_EN = (
    "my projects",
    "your projects",
    "my project",
    "your project",
    "all projects",
    "list projects",
    "list your projects",
    "tell me about your projects",
    "show me your projects",
    "show your projects",
    "your portfolio",
    "my portfolio",
    "what projects",
    "which projects",
)

_BROWSE_TOKENS = frozenset({"projeto", "projetos", "project", "projects", "portfolio", "cases"})

_PERSONAL_BROWSE_HINTS = (
    "meu",
    "meus",
    "minha",
    "minhas",
    "pessoal",
    "pessoais",
    "personal",
    "side project",
    "side-project",
    "open source",
    "open-source",
)

_OVERVIEW_PERSONAL_ORDER = ("drop", "quark", "passanota", "newsletter")

_DOMAIN_TOKENS = frozenset(
    kw for keywords in _DOMAIN_KEYWORDS.values() for kw in keywords
)


def is_portfolio_browse_query(query: str) -> bool:
    """Detect generic portfolio browse intents (not domain-specific searches)."""
    lowered = query.lower().strip()
    if any(phrase in lowered for phrase in _BROWSE_PHRASES_PT):
        return True
    if any(phrase in lowered for phrase in _BROWSE_PHRASES_EN):
        return True
    tokens = _tokenize(query)
    has_browse_token = bool(tokens & _BROWSE_TOKENS)
    has_domain_keyword = bool(tokens & _DOMAIN_TOKENS)
    return has_browse_token and not has_domain_keyword


def _wants_personal_overview(query: str) -> bool:
    lowered = query.lower()
    return any(hint in lowered for hint in _PERSONAL_BROWSE_HINTS)


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
        for pid in _OVERVIEW_PERSONAL_ORDER:
            if pid in by_id:
                ordered.append(by_id[pid])
    else:
        for pid in _OVERVIEW_PERSONAL_ORDER:
            if pid in by_id:
                ordered.append(by_id[pid])
        work = [e for e in catalog if e.type == "project" and e.id not in _OVERVIEW_PERSONAL_ORDER]
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
