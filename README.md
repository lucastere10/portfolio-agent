# 🤖 Portfolio Agent

> Agente conversacional inteligente alimentado por Google ADK e FastAPI com recomendações semânticas de projetos e labs.

Um servidor FastAPI que oferece uma API RESTful para interações com um agente conversacional baseado em IA. O agente usa a base de conhecimento integrada para fornecer recomendações personalizadas de projetos e labs do portfólio.

---

## ✨ Características

- **Conversas Multi-turno**: Mantém contexto de sessão por até 30 minutos
- **Recomendações Semânticas**: Busca de projetos e labs através de embeddings
- **Múltiplos Provedores de LLM**: Suporta Google Gemini e OpenAI
- **Base de Conhecimento Integrada**: Carregamento automático de catálogo, perfil e skills
- **Cache Inteligente**: Indexação em memória para buscas rápidas
- **CORS Configurável**: Compatível com front-ends locais e remotos
- **Cloud Run Ready**: Dockerfile otimizado para Google Cloud Platform
- **Health Checks**: Monitoramento automático de saúde do serviço

---

## 🏗️ Arquitetura

```
portfolio-agent/
├── src/
│   ├── adk/                    # Google ADK integration
│   ├── api/                    # API routes (FastAPI)
│   ├── config.py              # Settings & environment
│   ├── domain/                # Business logic
│   ├── knowledge_base/        # Índices e loader de conhecimento
│   ├── orchestration/         # Orquestração de fluxo
│   ├── providers/             # Configuração de LLM providers
│   ├── session/               # Gerenciamento de sessão
│   └── tools/                 # Ferramentas do agente
├── main.py                     # FastAPI entry point
├── pyproject.toml             # Dependências Python
├── Dockerfile                 # Multi-stage build otimizado
├── .dockerignore              # Exclusões Docker
└── cloudbuild.yaml            # Google Cloud Build pipeline
```

---

## 📋 Requisitos

- **Python**: >= 3.13
- **uv**: Gerenciador de pacotes Python (recomendado)
- **Docker**: Para containerização
- **API Keys**: 
  - Google Gemini (padrão) ou
  - OpenAI (alternativa)

---

## 🚀 Início Rápido

### Opção 1: Desenvolvimento Local

#### 1. Clonar e preparar ambiente

```bash
# Clone o repositório
git clone <your-repo>
cd portfolio-agent

# Criar ambiente virtual com uv (recomendado)
uv venv
source .venv/bin/activate  # ou: .\.venv\Scripts\Activate (Windows)

# Ou com venv padrão
python -m venv .venv
source .venv/bin/activate
```

#### 2. Instalar dependências

```bash
# Com uv (mais rápido)
uv pip install -e .

# Ou com pip padrão
pip install -e .
```

#### 3. Configurar variáveis de ambiente

```bash
# Copiar template
cp .env.example .env

# Editar .env com suas credenciais
nano .env
```

#### 4. Executar servidor local

```bash
# Com reload automático (desenvolvimento)
python main.py

# Ou com uvicorn direto
uvicorn main:app --reload --port 8000
```

✅ Acesse em: `http://localhost:8000`

---

### Opção 2: Docker Local

```bash
# Build da imagem
docker build -t portfolio-agent:local .

# Run container
docker run -p 8080:8080 \
  --env-file .env \
  portfolio-agent:local

# Health check
curl http://localhost:8080/health
```

---

### Opção 3: Google Cloud Run

```bash
# Submit build ao Cloud Build
gcloud builds submit --config cloudbuild.yaml .

# Configurar variáveis de ambiente após deploy
gcloud run services update portfolio-agent \
  --set-env-vars LLM_PROVIDER=gemini \
  --region southamerica-east1
```

---

## 🔧 Configuração

### Variáveis de Ambiente

Veja `.env.example` para a lista completa. Principais:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LLM_PROVIDER` | `gemini` | Provedor de LLM: `gemini` ou `openai` |
| `PORTFOLIO_AGENT_GEMINI_API_KEY` | - | Chave API Google Gemini |
| `PORTFOLIO_AGENT_OPENAI_API_KEY` | - | Chave API OpenAI |
| `APP_VERSION` | `0.1.0` | Versão da aplicação |
| `DEBUG` | `false` | Modo debug (use `true` em dev) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Origens permitidas para CORS |
| `SESSION_TTL_SECONDS` | `1800` | TTL de sessão (30 min) |
| `SESSION_MAX_MESSAGES` | `20` | Máximo de mensagens por sessão |

---

## 📡 API Endpoints

### Health Check

```http
GET /health
```

Retorna status do serviço, versão, tamanho do catálogo e estado do LLM.

**Exemplo:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "catalog_size": 42,
  "projects": 30,
  "labs": 12,
  "provider": "gemini",
  "llm_configured": true
}
```

### API v1

Veja documentação interativa em: `/docs` (Swagger UI)

---

## 🏗️ Desenvolvimento

### Estrutura de Pastas

- **`src/adk/`**: Integração com Google Agent Development Kit
- **`src/api/`**: Rotas FastAPI (controllers)
- **`src/domain/`**: Lógica de negócio e modelos
- **`src/knowledge_base/`**: Carregamento e indexação de dados
- **`src/providers/`**: Abstração de provedores LLM
- **`src/session/`**: Gerenciamento de conversas
- **`src/tools/`**: Ferramentas customizadas do agente

### Debug e Logs

```python
# Logs automáticos via Python logging
# Configure nível no main.py:
logging.basicConfig(level=logging.DEBUG)  # ou INFO, WARNING
```

---

## 🐳 Docker & Cloud Build

### Build Local

```bash
# Build otimizado multi-stage
docker build -t portfolio-agent:dev .

# Com buildkit para cache melhorado
DOCKER_BUILDKIT=1 docker build -t portfolio-agent:dev .
```

### Cloud Build (GCP)

```bash
# Deploy automático via Cloud Build
gcloud builds submit --config cloudbuild.yaml .

# Ou com substituições customizadas
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions _IMAGE_NAME=portfolio-agent,_TAG=v1.0.0 \
  .
```

**Fluxo no Pipeline:**
1. Build Docker image → Artifact Registry
2. Push → Artifact Registry (southamerica-east1)
3. Deploy → Cloud Run com auto-scaling

---

## 🧪 Testes

```bash
# Com pytest (não incluído, adicionar se necessário)
pip install pytest pytest-asyncio

# Executar testes
pytest

# Com cobertura
pytest --cov=src/
```

---

## 📊 Monitoramento

### Health Endpoint

```bash
# Health check recorrente
watch -n 10 'curl -s http://localhost:8080/health | jq .'
```

### Logs em Cloud Run

```bash
# Ver logs em tempo real
gcloud run logs read portfolio-agent --region southamerica-east1 --limit=50 --follow
```

---

## 🔐 Segurança

- ✅ Imagem Docker com usuário não-root (`appuser`)
- ✅ Variáveis sensíveis via `.env` (não no Git)
- ✅ CORS restrito a origens conhecidas
- ✅ Session service com TTL automático
- ✅ Exception handler global para erros

**Checklist antes de produção:**
- [ ] Gerar novas API keys (não reusar dev keys)
- [ ] Configurar CORS apenas com domínios produção
- [ ] Ativar autenticação Cloud Run se necessário
- [ ] Revisar variáveis em `.env` (nunca commit!)
- [ ] Testar health endpoint
- [ ] Monitorar logs iniciais

---

## 🤝 Contribuição

1. Create feature branch: `git checkout -b feature/minha-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push: `git push origin feature/minha-feature`
4. Open Pull Request

---

## 📝 Licença

MIT

---

## 🆘 Troubleshooting

### Erro: "API key not configured"

```bash
# Verificar .env
cat .env | grep GEMINI_API_KEY

# Ou testar health endpoint
curl http://localhost:8080/health
```

### Erro: "Module not found"

```bash
# Reinstalar dependências
uv pip install --force-reinstall -e .

# Ou com pip
pip install --force-reinstall -e .
```

### Container não inicia

```bash
# Ver logs Docker
docker logs <container-id>

# Ou executar com output
docker run --rm -it portfolio-agent:local
```

### Cloud Run: Service timeout

Verificar:
- [ ] API keys válidas
- [ ] Base de conhecimento carregada (`/health` endpoint)
- [ ] Aumentar `--timeout=300` no cloudbuild.yaml

---

## 📞 Suporte

Para issues e perguntas, abra uma issue no repositório.

---

**Desenvolvido com ❤️ usando FastAPI, Google ADK e Python 3.13**
