"""Shared intent / browse heuristics (A3) — single source for handler + search."""

from __future__ import annotations

BROWSE_PHRASES_PT = (
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
    "me fala dos seus projetos",
    "me fala dos meus projetos",
    "me fale dos seus projetos",
    "me fale dos meus projetos",
)

BROWSE_PHRASES_EN = (
    "all projects",
    "list projects",
    "list your projects",
    "tell me about your projects",
    "show me your projects",
    "show your projects",
    "your portfolio",
    "my portfolio",
    "what projects do you",
    "which projects do you",
    "any personal projects",
)

# Token shortcut removed in B1 — browse is phrase-only (see is_portfolio_browse_query)

PERSONAL_BROWSE_HINTS = (
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

# Vague "pick one / recommend" — LLM path, not deterministic overview
RECOMMEND_PHRASES = (
    "interessante",
    "interessantes",
    "recomend",
    "recomenda",
    "recomendação",
    "recomendacao",
    "sugira",
    "sugere",
    "sugestão",
    "sugestao",
    "me indica",
    "me indique",
    "um projeto",
    "algum projeto",
    "projeto pessoal",
    "projeto preferido",
    "favorito",
    "preferido",
    "interesting",
    "recommend",
    "recommendation",
    "suggest",
    "suggestion",
    "favorite",
    "favourite",
    "a project",
    "one project",
    "personal project",
    "cool project",
    "pick a project",
)

RECOMMEND_CURATED_ORDER = (
    "ai-agents-adk",
    "quark",
    "drop",
    "passanota",
    "newsletter",
)

RECOMMEND_PERSONAL_ORDER = ("quark", "drop", "passanota", "newsletter")

OVERVIEW_PERSONAL_ORDER = ("drop", "quark", "passanota", "newsletter")

LEARNING_HINTS = frozenset(
    {
        "trilha",
        "trilhas",
        "learning",
        "aprender",
        "roadmap",
        "path",
        "jornada",
        "sequencia",
        "sequência",
        "passo a passo",
        "progressão",
        "progressao",
        "estudar",
        "como aprender",
    }
)

PROJECT_HINTS = (
    "projeto",
    "projetos",
    "project",
    "projects",
    "case",
    "work",
    "portfolio",
)

LAB_HINTS = (
    "lab",
    "labs",
    "demo",
    "simulador",
    "simulator",
    "explore",
    "explorer",
)

PERSONAL_TYPE_HINTS = (
    "quark",
    "passanota",
    "drop",
    "pessoal",
    "personal",
    "open-source",
    "open source",
    "side project",
    "side-project",
    "artificial life",
    "vida artificial",
    "neuroevolution",
    "neuroevolução",
    "neuroevolucao",
    "simulation",
    "simulação",
    "simulacao",
    "genetic",
    "genética",
    "genetica",
    "evolution",
    "evolução",
    "evolucao",
    "pixijs",
    "emergent",
    "emergente",
    "nota fiscal",
    "receipt",
    "receipts",
    "expense",
    "expenses",
    "fintech",
    "cupom",
    "nf-e",
    "nota-fiscal",
    "dados",
    "spreadsheet",
    "csv",
    "analytics",
    "dashboard",
    "insights",
    "planilha",
    "newsletter",
    "knowledgehub",
    "rss",
    "curation",
    "curadoria",
    "personalization",
    "personalizado",
    "recommendation",
    "recomendação",
    "recomendacao",
)

FOLLOW_UP_MARKERS = (
    "e sobre",
    "e o",
    "e a",
    "esse",
    "essa",
    "isso",
    "desse",
    "deste",
    "desta",
    "mais",
    "detalhe",
    "detalhes",
    "continua",
    "também",
    "tambem",
    "outro",
)

SHORT_FOLLOW_WORDS = frozenset(
    {"e", "sim", "não", "nao", "ok", "certo", "entendi", "isso", "esse", "essa"}
)

BOUNDARY_HINTS = (
    "salário",
    "salario",
    "salary",
    "freela",
    "freelance",
    "disponibilidade",
    "availability",
    "quanto cobra",
    "how much do you charge",
)

INTRO_PHRASES = (
    "o que você faz",
    "o que voce faz",
    "quem é você",
    "quem e voce",
    "me fala de você",
    "me fala de voce",
    "what kind of systems",
    "what do you do",
    "who are you",
    "tell me about yourself",
    "what do you build",
)

INTRO_GREETINGS = frozenset(
    {"oi", "olá", "ola", "hello", "hi", "hey", "bom dia", "boa tarde", "boa noite"}
)

# "Which project defines you?" — domain, not browse overview
SIGNATURE_PROJECT_PHRASES = (
    "te define",
    "me define",
    "define melhor",
    "te define melhor",
    "projeto principal",
    "projeto que te define",
    "qual projeto te define",
    "flagship",
    "signature project",
    "best represents",
    "defines you",
    "define you",
)

# Enrichment when signature intent fires (featured work signal)
SIGNATURE_SEARCH_QUERY = "featured AI agents ADK production GCP"
