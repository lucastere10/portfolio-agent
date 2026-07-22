# AGENTS.md — Portfolio Agent

Instruções permanentes para agentes de código neste repositório.

## Fonte da verdade

Leia e siga **[`docs/agent-roadmap.md`](docs/agent-roadmap.md)** antes de alterar conhecimento, instruções, orquestração ou retrieval.

Este arquivo é o índice operacional. O roadmap tem o detalhe (diagnóstico, fases, checklists). Docs de apoio:

| Doc | Uso |
|-----|-----|
| [`docs/knowledge-contract.md`](docs/knowledge-contract.md) | Sync portfolio `content/` → KB |
| [`docs/content-gap.md`](docs/content-gap.md) | Inventário web vs KB |
| [`docs/conversation-quality.md`](docs/conversation-quality.md) | Estilo, anti-padrões, golden queries |
| [`docs/orchestration.md`](docs/orchestration.md) | Intent → matches → tools (A3) |

## Decisões travadas (não reabrir)

| Tema | Escolha |
|------|---------|
| Fonte editorial | `portfolio/content/**` (MDX + meta) |
| KB | Artefato derivado em `src/knowledge_base/data/` |
| Stack | FastAPI + Google ADK + catálogo in-memory |
| Embeddings / vector DB | Fora desta wave (D0–A5) |
| Locale canônico da KB (cases) | `en` + campos `*_pt` para voz/perfil |
| HTTP | BFF no portfolio → este serviço |
| Etapas | Uma por vez: D0 → A0 → … → A5 |

## Fluxo de trabalho por etapa

1. Trabalhe **uma etapa por vez** (D0 → A0 → … → A5).
2. Não misture sync de KB (A1) com rewrite de orquestração (A3) no mesmo PR amplo.
3. Ao concluir uma etapa: marque os checkboxes e o **Status** no roadmap.
4. Respeite a seção **Não fazer** da etapa atual.
5. Não faça commit a menos que o usuário peça explicitamente.

### Etapas (resumo)

| Etapa | Objetivo |
|-------|----------|
| **D0** | Docs + AGENTS + Cursor rules (done) |
| **A0** | Baseline conversacional (golden queries) (done) — ver `docs/baseline/` |
| **A1** | Sync KB ← `portfolio/content/` (done) — `scripts/generate_kb.py` |
| **A2** | Qualidade de resposta (done) — overview curto, persona PT, few-shots |
| **A3** | Orquestração (done) — intent, intro sem matches, tools slim — `docs/orchestration.md` |
| **A4** | Retrieval lexical + indexes reais (done) — phrases, experience bias, `check_retrieval.py` |
| **A5** | Testes de regressão + README honesto (done) — `uv run pytest`; CI offline |
| **B0** | Conversation polish (done) — sticky lang PT, overview titles, fuzzy names |
| **B1** | Conversation presence (done) — recommend intent, persona, chat markdown |
| **B2** | Agentic chat UX (done) — no deterministic overview; tokens 640; input focus |

## Regras Cursor

| Rule | Quando |
|------|--------|
| [`.cursor/rules/agent-architecture.mdc`](.cursor/rules/agent-architecture.mdc) | Sempre — princípios e decisões |
| [`.cursor/rules/stage-knowledge.mdc`](.cursor/rules/stage-knowledge.mdc) | KB, sync, knowledge-contract |
| [`.cursor/rules/stage-conversation.mdc`](.cursor/rules/stage-conversation.mdc) | Instruction, persona, qualidade de resposta |
| [`.cursor/rules/stage-orchestration.mdc`](.cursor/rules/stage-orchestration.mdc) | chat_handler, tools, retrieval wiring |

## Princípios rápidos

- **Conteúdo ≠ runtime:** editorial no portfolio; este repo serve conversa + KB derivada.
- **Retrieve once:** busca no handler alimenta painel e contexto; tools só para aprofundar.
- **Contexto magro:** 1 primary (+1 related); respostas ≤ 4 frases salvo pedido.
- **Sem conflito de prompt:** overview não manda listar o catálogo em essay.
- **Uma etapa por vez.**

## Fora de escopo (salvo pedido explícito)

- Embeddings / vector DB
- Redis / sessão multi-instância
- Redesign do chat no portfolio
- Alterar Cloud Build sem relação com a etapa atual

## Stack relevante

- Python ≥ 3.13, FastAPI, Google ADK, Pydantic Settings
- LLM: Gemini (default) ou OpenAI via factory
- Deploy: Cloud Run + `cloudbuild.yaml`
