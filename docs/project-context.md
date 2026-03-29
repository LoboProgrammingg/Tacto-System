# Tacto-System — Contexto Geral do Projeto

**Versão:** 1.1.0  
**Última Atualização:** 2026-03-29  
**Status:** ✅ Sistema Funcional — Refatoração DDD Completa (ADR-005 Implemented)  
**Metodologias:** DDD (Eric Evans), Clean Architecture, SOLID, KISS, Clean Code

---

## Índice

1. [Visão do Produto](#visão-do-produto)
2. [Como Funciona](#como-funciona)
3. [Arquitetura Técnica](#arquitetura-técnica)
4. [Bounded Contexts](#bounded-contexts)
5. [Multi-tenancy](#multi-tenancy)
6. [Stack e Integrações](#stack-e-integrações)
7. [Configuração de Ambiente](#configuração-de-ambiente)
8. [Como Rodar Localmente](#como-rodar-localmente)
9. [Como Adicionar Novo Restaurante](#como-adicionar-novo-restaurante)
10. [Features Implementadas](#features-implementadas)
11. [Backlog](#backlog)
12. [Referências](#referências)

---

## Visão do Produto

**Tacto-System** é um backend multi-tenant para automação de atendimento via WhatsApp para restaurantes. O sistema usa IA (Google Gemini) para simular uma atendente humanizada que responde clientes em tempo real, integrada com a plataforma Tacto para dados de cardápio e com a Join Developer API para comunicação WhatsApp.

### Problema Resolvido

Restaurantes recebem alto volume de mensagens via WhatsApp e precisam:
- Responder 24/7 sem aumentar equipe
- Fornecer informações de cardápio, horários e endereço de forma consistente
- Não perder clientes fora do horário comercial
- Manter qualidade de atendimento personalizado por cliente

### Modelo de Operação

**Multi-tenant interno** (não SaaS):
- Múltiplos restaurantes no mesmo sistema
- Infraestrutura compartilhada (DB, Redis, APIs)
- Dados completamente isolados por `restaurant_id`
- Cada restaurante tem sua própria instância WhatsApp (Join), seu próprio prompt e horários

---

## Como Funciona

### Fluxo de uma mensagem até a resposta da IA

```
Cliente envia mensagem no WhatsApp
         ↓
Join Developer API dispara webhook
  POST /api/v1/webhook/join
  { "instance": "canal_master_id_do_restaurante", "event": "messages.upsert", ... }
         ↓
webhook_join.py
  1. Filtra eventos não-mensagem (connection.update, etc.)
  2. Detecta fromMe=true → ignora (mensagem enviada pelo número)
  3. Detecta operador humano via SentMessageTracker (TTL 15s)
     → se detectado: registra human_intervention, desativa IA 12h
  4. Extrai: instance_key, phone, texto, message_id
  5. Responde 200 OK imediatamente (não bloqueia Join)
  6. Envia para MessageBufferService (background task)
         ↓
MessageBufferService (Redis, janela 5s)
  - Acumula mensagens rápidas do mesmo cliente
  - Aguarda 5 segundos de silêncio
  - Concatena e chama ProcessIncomingMessageUseCase
         ↓
ProcessIncomingMessageUseCase.execute()
  1. Busca restaurante por canal_master_id → Restaurant entity
  2. Verifica se restaurante está ativo
  3. Busca/cria Conversation (restaurant_id + phone)
  4. Verifica is_ai_active → se False, não responde
  5. Verifica se é humano (fromMe=True + source=phone) → desativa IA 12h
  6. Verifica horário de funcionamento → se fechado, responde e encerra
  7. Busca histórico recente de mensagens
  8. Executa RAG: embedding da mensagem → busca semântica no pgvector por restaurant_id
  9. Busca dados institucionais da Tacto API (endereço, horários reais)
 10. Monta AgentContext com todos os dados do restaurante
 11. Level1Agent.process(message, context, history)
         ↓
Level1Agent (infrastructure/agents/)
  - Verifica restaurante fechado → retorna mensagem de fechamento sem chamar LLM
  - Verifica pedido de atendente humano → retorna handoff sem chamar LLM
  - Carrega memória 3 níveis:
      short_term  → Redis (conversa atual, TTL 30min)
      medium_term → Redis (visitas recentes, TTL 24h)
      long_term   → PostgreSQL + busca semântica
  - Monta system prompt via Level1Prompts.build_system_prompt()
  - Invoca chain LangChain LCEL: ChatGoogleGenerativeAI | StrOutputParser
  - Salva exchange na memória
  - Retorna AgentResponse
         ↓
ProcessIncomingMessageUseCase (continuação)
  - Salva mensagem do cliente no DB
  - Salva mensagem da IA no DB
  - Envia resposta via JoinClient.send_message(instance_key, phone, texto)
  - Envia presença "composing" antes para simular digitação
```

### Fluxo de restaurante fechado

Quando o restaurante está fechado no momento da mensagem:
- `Conversation.disable_ai_until_opening()` calcula próxima abertura
- IA fica desativada até 10 minutos antes do horário de abertura
- Cliente recebe mensagem humanizada com horário de abertura
- Nenhuma chamada ao LLM é feita (economia de tokens)

### Intervenção humana

Quando um funcionário responde pelo telefone (source=phone, fromMe=True):
- `Conversation.handle_human_intervention()` desativa IA por 12h
- Sistema não interfere enquanto humano está atendendo
- IA reativa automaticamente após 12h

---

## Arquitetura Técnica

### Diagrama de camadas (Clean Architecture + DDD)

```
┌─────────────────────────────────────────────────────────┐
│              Interface Layer (HTTP)                      │
│  webhook_join.py │ restaurants.py │ instances.py │ chat  │
└──────────────────────────┬──────────────────────────────┘
                           │ depends on
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Application Layer (Use Cases)               │
│  ProcessIncomingMessage │ CreateRestaurant │ SyncMenu    │
│  FetchTactoRestaurantData │ MemoryOrchestrationService  │
│  MessageBufferService                                    │
└──────────────────────────┬──────────────────────────────┘
                           │ depends on (interfaces only)
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Domain Layer (CORE)                     │
│                                                         │
│  ai_assistance/          messaging/                     │
│  ├── ports/              ├── entities/                  │
│  │   ├── BaseAgent       │   ├── Conversation           │
│  │   ├── AIClient        │   └── Message                │
│  │   ├── EmbeddingClient ├── events/                    │
│  │   ├── MessagingClient │   ├── MessageReceived        │
│  │   ├── MenuProvider    │   ├── AIDisabled             │
│  │   └── VectorStore     │   └── AIEnabled              │
│  ├── prompts/            └── value_objects/             │
│  │   └── Level1Prompts                                  │
│  └── value_objects/      restaurant/                    │
│      ├── AgentContext    ├── entities/                  │
│      └── AgentResponse   │   └── Restaurant (AggRoot)  │
│                          ├── events/                    │
│  customer_memory/        │   └── RestaurantCreated      │
│  ├── ports/MemoryPort    └── value_objects/             │
│  └── value_objects/          OpeningHours, AutomationType│
│                                                         │
│  shared/                                                │
│  ├── events/DomainEvent (base)                          │
│  ├── exceptions/                                        │
│  └── value_objects/ (RestaurantId, PhoneNumber, etc.)   │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ implements
┌─────────────────────────────────────────────────────────┐
│             Infrastructure Layer                         │
│                                                         │
│  agents/Level1Agent          ai/GeminiClient            │
│  ai/RedisMemoryAdapter       ai/PostgresMemoryAdapter   │
│  database/ (models, conn)    external/TactoClient       │
│  external/TactoMenuProvider  messaging/JoinClient        │
│  messaging/JoinInstanceManager                          │
│  messaging/SentMessageTracker                           │
│  messaging/instance_phone_cache                         │
│  persistence/ (repositories) redis/RedisClient          │
│  vector_store/PgvectorStore                             │
└─────────────────────────────────────────────────────────┘
```

### Regra de Dependência

- **Domain**: ZERO dependências externas (sem ORM, sem HTTP, sem framework)
- **Application**: depende apenas de interfaces do domínio
- **Infrastructure**: implementa as interfaces; contém todos os detalhes técnicos
- **Interface**: controllers FastAPI + DTOs de entrada/saída

---

## Bounded Contexts

### 1. `ai_assistance` — Contexto de IA

**Responsabilidade:** Definir contratos e lógica pura de IA, sem dependências externas.

**Ports (interfaces do domínio):**
- `BaseAgent` — contrato para qualquer agente de IA (process, initialize, shutdown)
- `AIClient` — contrato para chamada ao LLM
- `EmbeddingClient` — contrato para geração de embeddings
- `MessagingClient` — contrato para envio de mensagens WhatsApp
- `MenuProvider` — contrato para obter dados de cardápio
- `VectorStore` — contrato para busca semântica

**Value Objects:**
- `AgentContext` — imutável; todos os dados que a IA precisa por conversa
- `AgentResponse` — resposta do agente com metadados

**Prompts:**
- `Level1Prompts` — lógica pura de construção de prompt; sem I/O

**Implementação concreta:** `infrastructure/agents/Level1Agent` (usa LangChain + Gemini)

---

### 2. `messaging` — Contexto de Conversas WhatsApp

**Responsabilidade:** Gerenciar conversas e mensagens; controlar estado da IA por conversa.

**Entities:**
- `Conversation` (Aggregate Root) — controla `is_ai_active`, `ai_disabled_until`, `ai_disabled_reason`
- `Message` — registro de cada mensagem (customer ou AI)

**Domain Events:**
- `MessageReceived` — emitido ao registrar nova mensagem
- `AIDisabled` — emitido quando IA é desativada
- `AIEnabled` — emitido quando IA é reativada

**Value Objects:** `MessageDirection`, `MessageSource`

**Regras de Negócio:**
- `disable_ai(reason, duration_hours=12)` — desativa com TTL
- `disable_ai_until_opening(opening_hours, tz)` — desativa até 10min antes da próxima abertura
- `handle_human_intervention()` — atalho para desativar 12h por intervenção humana
- `can_ai_respond()` — verifica `is_ai_active` + TTL do `ai_disabled_until`

---

### 3. `restaurant` — Contexto de Restaurantes

**Responsabilidade:** Gerenciar dados, configuração e regras de cada restaurante tenant.

**Entities:**
- `Restaurant` (Aggregate Root) — nome, prompt_default, menu_url, opening_hours, automation_type, canal_master_id, empresa_base_id, chave_grupo_empresarial

**Domain Events:**
- `RestaurantCreated` — emitido pelo factory method `Restaurant.create()`

**Value Objects:**
- `OpeningHours` — horários por dia da semana; calcula `is_open_now(tz)` e próxima abertura
- `AutomationType` — BASIC=1, INTERMEDIATE=2, ADVANCED=3
- `IntegrationType` — JOIN=1, WHATSAPP_BUSINESS=2

**Regras de Negócio:**
- Nome mínimo 3 caracteres
- menu_url deve ser HTTP/HTTPS válido
- `is_open_now()` — usa timezone do restaurante
- `can_process_ai_response()` — ativo + não deletado

---

### 4. `customer_memory` — Contexto de Memória

**Responsabilidade:** Gerenciar memória personalizada por cliente por restaurante.

**Ports:** `MemoryPort` — interface para load/save de memória

**Value Objects:**
- `MemoryEntry` — entrada individual de memória
- `MemoryType` — SHORT_TERM, MEDIUM_TERM, LONG_TERM
- `ConversationMemory` — agrega os 3 níveis para uma conversa

**Implementações:**
- `RedisMemoryAdapter` — short_term (TTL 30min) + medium_term (TTL 24h)
- `PostgresMemoryAdapter` — long_term permanente com busca semântica

---

### 5. `shared` — Kernel Compartilhado

- `DomainEvent` — base para todos os eventos de domínio
- Value Objects base: `RestaurantId`, `ConversationId`, `PhoneNumber`
- Exceções tipadas: `ValidationError`, `BusinessRuleViolationError`
- Result monad: `Success[T]`, `Failure[E]`

---

## Multi-tenancy

O sistema é **shared-tenancy**: infraestrutura única, isolação de dados por `restaurant_id`.

### Como um restaurante é identificado

Cada restaurante tem um `canal_master_id` — a chave da sua instância WhatsApp na plataforma Join. Quando o Join dispara um webhook, inclui `instance = canal_master_id`. O sistema usa isso para buscar o restaurante no banco.

### Isolação por camada

| Camada | Mecanismo |
|--------|-----------|
| PostgreSQL | Todas as queries filtradas por `restaurant_id` |
| pgvector | Busca semântica filtrada por `restaurant_id` |
| Redis (memória) | Prefixo `memory:{restaurant_id}:{phone}:{type}` |
| Redis (buffer) | Prefixo `tacto:msg_buffer:{instance_key}:{phone}` |
| TactoClient | Headers `EmpresaId` + `Tacto-Grupo-Empresarial` por chamada |
| JoinClient | Header `instancia = canal_master_id` por chamada |
| AgentContext | Construído com dados específicos do Restaurant carregado |

### Credenciais compartilhadas vs. por restaurante

**Global (única instância para todos):**
- Tacto OAuth2: `TACTO_CLIENT_ID` + `TACTO_CLIENT_SECRET`
- Join: `JOIN_TOKEN_CLIENTE`
- Gemini: `GOOGLE_API_KEY`

**Por restaurante (salvo no banco):**
- `canal_master_id` — chave da instância Join
- `empresa_base_id` — ID da empresa na Tacto
- `chave_grupo_empresarial` — grupo empresarial na Tacto
- `prompt_default` — instruções customizadas para a IA
- `opening_hours` — horários de funcionamento
- `timezone` — timezone local do restaurante
- `menu_url` — link do cardápio para clientes

---

## Stack e Integrações

### Backend

| Tecnologia | Uso |
|-----------|-----|
| Python 3.11+ | Linguagem principal |
| FastAPI | Framework web async |
| Pydantic v2 | Validação e settings |
| SQLAlchemy 2.0 (async) | ORM — apenas na camada de infra |
| Alembic | Migrations |
| httpx | HTTP client async |
| LangChain LCEL | Pipeline do agente de IA |
| langchain-google-genai | Integração Gemini |

### Infraestrutura

| Tecnologia | Porta | Uso |
|-----------|-------|-----|
| PostgreSQL 16 + pgvector | 5433 (dev) | Persistência + busca semântica |
| Redis 7 | 6380 (dev) | Cache, buffer, memória curto/médio prazo |
| uvicorn | 8000 | ASGI server |

### Integrações Externas

#### Join Developer API
- **Propósito:** Enviar/receber mensagens WhatsApp
- **Auth:** `token_cliente` global (header por chamada)
- **Identificação de restaurante:** `instancia` = `canal_master_id`
- **Endpoints usados:** `POST /mensagens/enviartexto`, `POST /mensagens/enviar-presenca`, instâncias

#### Tacto API
- **Propósito:** Cardápio para RAG, dados institucionais (endereço, horários reais)
- **Auth:** OAuth2 client credentials; token cacheado em Redis
- **Identificação de restaurante:** headers `EmpresaId` + `Tacto-Grupo-Empresarial` por chamada
- **Endpoints usados:** `GET /menu/rag-full`, `GET /institucional/wg`

#### Google Gemini
- **Modelo LLM:** `gemini-2.5-flash` (configurável via `LEVEL1_LLM_MODEL`)
- **Modelo Embedding:** `models/embedding-001` (768 dimensões)
- **Observabilidade:** LangSmith tracing via `LANGCHAIN_API_KEY`

---

## Configuração de Ambiente

Copie `.env.example` para `.env` e preencha:

```bash
# Aplicação
APP_NAME=Tacto-System
APP_DEBUG=true
SECRET_KEY=<gerar-com-openssl-rand>

# PostgreSQL
DB_HOST=localhost
DB_PORT=5433
DB_NAME=tacto_db
DB_USER=tacto_user
DB_PASSWORD=<senha>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_PASSWORD=<senha>

# Google Gemini
GOOGLE_API_KEY=<chave>
LEVEL1_LLM_MODEL=gemini-2.5-flash

# LangSmith (opcional — observabilidade)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<chave>
LANGCHAIN_PROJECT=tacto-system

# Tacto API
TACTO_API_BASE_URL=https://api-externa.tactonuvem.com.br
TACTO_AUTH_URL=https://accounts.tactonuvem.com.br/connect/token
TACTO_CLIENT_ID=<client_id>
TACTO_CLIENT_SECRET=<client_secret>
TACTO_CHAVE_ORIGEM=<chave>

# Join Developer API
JOIN_API_BASE_URL=https://api-prd.joindeveloper.com.br
JOIN_TOKEN_CLIENTE=<token>
```

---

## Como Rodar Localmente

```bash
# 1. Criar e ativar virtualenv
python3.11 -m venv venv
source venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar .env
cp .env.example .env
# Editar .env com credenciais

# 4. Subir PostgreSQL + Redis
docker-compose up -d postgres redis

# 5. Rodar migrations
alembic upgrade head

# 6. Iniciar API
uvicorn tacto.main:app --reload --port 8000

# 7. Verificar saúde
curl http://localhost:8000/health
curl http://localhost:8000/ready

# 8. Docs interativos (apenas em debug=true)
open http://localhost:8000/docs
```

---

## Como Adicionar Novo Restaurante

```bash
# 1. Criar o restaurante no sistema
curl -X POST http://localhost:8000/api/v1/restaurants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Restaurante XYZ",
    "prompt_default": "Seja cordial e foque em pizzas artesanais.",
    "menu_url": "https://cardapio.restaurante.xyz",
    "canal_master_id": "<chave-instancia-join>",
    "empresa_base_id": "<empresa-id-tacto>",
    "chave_grupo_empresarial": "<grupo-uuid-tacto>",
    "timezone": "America/Sao_Paulo",
    "opening_hours": {
      "monday": {"open": "11:00", "close": "23:00"},
      "tuesday": {"open": "11:00", "close": "23:00"},
      ...
    }
  }'

# 2. Configurar webhook no Join para a instância
curl -X POST http://localhost:8000/api/v1/instances/<canal_master_id>/webhook \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://seu-dominio.com/api/v1/webhook/join"}'

# 3. Sincronizar cardápio (embeddings pgvector)
# Feito automaticamente via use case SyncTactoMenu
# Pode ser chamado manualmente via endpoint de admin (backlog)
```

A partir daí, mensagens WhatsApp recebidas nessa instância Join serão processadas automaticamente pela IA com contexto específico desse restaurante.

---

## Features Implementadas

### Core do Sistema

- [x] **Webhook Join** — recebe mensagens, filtra eventos, detecta fromMe
- [x] **Message Buffer** — Redis 5s, agrupa mensagens rápidas, lock distribuído
- [x] **Detecção de operador humano** — SentMessageTracker (Redis TTL 15s)
- [x] **Desativação de IA por intervenção** — 12h automáticas, reativação automática
- [x] **Verificação de horário** — timezone por restaurante, desativa IA até 10min antes da abertura
- [x] **RAG de cardápio** — pgvector cosine similarity por restaurant_id
- [x] **Dados institucionais** — endereço e horários reais via Tacto API

### IA (Level1Agent)

- [x] **Persona humanizada** — "Maria, atendente do restaurante", nunca revela que é IA
- [x] **Memória 3 níveis** — short (Redis 30min), medium (Redis 24h), long (PostgreSQL + semântica)
- [x] **System prompt dinâmico** — montado por conversa com dados do restaurante
- [x] **Early exits sem LLM** — restaurante fechado e pedido de atendente humano não chamam Gemini
- [x] **Trigger de menu** — detecta palavras de preço/pedido e inclui link do cardápio
- [x] **LangSmith observability** — tracing com restaurant_id e nome como tags
- [x] **LCEL chain** — `ChatGoogleGenerativeAI | StrOutputParser`

### Infraestrutura de Dados

- [x] **PostgreSQL + pgvector** — restaurantes, conversas, mensagens, memórias de longo prazo, embeddings
- [x] **Redis** — memória curto/médio prazo, buffer, locks, tracker de mensagens enviadas, cache Tacto token
- [x] **Alembic migrations** — 001_initial_schema + 002_customer_memories + 003_pgvector

### Multi-tenancy

- [x] **Isolação completa por restaurant_id** em todas as camadas
- [x] **Lookup de restaurante por canal_master_id** — identificação via webhook Join
- [x] **Credenciais Tacto por restaurante** — headers por chamada (empresa_base_id, grupo_empresarial)
- [x] **Instâncias Join por restaurante** — instance_key por chamada

### API REST

- [x] `POST /api/v1/webhook/join` — webhook principal
- [x] `POST /api/v1/restaurants` — criar restaurante
- [x] `GET /api/v1/restaurants` — listar restaurantes
- [x] `GET /api/v1/restaurants/{id}` — buscar por ID
- [x] `PUT /api/v1/restaurants/{id}` — atualizar
- [x] `DELETE /api/v1/restaurants/{id}` — deletar (soft)
- [x] `GET/POST /api/v1/instances/...` — gerenciar instâncias Join (status, QR, webhook)
- [x] `POST /api/v1/chat` — endpoint de teste do agente (sem WhatsApp)
- [x] `GET /health` + `GET /ready`

### DDD (Refactoring — Fases 1–5)

- [x] **FASE 1** — remoção de código morto e arquivos órfãos pré-refactoring
- [x] **FASE 2** — `MemoryManager` movido de `domain/` para `application/services/`
- [x] **FASE 3** — bounded context `ai_assistance` criado no domínio; `Level1Agent` movido para `infrastructure/agents/`
- [x] **FASE 4** — imports de infraestrutura apontam para `domain/ai_assistance/ports/`; pastas obsoletas deletadas
- [x] **FASE 5** — Domain Events (`DomainEvent`, `MessageReceived`, `AIDisabled`, `AIEnabled`, `RestaurantCreated`) implementados com Pending Events pattern

---

## Backlog

### Alta Prioridade

- [ ] **Testes unitários** — domain layer (entities, value objects, prompts)
- [ ] **Testes de integração** — use cases com banco real (pytest-asyncio + testcontainers)
- [ ] **Admin endpoint: sync cardápio** — `POST /api/v1/restaurants/{id}/sync-menu`
- [ ] **Admin endpoint: reativar IA** — `POST /api/v1/conversations/{id}/enable-ai`
- [ ] **Logging estruturado** — structlog com `restaurant_id` em todos os logs

### Média Prioridade

- [ ] **Level2Agent (INTERMEDIATE)** — RAG mais sofisticado, sugestões por perfil do cliente
- [ ] **Dashboard admin** — listar conversas, status de IA por conversa, histórico
- [ ] **Endpoint de métricas** — total de mensagens, taxa de resposta, tokens consumidos por restaurante
- [ ] **Webhook de eventos de domínio** — publicar `AIDisabled`, `MessageReceived` para sistemas externos
- [ ] **Rate limiting** — por restaurante e por instância Join
- [ ] **Circuit breaker** — para TactoClient e JoinClient

### Baixa Prioridade / Futuro

- [ ] **Level3Agent (ADVANCED)** — coleta de pedidos, validação de endereço, integração com Tacto Order
- [ ] **Pagamentos** — integração Asaas para pedidos via WhatsApp
- [ ] **Order Context** — `domain/order/` com `Order`, `OrderItem`, `OrderStatus`
- [ ] **Notificações** — status do pedido via WhatsApp
- [ ] **Relatórios** — export de conversas, análise de satisfação
- [ ] **Multi-idioma** — inglês para restaurantes turísticos

---

## Referências

### Documentação Interna

- [`docs/ddd-refactoring-plan.md`](./ddd-refactoring-plan.md) — plano detalhado das 5 fases do refactoring DDD (todas concluídas)
- [`docs/excellence-review-plan.md`](./excellence-review-plan.md) — plano de revisão de excelência (auditoria, multi-tenant, AI, docs)
- [`docs/api-externa-tacto.md`](./api-externa-tacto.md) — especificação da Tacto API
- [`docs/join-integration.md`](./join-integration.md) — especificação da Join Developer API

### Livros e Metodologias

- **Domain-Driven Design** — Eric Evans (2003)
- **Implementing Domain-Driven Design** — Vaughn Vernon (2013)
- **Clean Architecture** — Robert C. Martin (2017)
- **Architecture Patterns with Python** — Harry Percival & Bob Gregory (2020)

### Documentação Externa

- [Tacto API Swagger](https://api-externa.tactonuvem.com.br/swagger/index.html)
- [Join Developer API](https://documenter.getpostman.com/view/20242264/2sAXjDdEpW)
- [Google Gemini API](https://ai.google.dev/docs)
- [pgvector](https://github.com/pgvector/pgvector)
- [LangChain LCEL](https://python.langchain.com/docs/expression_language/)

---

**Mantido por:** Loboprogramming
**Última Revisão:** 2026-03-28
