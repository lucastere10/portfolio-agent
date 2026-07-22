# Orquestração do chat (A3)

Política do turno: **retrieve once** no handler; painel alinhado à intent; tools ADK só para detalhe pontual.

Código: [`src/orchestration/intent.py`](../src/orchestration/intent.py), [`hints.py`](../src/orchestration/hints.py), [`chat_handler.py`](../src/orchestration/chat_handler.py), [`src/adk/agent.py`](../src/adk/agent.py).

---

## Intent → matches → resposta

| Intent | Matches no painel | Contexto LLM | Resposta |
|--------|-------------------|--------------|----------|
| `intro` | `[]` | só profile | LLM |
| `boundary` | `[]` | só profile | LLM |
| `overview` | overview (até 5–6) | one-liners no contexto | LLM (`adk_agent`) — B2 removeu deterministic |
| `learning` | learning path | primary+1 | LLM |
| `follow_up` | search (com contexto de sessão) | primary+1 | LLM |
| `domain` / `other` | search | primary+1 | LLM |

Classificação: `classify_intent()` — ordem boundary → overview → learning → follow_up → intro → domain → other.

---

## Tools ADK

| Tool | No agent? | Quando |
|------|-----------|--------|
| `get_portfolio_item` | sim | Usuário pede mais detalhe de um id não coberto no PRIMARY/Related |
| `search_portfolio` | **não** | Handler já busca |
| `build_learning_path` | **não** | Handler já monta path na intent `learning` |

Rotas HTTP de search (se existirem) permanecem para uso interno/API — fora do `LlmAgent.tools`.

---

## Happy path

1. Sanitize + detect lang + `classify_intent`
2. Fetch matches **só** conforme intent (intro/boundary = vazio)
3. Montar `matches_context` (vazio se sem matches)
4. Overview → reply curta sem LLM; demais → ADK com contexto injetado
5. Painel = mesma lista `matches` (retrieve once)

---

## Fora de escopo (outras fases)

- Ranking / cold-start primary → **A4** (done)
- Suite pytest offline + CI → **A5** (done) — `uv run pytest`; baseline LLM continua local
- Sticky lang / overview PT / fuzzy nomes → **B0** (done)
- Recommend + persona + rich markdown chat → **B1** (done)
