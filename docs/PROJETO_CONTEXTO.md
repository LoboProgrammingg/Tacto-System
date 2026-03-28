# 📋 Tacto-System — Contexto Geral do Projeto

**Data**: 2026-03-28
**Status**: Em desenvolvimento — Fase de correções pré-go-live multi-tenant
**Último commit**: Timezone + AI Humanization + Settings consolidation

---

## 🎯 Visão Geral

**Tacto-System** é um sistema de automação de atendimento para restaurantes via WhatsApp, powered by Google Gemini AI.

### Propósito
- Automatizar respostas de clientes via WhatsApp sem intervenção humana
- Suportar múltiplos restaurantes (multi-tenant) com isolamento total de dados
- Integrar com APIs externas: Join (WhatsApp), Tacto (cardápios), Google Gemini (IA)
- Fornecer observabilidade via LangSmith e logs estruturados

### Stack Principal
- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
- **IA**: LangChain + Google Gemini API (embedding + LLM)
- **Message Queue**: Redis (buffer + caching)
- **Observabilidade**: LangSmith + structlog
- **Infraestrutura**: Docker + docker-compose (local) → Railway (produção)

---

## 🏗️ Arquitetura — Clean Architecture + DDD

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface/API Layer                      │
│  - FastAPI routers (/api/v1/...)                            │
│  - HTTP handlers (webhook_join, restaurants, ...)           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Application Layer                          │
│  - Use Cases (ProcessIncomingMessage, SyncTactoMenu, ...)   │
│  - DTOs (Data Transfer Objects)                             │
│  - Dependencies (dependency injection)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     Domain Layer                            │
│  - Entities (Restaurant, Conversation, Message, ...)        │
│  - Value Objects (OpeningHours, MessageSource, ...)         │
│  - Repositories (interfaces/contracts)                      │
│  - Services (domain-level logic)                            │
│  - Ports (abstract interfaces para infra)                   │
│  - Events (domain events para comunicação assíncrona)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│               Infrastructure Layer                          │
│  - PostgreSQL models + migrations                           │
│  - Repositories (implementações concretas)                  │
│  - External clients (JoinClient, GeminiClient, ...)         │
│  - Redis (caching, message buffer, distributed locks)       │
│  - Vector store (pgvector para embeddings)                  │
└─────────────────────────────────────────────────────────────┘
```

### Princípios
- **Dependency Rule**: Código aponta sempre para dentro (Domain)
- **Repositories**: Encapsulam persistência, retornam objetos de domínio
- **Ports (Interfaces)**: Use cases dependem de abstrações, não implementações
- **DTOs**: Transferência de dados entre camadas
- **Value Objects**: Immutable, com validação de negócio

---

## 🔐 Multi-Tenancy — Isolamento de Dados

Cada restaurante é isolado por:

1. **`canal_master_id`** (Join API instance key)
   - Unique constraint na tabela `restaurants`
   - Identifica qual restaurante ao receber webhook

2. **`restaurant_id`** (UUID)
   - Foreign key em `conversations`, `messages`, `menu_embeddings`
   - Filtra todas as queries por restaurant_id

3. **Redis keys** namespaced por restaurant
   - `buffer:{restaurant_id}:{phone}`
   - `sent_messages:{instance_key}`

4. **pgvector searches** filtrados por restaurant_id
   - Embeddings isolados: apenas busca itens do próprio restaurante

### Verificação de Multi-Tenancy
```python
# Sempre verificar:
restaurant = await restaurant_repo.find_by_canal_master_id(instance_key)
if restaurant is None:
    return error  # Rejeita requests de restaurantes não registrados

# Todos os repositórios filtram por restaurant_id
conversations = await conv_repo.find_by_restaurant(restaurant.id)
```

---

## 📊 Modelo de Domínio

### Aggregates

#### 1. **Restaurant** (Aggregate Root)
```
Restaurant
├── id: RestaurantId
├── name, prompt_default, menu_url
├── opening_hours: OpeningHours (VO)
├── integration_type: IntegrationType (VO — JOIN, TACTO, etc)
├── automation_type: AutomationType (VO — BASIC, ADVANCED, etc)
├── canal_master_id: str (unique — Join API key)
├── timezone: str (America/Sao_Paulo, etc)
├── is_active, created_at, updated_at, deleted_at
└── [Methods] is_open_now(), get_today_hours(), update_prompt(), ...
```

#### 2. **Conversation** (Aggregate Root)
```
Conversation
├── id: ConversationId
├── restaurant_id: RestaurantId (FK)
├── customer_phone: PhoneNumber (VO)
├── customer_name: Optional[str]
├── is_ai_active: bool
├── ai_disabled_until: Optional[datetime]
├── ai_disabled_reason: str
├── message_count, last_message_at, created_at, updated_at
└── [Methods] disable_ai(), enable_ai(), record_message(), ...
```

#### 3. **Message** (Value Object)
```
Message
├── id: MessageId
├── conversation_id: ConversationId (FK)
├── body: str
├── direction: MessageDirection (INCOMING / OUTGOING)
├── source: MessageSource (CUSTOMER / AI / HUMAN_OPERATOR)
├── timestamp, external_id (Join API message_id)
└── [Immutable]
```

### Value Objects
- **OpeningHours**: Weekly schedule (Mon-Sun) com `is_open_now(tz)`, `get_next_opening(tz)`
- **DaySchedule**: Horário de um dia específico
- **PhoneNumber**: Telefone do cliente (validado)
- **MessageDirection**: INCOMING, OUTGOING
- **MessageSource**: CUSTOMER, AI, HUMAN_OPERATOR, ECHO
- **RestaurantId, ConversationId, MessageId**: Typed UUIDs

### Repositories (Interfaces)
```python
# domain/restaurant/repository.py
class RestaurantRepository(ABC):
    async def find_by_id(id) -> Restaurant
    async def find_by_canal_master_id(canal_master_id) -> Restaurant
    async def find_all_active() -> List[Restaurant]
    async def save(restaurant) -> Restaurant
    async def delete(id) -> bool

# domain/messaging/repository.py
class ConversationRepository(ABC):
    async def find_by_id(id) -> Conversation
    async def find_by_restaurant_and_phone(restaurant_id, phone) -> Conversation
    async def save(conversation) -> Conversation

class MessageRepository(ABC):
    async def save(message) -> Message
    async def find_recent_by_conversation(conversation_id, limit) -> List[Message]
```

---

## 🤖 IA — Level 1 Agent (BASIC Automation)

### Fluxo de Processamento

```
1. Webhook Join recebe mensagem WhatsApp
   ↓
2. Validar: from_me=false (ignorar respostas do bot)
   ↓
3. Find/Create Conversation (multi-tenant by restaurant_id)
   ↓
4. Check: AI ativo? (conversation.is_ai_active)
   ↓
5. RAG Search: Embed mensagem → buscar items cardápio relevantes
   ↓
6. Build AgentContext com:
   - is_open: restaurant.is_open_now()
   - next_opening_text: para resposta de fechamento
   - rag_context: itens relevantes
   - conversation_history: últimas 10 mensagens
   ↓
7. Level1Agent.process():
   a) Se restaurante fechado → resposta pré-pronta + disable AI
   b) Se "quero atendente" → handoff response + disable AI
   c) Senão → LLM gera resposta humanizada
   ↓
8. Send via Join API + Save outgoing message
```

### SYSTEM_PROMPT (Reescrito - 2026-03-28)

**Personality**:
- Nome: **Maria** (atendente virtual)
- Simpática, educada, prestativa
- Respostas CURTAS (máx 2 frases)
- **Máximo 1 emoji por mensagem** (só quando expressivo)
- Use nome cliente APENAS na saudação inicial
- Nunca revele que é IA (a menos que perguntado)

**Rules**:
- NUNCA mencione preços (redirecionar para cardápio)
- SEMPRE enviar link do cardápio quando perguntado
- Use itens RAG para orientar cliente
- Horários e endereço quando perguntado

### AgentContext
```python
@dataclass
class AgentContext:
    restaurant_id: UUID
    restaurant_name: str
    customer_phone: str
    customer_name: Optional[str]
    menu_url: str
    prompt_default: str
    opening_hours: dict
    is_open: bool  # ← Novo
    next_opening_text: str  # ← Novo
    rag_context: str
    automation_level: int = 1
```

### AgentResponse
```python
@dataclass
class AgentResponse:
    message: str
    should_send: bool = True
    triggered_actions: list[str] = []
    # Possíveis actions:
    # - "menu_url_sent" (cardápio enviado)
    # - "human_handoff" (cliente pediu atendente)
    # - "restaurant_closed" (restaurante fechado)
```

---

## 🔄 Fluxo de Mensagens — from_me Echo Detection

**Problema resolvido**: Join API envia webhook com `fromMe=true` ~1s após bot enviar mensagem.

**Solução**: TTL curto (5s) no Redis para distinguir echo de operador humano.

### Sequência
```
1. Bot sends message via Join API
   ↓ [resposta imediata: {"status": 200, "response": "..."}]
   ↓ [SEM message_id no response]
   ↓
2. Store message ID em Redis (phone + timestamp)
   ├─ Redis.set(f"sent_messages:{instance_key}:{phone}", msg_id, ex=5)
   └─ TTL=5s (tempo de vida da entry)
   ↓
3. ~1s depois, Join fires webhook with fromMe=true
   ├─ Check: está em sent_messages? SIM → é echo do bot, ignora
   └─ TTL expirou? SIM → é operador humano, processa
   ↓
4. Se é operador humano → disable AI para esse número
```

---

## 📍 Timezone — Correção Implementada (2026-03-28)

**Problema**: `datetime.now()` usa hora local do servidor (UTC em produção), não do restaurante.

**Solução**:
- Restaurant entity agora tem campo `timezone` (default: "America/Sao_Paulo")
- `OpeningHours.is_open_now(tz)` usa `datetime.now(ZoneInfo(tz))`
- Docker tem `TZ=America/Sao_Paulo` definido
- `datetime.utcnow()` substituído por `datetime.now(timezone.utc)`

**Uso**:
```python
# No use case:
is_open = restaurant.is_open_now()  # Usa restaurant.timezone automaticamente

# No prompt:
next_opening = restaurant.opening_hours.get_next_opening(restaurant.timezone)
# Retorna: "Abrimos amanhã, segunda-feira, às 11:00"
```

---

## ⚙️ Settings & Environment Variables

**Arquivo**: `tacto/config/settings.py`

### AppSettings
```python
ai_disable_hours: int = 12  # AI_DISABLE_HOURS
rag_search_limit: int = 6   # RAG_SEARCH_LIMIT
conversation_history_limit: int = 10  # CONVERSATION_HISTORY_LIMIT
```

### RedisSettings
```python
buffer_window_seconds: int = 5  # REDIS_BUFFER_WINDOW_SECONDS
buffer_lock_ttl: int = 10  # REDIS_BUFFER_LOCK_TTL
echo_tracker_ttl: int = 5  # REDIS_ECHO_TRACKER_TTL
message_id_tracker_ttl: int = 300  # REDIS_MSG_ID_TRACKER_TTL
```

### GeminiSettings
```python
max_tokens: int = 2048  # GEMINI_MAX_TOKENS
temperature: float = 0.7  # GEMINI_TEMPERATURE
level1_temperature: float = 0.7  # LEVEL1_TEMPERATURE
level1_max_tokens: int = 2048  # LEVEL1_MAX_TOKENS
```

---

## 🗄️ Database Schema

### Tabelas Principais

#### `restaurants`
```sql
id (UUID, PK)
name (VARCHAR)
prompt_default (TEXT)
menu_url (VARCHAR)
opening_hours (JSONB)
integration_type (INT)
automation_type (INT)
chave_grupo_empresarial (UUID)
canal_master_id (VARCHAR, UNIQUE) ← Join API instance key
empresa_base_id (VARCHAR)
timezone (VARCHAR) ← Novo (2026-03-28)
is_active (BOOLEAN)
created_at, updated_at, deleted_at (TIMESTAMPTZ)
```

#### `conversations`
```sql
id (UUID, PK)
restaurant_id (UUID, FK → restaurants)
customer_phone (VARCHAR(20))
customer_name (VARCHAR)
is_ai_active (BOOLEAN)
ai_disabled_until (TIMESTAMPTZ)
ai_disabled_reason (VARCHAR)
message_count (INT)
last_message_at (TIMESTAMPTZ)
created_at, updated_at (TIMESTAMPTZ)
UNIQUE(restaurant_id, customer_phone)
```

#### `messages`
```sql
id (UUID, PK)
conversation_id (UUID, FK → conversations)
body (TEXT)
direction (INT) ← 0=INCOMING, 1=OUTGOING
source (INT) ← 0=CUSTOMER, 1=AI, 2=HUMAN_OPERATOR, 3=ECHO
timestamp (TIMESTAMPTZ)
external_id (VARCHAR) ← Join API message_id
created_at (TIMESTAMPTZ)
```

#### `menu_embeddings`
```sql
id (UUID, PK)
restaurant_id (UUID, FK → restaurants)
content (TEXT)
embedding (vector(768)) ← pgvector
metadata (JSONB)
created_at, updated_at (TIMESTAMPTZ)
INDEX: restaurant_id, IVFFlat(embedding, cosine)
```

#### `customer_memories` (para contexto conversacional)
```sql
id (UUID, PK)
conversation_id (UUID, FK → conversations)
memory_type (VARCHAR) ← "context", "preference", "history"
content (TEXT)
timestamp (TIMESTAMPTZ)
```

---

## 🔌 Integrações Externas

### Join Developer API (WhatsApp)
- **Endpoint**: POST `https://api-prd.joindeveloper.com.br/message/send`
- **Auth**: Token no header
- **Webhook**: POST `/api/v1/webhooks/join` (messages.upsert, messages.update)
- **Response**: `{"status": 200, "response": "Message sent"}` (SEM message_id)
- **Quirk**: Echo message ~1s depois com `fromMe=true`

### Google Gemini API
- **Models**:
  - LLM: `gemini-2.5-flash` (conversa)
  - Embedding: `models/gemini-embedding-001` (768 dims)
- **Uso**: Embeddings para RAG, LLM para resposta
- **Observabilidade**: Logs estruturados + LangSmith tracing

### Tacto External API (Cardápios)
- **Endpoint**: https://api-externa.tactonuvem.com.br
- **Auth**: OAuth2 token-based
- **Uso**: Fetch cardápio com endereço e horários
- **Caching**: Redis 1h

---

## 📝 Migrations Alembic

**Chain de migrations**:
```
001_initial_schema (restaurants, conversations, messages)
    ↓
002_customer_memories (adiciona memory table)
    ↓
003_menu_embeddings (tabela de embeddings para RAG)
    ↓
004_restaurant_timezone (Novo - 2026-03-28)
```

**Como rodar**:
```bash
# Development (local)
DB_HOST=localhost DB_PORT=5433 python -m alembic -c alembic.ini upgrade head

# Production
python -m alembic -c alembic.ini upgrade head
```

---

## 🐳 Docker Compose (Local Development)

```yaml
postgres:
  image: pgvector/pgvector:pg16
  ports: 5433:5432
  volumes: postgres_data
  env: POSTGRES_USER=tacto, POSTGRES_PASSWORD=tacto, POSTGRES_DB=tacto_db
  healthcheck: pg_isready

redis:
  image: redis:7-alpine
  ports: 6380:6379
  volumes: redis_data
  healthcheck: redis-cli ping

api:
  build: Dockerfile
  ports: 8100:8000
  environment:
    - TZ=America/Sao_Paulo
    - DEBUG=true
    - DB_HOST=postgres, DB_PORT=5432
    - REDIS_HOST=redis, REDIS_PORT=6379
    - LANGSMITH_TRACING=true (se configurado)
  depends_on: postgres, redis (health checks)
  healthcheck: curl http://localhost:8000/health
```

---

## 🔐 Observabilidade — LangSmith

**Configuração** (2026-03-28):
```python
# .env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT="Tacto-System"
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

**Habilitação** em `main.py`:
```python
def _configure_langsmith(settings: Settings):
    if not settings.langsmith.tracing or not settings.langsmith.api_key:
        return

    # Set BOTH naming conventions for compatibility
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    # ... (todos os env vars)
```

**Próximo passo**: Refatorar `Level1Agent` para LCEL com `RunnableConfig` para estruturado tracing.

---

## 📌 Status de Implementação (2026-03-28)

### ✅ Completo
- [x] Multi-tenancy base (restaurant_id isolation)
- [x] Restaurant entity + repository
- [x] Conversation + message entities
- [x] Level1Agent (BASIC automation)
- [x] Join webhook integration
- [x] Gemini embedding + LLM
- [x] pgvector RAG search
- [x] Message buffer + echo detection
- [x] Timezone support (restaurant-specific)
- [x] AI humanization (Maria persona, 1 emoji max)
- [x] Settings consolidation (app, redis, gemini)
- [x] LangSmith basic setup

### 🔄 Em Progresso
- [ ] LangChain LCEL chain (Level1Agent refactor)
- [ ] DDD ports cleanup (EmbeddingClient, VectorStore, MessagingClient)
- [ ] Settings: usar em todos os arquivos (conversation, webhook, tracker, agent)
- [ ] Buffer logic no domain layer

### 📋 Próximos
- [ ] Level 2 Agent (ADVANCED — com contexto de historicidade)
- [ ] Level 3 Agent (PRO — com recommendations)
- [ ] Async task queue para processamento pesado
- [ ] Webhooks de eventos para sync em background
- [ ] Testes de integração (pytest + testcontainers)

---

## 🎓 Como Onboard um Dev Novo

1. Leia este arquivo (`PROJETO_CONTEXTO.md`)
2. Leia `docs/ARQUITETURA_DDD.md` para detalhes de domínio
3. Clone repo → `docker-compose up -d` → rodar migrations
4. Estude `tacto/application/use_cases/process_incoming_message.py` (fluxo principal)
5. Estude `tacto/domain/ai/agents/level1_agent.py` (IA)
6. Inicie com issues labeled `good-first-issue`

---

## 📞 Contato & Dúvidas

**Slack/Discord**: [seu canal aqui]
**Issues**: GitHub issues do projeto
**Docs**: Ver `/docs` do projeto
**Observabilidade**: LangSmith (Tacto-System project)

---

**Last Updated**: 2026-03-28 — Pre-go-live corrections phase
