# Baseline issues

## Pós-B2

- Overview determinístico removido (sempre LLM)
- “seus projetos + favorito” → recommend
- Truncation: tokens 640 + ellipsis em cauda incompleta
- Chat input refoca após enviar / ao fim do loading

---

## Pós-B1

- Recommend / “um projeto” / “projeto pessoal” → LLM (não template “Alguns destaques”)
- Browse só listagem explícita (“me fala dos seus projetos”)
- Chat UI: markdown links/listas; contact deve usar `[label](url)`
- Gaps: tagline_pt, github/demo nos work cases

---

## Pós-B0

- Sticky lang (default PT); overview PT sem taglines EN
- Fuzzy KnowledgeHub / PassaNota; signature → `ai-agents-adk`
- `max_output_tokens=400`; strip Claro/Sure
- Suite: `uv run pytest` (46+)

---

## Pós-A5

- Suite offline no CI: `uv run pytest` (KB, retrieval, intent, style)
- Baseline LLM permanece local (`run_baseline.py`) — não é gate do Actions
- Truncation / verbosity residual — mitigado em parte na B0 (`400` tokens)

---

## Pós-A4

- Primary **8/8** (case **7** cold-start → `ai-agents-adk`)
- Smoke lexical: `python scripts/check_retrieval.py`
- Case **14** ainda pode marcar verbosity (threshold) — polish opcional
- Truncation por `max_output_tokens=256` (A2) — fora de A4

Ver scoring em `src/tools/search.py`.

---

## Pós-A3

- Case **11** (`What kind of systems…`): `selected_project=null`, `match_ids=[]` — intro sem painel ruidoso
- Case **9** follow-up payments: primary OK
- Cases **2/13** overview determinístico OK
- Case **7** cold-start primary → corrigido na **A4**
- Algumas respostas curtas/truncadas por `max_output_tokens=256` (A2) — polish opcional depois

Ver [`orchestration.md`](../orchestration.md).

---

## Pós-A2 (UTC from `results/latest.md`)

**Resumo automático (A2):** primary 7/8 · verbosity fails **0** · anti-pattern **0** · lang fails **0**

| Case | Status pós-A2 | Notas |
|------|---------------|-------|
| 2, 13 | OK | Overview determinístico |
| 11 | painel ruidoso | Corrigido na **A3** (matches vazios) |
| 7 | FAIL primary | Corrigido na **A4** |

---

## Histórico A0 (2026-07-22T03:06:41)

Primary 7/8 · verbosity 3 · anti-pattern regex 0 · lang 1 — ver git history / notas abaixo.

P0 era overview essay (2, 13), cold-start (7), idioma (15). A2 fechou estilo/idioma; A4 fechou retrieval.
