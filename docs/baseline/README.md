# Baseline conversacional (A0)

Smoke reproduzível das golden queries contra o agent local — **sem** alterar instruction, KB ou retrieval.

Política de estilo: [`../conversation-quality.md`](../conversation-quality.md).  
Roadmap: [`../agent-roadmap.md`](../agent-roadmap.md) fase **A0**.

---

## Pré-requisitos

1. Python 3.13+ com deps do projeto (`uv pip install -e .` ou equivalente)
2. `.env` com `PORTFOLIO_AGENT_GEMINI_API_KEY` (ou provider ativo)
3. Agent rodando em `http://127.0.0.1:8000`

```bash
cd portfolio-agent
python main.py
# em outro terminal:
curl -s http://127.0.0.1:8000/health
# status=ok e llm_configured=true
```

---

## Rodar

```bash
python scripts/run_baseline.py
```

Variáveis:

| Env | Default | Descrição |
|-----|---------|-----------|
| `BASELINE_BASE_URL` | `http://127.0.0.1:8000` | Base do agent |
| `BASELINE_CASES` | `docs/baseline/golden-cases.json` | Cases |

Saídas:

- [`results/latest.md`](results/latest.md) — relatório humano
- [`results/latest.json`](results/latest.json) — raw + scores

Exit code ≠ 0 se health falhar. Mismatches de primary **não** falham o processo (baseline descreve; gate na A5).

---

## Rubrica

### Automático (script)

| Campo | Passa se |
|-------|----------|
| `primary_ok` | `selected_project == expected_primary` (quando expected ≠ null) |
| `verbosity_ok` | `response_len` ≤ threshold (600 chars) |
| `anti_pattern_ok` | Sem regex de bajulação / intro vazia listada |
| `lang_ok` | Heurística alinhada a `lang` do case |

### Humano (preencher em `issues.md` / colunas do MD)

| Campo | Significado |
|-------|-------------|
| `style_ok` | ≤4 frases; concreto; sem listagem forçada |
| `invented` | Inventou projeto/métrica/stack? |
| `notes` | Observação livre |

Famílias e critérios: seção 6 de `conversation-quality.md`.

---

## Sessão `pay`

Cases #4 e #9 compartilham `session_group: "pay"`. O runner envia #4, guarda `session_id`, e reutiliza em #9 (`E sobre isso?`).

---

## Após a run

1. Revisar `results/latest.md`
2. Atualizar [`issues.md`](issues.md) com tags `style` / `retrieval` / `kb-shallow` / `orchestration`
3. Marcar A0 no roadmap quando baseline + issues estiverem commitáveis
