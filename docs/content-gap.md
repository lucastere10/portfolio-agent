# Content Gap — Web vs Agent KB

Inventário slug-a-slug entre `portfolio/content/` e `portfolio-agent/src/knowledge_base/data/`.

**Atualizado em:** A1 concluída (generate a partir do content).

**Legenda de profundidade**

| Nível | Significado |
|-------|-------------|
| rico | context + challenges + learnings (+ decisions/tradeoffs/implementation quando aplicável) |
| médio | summary/tagline/techs bons; falta narrativa profunda |
| raso | quase só título/summary/tags; sem narrative |

---

## 1. Cobertura de IDs

**19/19** regeneráveis via `scripts/generate_kb.py`. Gap de profundidade editorial fechado no catálogo.

---

## 2. Work (`projects.json`)

| Slug | Na KB? | Profundidade | Campos A1 | Prioridade residual |
|------|--------|--------------|-----------|---------------------|
| `ai-agents-adk` | sim | rico | decisions/tradeoffs/implementation + cold start em challenges | — |
| `payment-integration-platform` | sim | rico | idem | — |
| `gpos-payment-system` | sim | rico | idem | — |
| `transactional-email-microservice` | sim | rico | idem | — |
| `computer-vision-analytics` | sim | rico | idem | — |
| `service-licensing-system` | sim | rico | idem | — |

---

## 3. Personal projects

| Slug | Na KB? | Profundidade | Notas |
|------|--------|--------------|-------|
| `quark` | sim | rico | overview→summary; technicalNotes→implementation; links ok |
| `passanota` | sim | rico | idem |
| `drop` | sim | rico | idem |
| `astra` | sim | rico | idem |

---

## 4. Labs

| Slug | Na KB? | Profundidade | Notas |
|------|--------|--------------|-------|
| todos os 9 | sim | médio+ | `narrative` (4) + demonstrates + tags do meta |

---

## 5. Profile / persona / skills

| Artefato | Estado pós-A1 | Residual |
|----------|---------------|----------|
| `profile.json` | about_en + specialties do about EN | about_pt opcional (A2) |
| `persona.json` | **não** regenerado (voz curada) | `*_pt` na A2 |
| `skills.json` | união das stacks do catálogo | — |

---

## 6. Critério “gap fechado”

- [x] Cada slug em `content/{work,projects,labs}` aparece na KB com mesmo `id`
- [x] Work entries incluem decisions/tradeoffs/implementation quando presentes no MDX
- [x] Labs incluem `narrative` quando presente no MDX
- [x] Campos factuais do catálogo vêm do content (related_projects preservados/fallback)
- [x] Este arquivo atualizado pós-A1
