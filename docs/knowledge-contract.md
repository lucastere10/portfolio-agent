# Knowledge Contract — Portfolio → Agent KB

Contrato de sincronização entre o conteúdo editorial do **portfolio** e a base de conhecimento do **portfolio-agent**.

**Fonte canônica deste contrato:** este arquivo.  
**Roadmap:** [`agent-roadmap.md`](agent-roadmap.md) fase **A1**.  
**Gap:** [`content-gap.md`](content-gap.md).  
**Baseline A0:** [`baseline/issues.md`](baseline/issues.md) (tags `kb-shallow`).

**Revisão:** pós-A0 — mapeamento alinhado aos schemas Zod do portfolio (`src/content/schemas.ts`); escopo A1 estreito (catálogo + profile factual; persona/voz fica para A2).

---

## 1. Princípio

| Papel | Onde |
|-------|------|
| Fonte editorial | `portfolio/content/**` (`meta.json` + `pt-BR.mdx` + `en.mdx`) |
| Artefato do agent | `portfolio-agent/src/knowledge_base/data/*.json` |
| Schema runtime | `portfolio-agent/src/domain/models.py` (`KBEntry` + extensões) |

Após **A1**, não editar JSONs de catálogo (`projects`, `personal_projects`, `labs`) “na mão”. Regenerar via script.

Schemas de referência no portfolio (não duplicar Zod em Python — espelhar campos):

- Work: `workMetaSchema` + `workLocaleSchema`
- Personal: `personalProjectMetaSchema` + `personalProjectLocaleSchema`
- Labs: `labMetaSchema` + `labLocaleSchema`
- About: `aboutPageSchema`

---

## 2. Locale

| Decisão | Detalhe |
|---------|---------|
| Canônico no catálogo | **en** — `en.mdx` alimenta campos textuais do `KBEntry` |
| Validação | Sync **exige** `en.mdx` + `pt-BR.mdx` + `meta.json` por slug; falha se faltar |
| Profile | Gera `about_en` a partir de about EN; opcionalmente `about_pt` a partir de PT (sem apagar links) |
| Persona / voz | **Fora do generate-kb na A1** — curadoria humana; A2 completa `*_pt` |

Runtime do chat continua respondendo no idioma do usuário; fatos do catálogo vêm do entry EN.

---

## 3. Mapeamento de entidades

### 3.1 Work → `projects.json` (`type: "project"`)

Fonte: `content/work/<slug>/`.

| Origem | Destino KB |
|--------|------------|
| `meta.slug` | `id` |
| `meta.domain` | `domain`; também entra em `categories` (lista com domain) |
| `meta.stack` | `technologies` |
| `meta.featured` | `featured` (default `false`) |
| `meta.order` | só ordenação no generate (não precisa no `KBEntry`) |
| `en.name` | `title` |
| `en.tagline` | `tagline` |
| `en.impact` | `summary` |
| `en.context` | `context` |
| `en.challenges` | `challenges` |
| `en.learnings` | `learnings` |
| `en.metrics` | `metrics` |
| `en.decisions` | `decisions` |
| `en.tradeoffs` | `tradeoffs` |
| `en.implementation` | `implementation` |
| — | `slug`: `/work/<id>` |
| — | `difficulty`: preservar do JSON atual se existir; senão `"intermediate"` |
| — | `tags`: ver §5 |
| — | `related_projects`: ver §5 |
| — | `demonstrates`: derivar de `decisions[].title` + keywords de `technologies` (cap 6) **ou** preservar lista atual se generate não melhorar |

### 3.2 Personal projects → `personal_projects.json` (`type: "personal_project"`)

Fonte: `content/projects/<slug>/`.  
Frontmatter **não** usa `impact`/`context`/`challenges` — usa `overview`, `highlights`, `features`, `technicalNotes`.

| Origem | Destino KB |
|--------|------------|
| `meta.slug` | `id` |
| `meta.domain` | `domain` |
| `meta.stack` | `technologies` |
| `meta.featured` | `featured` |
| `meta.links.demo` | `demo_url` |
| `meta.links.github` | `github_url` |
| `meta.links.repo` | `repo_url` |
| `en.name` | `title` |
| `en.tagline` | `tagline` |
| `en.overview` | `summary` **e** `context` (mesmo texto; summary pode truncar a 1ª frase se overview > 400 chars — preferir summary=overview completo se < 600) |
| `en.highlights` | prefixo de `challenges` **ou** campo auxiliar: mapear para `challenges` (highlights como “pontos fortes / foco”) — **decisão A1:** `challenges` ← `highlights`; `learnings` ← `en.learnings` |
| `en.features` | entra em `demonstrates` (cap 8) |
| `en.technicalNotes` | `implementation` |
| `en.metrics` | `metrics` |
| — | `slug`: `/projects/<id>` |
| — | `narrative`: `[]` |
| — | `decisions`: `[]` |
| — | `tradeoffs`: `""` |
| — | `tags` / `related_projects`: §5 |

Não truncar overview/highlights/metrics que o MDX já tem.

### 3.3 Labs → `labs.json` (`type: "lab"`)

Fonte: `content/labs/<slug>/`.

| Origem | Destino KB |
|--------|------------|
| `meta.slug` | `id` |
| `meta.domain` | `domain` |
| `meta.tags` | `tags` |
| `meta.order` | ordenação no generate |
| `meta.demoKey` | **não** persistir na KB v1 (só no site) |
| `en.title` | `title` |
| `en.summary` | `summary` |
| `en.interactionPrompt` | `interaction_prompt` |
| `en.narrative` | `narrative` (tuple de 4 strings no site → `list[str]` len 4) |
| `en.demonstrates` | `demonstrates` |
| — | `slug`: `/labs/<id>` |
| — | `context`: `""` |
| — | `challenges` / `learnings`: `[]` |
| — | `technologies`: derivar de tags capitalizadas **ou** lista curta por domínio (ver generate); se vazio, usar tags |
| — | `featured`: `false` |
| — | `related_projects`: §5 |

### 3.4 Profile (A1) vs persona (A2)

| Artefato | A1 | A2 |
|----------|----|----|
| `profile.json` | Atualizar `name`, `about_en`, `specialties` (de `focusAreas[].title`), manter `links` / `availability` se já existirem | `about_pt` se útil |
| `persona.json` | **não** sobrescrever voice/boundaries/hooks | Completar `*_pt` (focus, highlights, boundaries) |
| `skills.json` | União ordenada de todas as `stack`/`technologies` do catálogo gerado (dedupe) | — |

---

## 4. Extensões de schema (`KBEntry`)

```text
decisions: list[{ title: str, reasoning: str }]  # default []
tradeoffs: str                                     # default ""
implementation: str                                # default ""
narrative: list[str]                               # default []
```

`format_entry_details` (A1 mínimo): incluir até 2 `decisions`, `tradeoffs` (1 linha), `implementation` (1–2 frases), `narrative` (labs, até 4 linhas). Refino de prompt/overview fica na **A2**.

Pydantic: `model_config` extra ignore se necessário; defaults vazios para não quebrar JSON antigo durante a transição.

---

## 5. Tags e `related_projects`

| Campo | Regra A1 |
|-------|----------|
| `tags` (work) | slugify de `technologies` + tokens do `domain` + `id`; lowercase; dedupe; sort |
| `tags` (personal) | idem + palavras do `id` |
| `tags` (labs) | `meta.tags` do site (já existem) |
| `related_projects` | **Preservar** o mapa do JSON atual por `id` se o target ainda existir pós-generate; senão, top 3 por overlap de tags/domain (excluir self) |
| `categories` | `[domain]` + eventualmente segundo label estável já usado hoje |

Não inventar related para IDs que não existem no catálogo gerado.

---

## 6. Script `generate_kb.py`

| Item | Escolha |
|------|---------|
| Path | `portfolio-agent/scripts/generate_kb.py` |
| Content dir | `PORTFOLIO_CONTENT_DIR` ou default `../portfolio/content` (sibling) |
| Parser | frontmatter YAML via `python-frontmatter` **ou** PyYAML + split `---`; **não** compilar body MDX |
| Output | `src/knowledge_base/data/{projects,personal_projects,labs}.json` + `profile.json` (factual) + `skills.json` |
| Sort | entries por `id`; keys JSON estáveis (`sort_keys` / ordem de campos fixa no dump) |
| Validate | carregar com `KBEntry`; assert set(ids) == set(slugs do content) por tipo |
| CLI | `python scripts/generate_kb.py` · `--check` só valida drift (exit 1 se diff) sem escrever |

Deps: adicionar `python-frontmatter` ou usar stdlib+PyYAML se já houver; preferir dependência mínima documentada no `pyproject.toml`.

### Critério ligado à A0 (case 7)

Após generate, `ai-agents-adk.challenges` (ou `implementation`) deve continuar/conter menção a cold start / Cloud Run vinda do MDX — o sync preserva o fato; o ranking lexical (A4) usa phrase match para primary correto.

---

## 7. Escopo A1 vs fora

**Inclui**

- Schema + generate catálogo (19 slugs) + profile/skills
- Wire compacto dos novos campos em `format_entry_details`
- Docs: atualizar `content-gap.md`; README how-to sync
- `--check` local (content em `portfolio/`; não é gate do CI deste repo — A5 usa pytest offline)

**Não inclui**

- Rewrite instruction / overview brevity (A2)
- Persona PT / few-shots (A2)
- Mudança de ranking/search além de indexar novos campos no scorer lexical **leve** (opcional A1: somar `implementation`/`narrative`/`tradeoffs` no `_score_entry` com peso baixo — recomendado para cold-start tokens)
- Embeddings, Redis, Cloud Build IAM

---

## 8. Regras para agentes de código

1. Ler este contrato + fase A1 do roadmap antes de tocar na KB.
2. Mudança editorial → portfolio `content/` → `generate_kb.py`.
3. Não adicionar entry só no JSON do agent.
4. Não inventar métricas/techs; só MDX/meta.
5. Após generate, smoke: `load_catalog()` size == 19; re-rodar subset baseline cases 5–7 se agent up (não bloqueante).

---

## 9. Fora de escopo permanente deste contrato

- Body MDX além do frontmatter
- Embeddings / CMS / banco
- Traduzir paths `/work`, `/projects`, `/labs`
