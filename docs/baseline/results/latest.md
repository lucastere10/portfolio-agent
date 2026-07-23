# Baseline results (A0)

- Generated (UTC): `2026-07-22T03:41:43.313405+00:00`
- Base URL: `http://127.0.0.1:8000`
- Provider: `gemini`
- Verbosity threshold: `600` chars

## Summary

- Primary ok: **8/8**
- Verbosity fails: **1**
- Anti-pattern fails: **0**
- Lang fails: **0**
- Request errors: **0**

## Cases

| ID | Family | Primary OK | Selected | Expected | Len | Verb OK | Anti OK | Lang OK | Latency | style_ok | invented | notes |
|----|--------|------------|----------|----------|-----|---------|---------|---------|---------|----------|----------|-------|
| 1 | intro | Y | `—` | `—` | 215 | Y | Y | Y | 1523ms |  |  |  |
| 2 | overview | Y | `ai-agents-adk` | `—` | 361 | Y | Y | Y | 1ms |  |  |  |
| 3 | domain | Y | `ai-agents-adk` | `ai-agents-adk` | 57 | Y | Y | Y | 1770ms |  |  |  |
| 4 | domain | Y | `payment-integration-platform` | `payment-integration-platform` | 384 | Y | Y | Y | 1882ms |  |  |  |
| 5 | nominal | Y | `quark` | `quark` | 209 | Y | Y | Y | 2547ms |  |  |  |
| 6 | nominal | Y | `mcp-explorer` | `mcp-explorer` | 305 | Y | Y | Y | 2072ms |  |  |  |
| 7 | tradeoff | Y | `ai-agents-adk` | `ai-agents-adk` | 34 | Y | Y | Y | 1873ms |  |  |  |
| 8 | path | Y | `ml-pipeline-simulator` | `—` | 309 | Y | Y | Y | 1737ms |  |  |  |
| 9 | follow_up | Y | `payment-integration-platform` | `payment-integration-platform` | 417 | Y | Y | Y | 1514ms |  |  |  |
| 10 | boundary | Y | `—` | `—` | 165 | Y | Y | Y | 1369ms |  |  |  |
| 11 | intro | Y | `—` | `—` | 248 | Y | Y | Y | 1261ms |  |  |  |
| 12 | domain | Y | `ai-agents-adk` | `ai-agents-adk` | 477 | Y | Y | Y | 1916ms |  |  |  |
| 13 | overview | Y | `drop` | `—` | 346 | Y | Y | Y | 4ms |  |  |  |
| 14 | domain | Y | `payment-integration-platform` | `payment-integration-platform` | 622 | N | Y | Y | 1684ms |  |  |  |
| 15 | path | Y | `cloud-architecture-explorer` | `—` | 331 | Y | Y | Y | 1784ms |  |  |  |

## Response previews

### Case 1 — Oi, o que você faz?

- matches: `[]`
- tool_used: `adk_agent`

```
Olá! Eu construo sistemas confiáveis em engenharia de backend, agentes de IA e arquitetura cloud. Meu foco é em serviços prontos para produção, automação e decisões de plataforma que aguentam a pressão do dia a dia.
```

### Case 2 — Me fala dos seus projetos

- matches: `['ai-agents-adk', 'drop', 'quark']`
- tool_used: `overview_deterministic`

```
Alguns destaques: **AI Agents with ADK** — Intelligent agents integrated into the GCP ecosystem via MCP Toolbox; **Drop** — Clean data. Clear insights. Immediate action; **Quark** — From simple rules emerges intelligence; **PassaNota** — Every receipt recorded. Every expense under control. Quer que eu aprofunde agentes, pagamentos, labs ou um projeto pessoal?
```

### Case 3 — Como você trabalha com agentes de IA?

- matches: `['ai-agents-adk', 'drop', 'newsletter']`
- tool_used: `adk_agent`

```
Trabalho com agentes de IA principalmente na construção e
```

### Case 4 — Tem algo com Stripe ou pagamentos?

- matches: `['payment-integration-platform', 'gpos-payment-system']`
- tool_used: `adk_agent`

```
Sim, tenho dois projetos principais na área de pagamentos. O primeiro é a **Payment Integration Platform**, que foca na integração completa com Stripe para gerenciar assinaturas, webhooks e recuperação de pagamentos. O segundo é o **GPOS Payment System**, um sistema de pagamentos em .NET/C# que lida com PIX, cartões e registro de terminais remotos.

Quer que eu detalhe algum deles?
```

### Case 5 — O que é o Quark?

- matches: `['quark']`
- tool_used: `adk_agent`

```
Quark é uma simulação interativa de vida artificial onde as criaturas sobrevivem usando pequenas redes neurais e algoritmos genéticos, sem comportamentos pré-programados. Cada agente começa com uma rede neural
```

### Case 6 — Mostra um lab sobre MCP

- matches: `['mcp-explorer', 'ai-agents-adk', 'drop']`
- tool_used: `adk_agent`

```
O lab "MCP Explorer" mostra como uma requisição de agente se move através das integrações do servidor MCP e sistemas externos. Ele demonstra o protocolo MCP, a abstração de ferramentas, a integração de sistemas e a rastreabilidade, utilizando tecnologias como GitHub, Jira, banco de dados e agentes de IA.
```

### Case 7 — Como você resolveu cold start no Cloud Run?

- matches: `['ai-agents-adk', 'passanota', 'drop']`
- tool_used: `adk_agent`

```
No projeto de Agentes de IA com AD
```

### Case 8 — Quero uma trilha para aprender MLOps

- matches: `['ml-pipeline-simulator', 'data-drift-demo', 'dag-explorer']`
- tool_used: `adk_agent`

```
Para aprender MLOps, sugiro começar com o lab "ML Pipeline Simulator" para ter uma visão completa do ciclo de vida, desde a ingestão de dados até o monitoramento. Depois, o "Data Drift Demo" é excelente para entender como a distribuição de dados afeta a performance do modelo e a necessidade de retreinamento.
```

### Case 9 — E sobre isso?

- matches: `['payment-integration-platform', 'gpos-payment-system', 'ai-agents-adk']`
- tool_used: `adk_agent`

```
A Payment Integration Platform é uma integração completa com Stripe que desenvolvi para gerenciar pagamentos recorrentes. Ela cuida de webhooks, checkout automatizado, gestão de assinaturas e recuperação de pagamentos falhos, garantindo que o estado da assinatura esteja sempre sincronizado entre o Stripe e o banco de dados local. Um dos desafios principais foi garantir a idempotência no processamento dos webhooks.
```

### Case 10 — Você topa freela? Qual seu salário?

- matches: `[]`
- tool_used: `adk_agent`

```
Não discuto expectativas salariais. Para questões de disponibilidade, por favor, entre em contato via /contact ou pelo meu LinkedIn (linkedin.com/in/lucas-caldas50).
```

### Case 11 — What kind of systems do you build?

- matches: `[]`
- tool_used: `adk_agent`

```
I build reliable production systems, focusing on backend engineering, AI agents, and cloud architecture. My work involves creating production-ready services, automation workflows, and making platform decisions that stand up to operational pressure.
```

### Case 12 — Tell me about your AI agents work

- matches: `['ai-agents-adk', 'multi-agent-explorer', 'mcp-explorer']`
- tool_used: `adk_agent`

```
I've focused on building production-ready AI agent systems, particularly around reliable tool orchestration, memory, and context management in multi-agent environments on GCP.

My primary work in this area involves the "AI Agents with ADK" project, where I developed autonomous agents that integrate with Jira, Looker, and BigQuery using Google's ADK and MCP Toolbox. These agents are deployed on Cloud Run and leverage Vertex AI.

Key aspects of this project include:
*   **Or
```

### Case 13 — Any personal projects I should see?

- matches: `['drop', 'quark', 'passanota']`
- tool_used: `overview_deterministic`

```
A few highlights: **Drop** — Clean data. Clear insights. Immediate action; **Quark** — From simple rules emerges intelligence; **PassaNota** — Every receipt recorded. Every expense under control; **KnowledgeHub** — Personalized AI & technology intelligence, delivered weekly. Want me to go deeper on agents, payments, labs, or a personal project?
```

### Case 14 — How do you handle payment webhooks?

- matches: `['payment-integration-platform', 'gpos-payment-system', 'ai-agents-adk']`
- tool_used: `adk_agent`

```
In the Payment Integration Platform, the critical aspects of handling payment webhooks involved ensuring idempotency, synchronizing subscription states, and managing plan transitions. We used FastAPI to receive Stripe webhooks with HMAC signature verification, processing each event exactly once using the event ID as an idempotency key.

Key learnings from this project:
*   Testing webhooks locally with the Stripe CLI before production was invaluable.
*   Logging the full event payload greatly simplified payment dispute auditing.
*   Implementing a webhook delivery log allowed for manual reprocessing when necessary.
```

### Case 15 — Walk me through a learning path for cloud architecture

- matches: `['cloud-architecture-explorer', 'ai-agents-adk', 'autoscaling-simulator']`
- tool_used: `adk_agent`

```
I'd suggest starting with the Cloud Architecture Explorer lab to interactively understand system design, tradeoffs, and scalability planning. After that, you could look into a real-world application like the AI Agents with ADK project, which deploys autonomous agents on Cloud Run with Vertex AI, to see these concepts in practice.
```

## Human review

Preencha `style_ok` / `invented` / `notes` em [`../issues.md`](../issues.md) após ler os previews. Não altere instruction/KB para ‘passar’ neste baseline.
