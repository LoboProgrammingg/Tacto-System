# 📚 Documentação — Tacto-System

Bem-vindo à documentação do **Tacto-System**! Este diretório contém tudo que você precisa para entender e trabalhar no projeto.

---

## 🚀 Quick Start Para Novos Devs

1. **Leia em ordem**:
   - [`PROJETO_CONTEXTO.md`](#projeto-contexto) — Entenda o projeto
   - [`STATUS_IMPLEMENTACAO.md`](#status-implementacao) — Saiba o que já foi feito
   - [`PROMPT_WINDSURF.md`](#prompt-windsurf) — Se você é o Windsurf continuando o trabalho

2. **Clone + Setup**:
   ```bash
   git clone <repo>
   cd Tacto-System
   docker-compose up -d
   DB_HOST=localhost DB_PORT=5433 python -m alembic upgrade head
   ```

3. **Veja saúde**:
   ```bash
   curl http://localhost:8100/health
   ```

4. **Estude o código principal**:
   - `tacto/application/use_cases/process_incoming_message.py` — fluxo principal
   - `tacto/domain/ai/agents/level1_agent.py` — IA
   - `tacto/interfaces/http/routes/webhook_join.py` — webhook de entrada

---

## 📖 Documentos

### PROJETO_CONTEXTO.md
**Para**: Todos os devs (especialmente novos)

**Contém**:
- Visão geral do projeto (propósito, stack)
- Arquitetura Clean + DDD
- Multi-tenancy (isolamento de dados)
- Modelo de domínio (Entities, VOs, Aggregates, Repositories)
- IA — Level 1 Agent (fluxo, prompts, AgentContext)
- Timezone (corriger hora do servidor)
- Settings & environment variables
- Database schema (tabelas principais)
- Integrações externas (Join, Gemini, Tacto)
- Migrations Alembic
- Docker Compose setup
- LangSmith observability
- Status de implementação
- Como onboard um dev novo

**Tempo de leitura**: 30-40 min

---

### STATUS_IMPLEMENTACAO.md
**Para**: Devs continuando trabalho (especialmente Windsurf)

**Contém**:
- Status dos 6 problemas identificados
- O que Claude já fez (✅ 2,5 problemas)
- O que ainda precisa (🔄 3,5 problemas)
- Lista detalhada de arquivos modificados
- Testes manuais necessários
- Environment variables
- Próximos passos priorizados

**Tempo de leitura**: 20-30 min

---

### PROMPT_WINDSURF.md
**Para**: Windsurf (ou quem continua o trabalho)

**Contém**:
- Context rápido (leia PROJETO_CONTEXTO + STATUS primeiro)
- Tarefas concretas (Task 1-4) com código exemplo
- Instruções passo-a-passo para cada task
- Checklist de validação
- Estimativa de tempo
- Referências rápidas

**Tempo de execução**: 2-3 horas (incluindo testes)

---

## 🗂️ Estrutura do Projeto

```
Tacto-System/
├── docs/                           # Documentação
│   ├── README.md                   # Este arquivo
│   ├── PROJETO_CONTEXTO.md         # Visão geral completa
│   ├── STATUS_IMPLEMENTACAO.md     # Status de tarefas
│   └── PROMPT_WINDSURF.md          # Instruções para continuação
│
├── tacto/                          # Código da aplicação
│   ├── config/                     # Settings e configuração
│   ├── domain/                     # Domínio (lógica de negócio)
│   │   ├── restaurant/             # Restaurant aggregate
│   │   ├── messaging/              # Conversation e Message
│   │   ├── ai/                     # Agentes IA e prompts
│   │   ├── assistant/              # Ports para IA
│   │   └── shared/                 # Exceções, Value Objects
│   ├── application/                # Use Cases e DTOs
│   │   ├── use_cases/              # ProcessIncomingMessage, SyncTactoMenu
│   │   └── dto/                    # RestaurantDTO, MessageDTO
│   ├── infrastructure/             # Implementações concretas
│   │   ├── database/               # Models, migrations
│   │   ├── persistence/            # Repositórios
│   │   ├── messaging/              # Clients (Join, etc)
│   │   ├── ai/                     # Clients (Gemini)
│   │   └── vector_store/           # PgVector
│   ├── interfaces/                 # FastAPI routers
│   │   └── http/
│   │       ├── routes/             # Endpoints
│   │       ├── dependencies.py     # Injeção de dependências
│   │       └── webhooks/           # Handlers de webhook
│   └── main.py                     # Entry point FastAPI
│
├── docker-compose.yml              # Postgres + Redis + API
├── Dockerfile                      # Build image
├── requirements.txt                # Python dependencies
├── alembic.ini                     # Configuração migrations
├── .env.example                    # Template variáveis (criar)
└── README.md                       # README principal
```

---

## 🎯 O Que Cada Camada Faz

### Domain (Lógica de Negócio)
- **Entities**: `Restaurant`, `Conversation`, `Message`
- **Value Objects**: `OpeningHours`, `PhoneNumber`, `MessageSource`
- **Repositories** (interfaces): `RestaurantRepository`, `ConversationRepository`
- **Services**: `Level1Agent`, `MessageBufferService`
- **Ports**: `EmbeddingClient`, `VectorStore`, `MessagingClient`

### Application (Orquestração)
- **Use Cases**: `ProcessIncomingMessage`, `SyncTactoMenu`, `CreateRestaurant`
- **DTOs**: `IncomingMessageDTO`, `RestaurantDTO`
- **Dependências**: Injeção de repositórios, clients, agents

### Infrastructure (Implementações Concretas)
- **Database**: SQLAlchemy models + Alembic migrations
- **Repositories**: Implementações de `RestaurantRepository`, `ConversationRepository`
- **Clients**: `JoinClient` (WhatsApp), `GeminiClient` (IA), `TactoAPIClient`
- **Vector Store**: `PgvectorStore` (RAG search)

### Interface (API HTTP)
- **Routers**: `/api/v1/restaurants`, `/api/v1/webhooks/join`
- **Webhooks**: Recebe mensagens de WhatsApp
- **Health checks**: `/health`, `/ready`

---

## 🔄 Fluxo Principal

```
1. Webhook Join → POST /api/v1/webhooks/join
   Body: { instance_key, messages: [{ id, from, body, timestamp, fromMe }] }

2. ProcessIncomingMessageUseCase.execute()
   ├─ Find restaurant por canal_master_id (instance_key)
   ├─ Find/Create conversation (restaurant_id + phone)
   ├─ Check: AI ativo?
   ├─ RAG search: Embed mensagem → buscar items cardápio
   ├─ Level1Agent.process():
   │  ├─ Se fechado → resposta pré-pronta
   │  ├─ Se "atendente" → human handoff
   │  └─ Senão → LLM gera resposta
   ├─ Send via Join API
   └─ Save messages (incoming + outgoing)

3. Return 200 OK
```

---

## 🧪 Como Testar

### Localmente (com Docker)
```bash
docker-compose up -d

# Verificar containers
docker-compose ps

# Logs da API
docker-compose logs -f api

# Parar
docker-compose down
```

### Health Check
```bash
curl http://localhost:8100/health
# {"status":"healthy","version":"0.0.1"}

curl http://localhost:8100/ready
# {"status":"ready","checks":{"database":"ok","redis":"ok"}}
```

### Database
```bash
# Conectar ao Postgres
psql -h localhost -p 5433 -U tacto -d tacto_db

# Ver tabelas
\dt

# Ver migrations aplicadas
SELECT * FROM alembic_version;

# Sair
\q
```

### Redis
```bash
# Conectar
redis-cli -p 6380

# Ver keys
KEYS *

# Monitor em tempo real
MONITOR
```

---

## 🚀 Próximos Passos Críticos

### Hoje (Por Windsurf)
1. ✅ Leia `PROJETO_CONTEXTO.md`
2. ✅ Leia `STATUS_IMPLEMENTACAO.md`
3. ✅ Leia `PROMPT_WINDSURF.md`
4. 🔄 Faça Task 1 (Settings)
5. 🔄 Faça Task 2 (LCEL Chain)
6. 🔄 Faça Task 3 (DDD Ports)

### Semana
- Testes manuais (timezone, humanização, settings, LangSmith)
- Code review + merge
- Preparar para deploy

### Go-Live
- Deploy em Railway
- Monitor LangSmith + Sentry
- Suporte aos restaurantes

---

## 🔐 Security Checklist

- [ ] Nenhum secret no código (usar .env)
- [ ] HMAC validation em webhooks
- [ ] Rate limiting em endpoints
- [ ] Input validation com Pydantic
- [ ] SQL sempre parameterized (SQLAlchemy ORM)
- [ ] CORS whitelisted
- [ ] Logs sem dados sensíveis

---

## 📞 Dúvidas Frequentes

**P: Como adicionar novo restaurant?**
A: POST `/api/v1/restaurants` com dados de criação. Veja `CreateRestaurantUseCase`.

**P: Como mudar o prompt da IA?**
A: Altere `SYSTEM_PROMPT` em `level1_prompts.py` ou `restaurant.prompt_default`.

**P: Como debugar um problema de RAG?**
A: Veja logs em `sent_messages`, `embeddings_stored`, `rag_semantic_search`.

**P: Timezone não está correto?**
A: Verifique `restaurant.timezone` (deve ser algo como "America/Sao_Paulo").

**P: Como ver trace no LangSmith?**
A: Abra https://smith.langchain.com/ → Projeto "Tacto-System" → veja traces.

---

## 📚 Referências

- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- LangChain: https://python.langchain.com/
- Clean Architecture: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Domain-Driven Design: https://martinfowler.com/bliki/DomainDrivenDesign.html

---

## 👥 Team

- **Product**: [Nome]
- **Backend Lead**: [Nome]
- **IA Lead**: [Nome]
- **DevOps**: [Nome]

---

## 📝 Versão

- **Documento**: v1.0
- **Projeto Status**: Pre-go-live corrections (60% done)
- **Última atualização**: 2026-03-28
- **Próxima revisão**: Após Windsurf completar tasks

---

**Bem-vindo ao Tacto-System! 🚀**
