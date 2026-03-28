# 📘 TactoFlow - Contexto Geral do Projeto

**Versão:** 0.0.1  
**Última Atualização:** 2026-03-27  
**Status:** 🚧 Em Desenvolvimento Inicial  
**Arquiteto:** Senior Software Engineer  
**Metodologias:** DDD, Clean Architecture, SOLID, KISS, Clean Code

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Contexto de Negócio](#contexto-de-negócio)
3. [Arquitetura](#arquitetura)
4. [Bounded Contexts](#bounded-contexts)
5. [Integrações Externas](#integrações-externas)
6. [Regras de Negócio Críticas](#regras-de-negócio-críticas)
7. [Stack Tecnológica](#stack-tecnológica)
8. [Status Atual](#status-atual)
9. [Próximos Passos](#próximos-passos)
10. [Referências](#referências)

---

## 🎯 VISÃO GERAL

**TactoFlow** é um sistema backend multi-tenant para automação de atendimento via WhatsApp para restaurantes, utilizando Inteligência Artificial (Gemini) para processar mensagens de clientes, com integração à plataforma Tacto para gerenciamento de cardápios e dados institucionais.

### Objetivos Principais

1. **Receber e processar mensagens** de clientes via WhatsApp através da integração Join Developer
2. **Automatizar respostas** usando IA (Gemini) com contexto específico de cada restaurante
3. **Gerenciar múltiplos restaurantes** em arquitetura multi-tenant interna (não SaaS)
4. **Integrar com API Tacto** para obter cardápio, dados institucionais e validação de endereços
5. **Preparar infraestrutura** para criação de pedidos (feature futura)

### Diferenciais Técnicos

- ✅ **Domain-Driven Design (DDD)** rigoroso seguindo Eric Evans
- ✅ **Clean Architecture** com separação total de camadas
- ✅ **SOLID principles** em toda base de código
- ✅ **Message Buffer** inteligente com Redis para agrupar mensagens
- ✅ **Multi-level Memory** (Redis + PostgreSQL + pgvector)
- ✅ **OAuth2 Token Caching** para otimização de chamadas externas
- ✅ **Strategy Pattern** para diferentes níveis de automação

---

## 🏢 CONTEXTO DE NEGÓCIO

### Problema Resolvido

Restaurantes recebem alto volume de mensagens via WhatsApp e necessitam:
- Responder rapidamente 24/7
- Fornecer informações sobre cardápio e horários
- Manter qualidade no atendimento
- Evitar perda de vendas fora do horário comercial
- Escalar atendimento sem aumentar equipe

### Solução Proposta

Sistema de IA conversacional que:
1. Responde automaticamente clientes via WhatsApp
2. Respeita horário de funcionamento do restaurante
3. Fornece informações institucionais (endereço, horários, formas de pagamento)
4. Sugere cardápio quando apropriado
5. Transfere para humano quando detecta intervenção manual
6. Agrupa mensagens para contextualização melhor

### Modelo de Negócio

**Multi-tenant Interno** (não SaaS):
- Cada restaurante é um tenant
- Compartilham infraestrutura
- Isolamento de dados por `restaurant_id`
- Configuração individual por restaurante

---

## 🏗️ ARQUITETURA

### Princípios Fundamentais

**Domain-Driven Design (DDD)**
```
├── Domain Layer (Core Business Logic)
│   ├── Entities (identidade própria)
│   ├── Value Objects (imutáveis, sem identidade)
│   ├── Aggregates (consistência transacional)
│   ├── Domain Services (lógica que não pertence a entidades)
│   └── Repository Interfaces (contratos, não implementação)
│
├── Application Layer (Use Cases)
│   ├── Use Cases (orquestração de domínio)
│   ├── DTOs (Data Transfer Objects)
│   └── Application Services
│
├── Infrastructure Layer (Detalhes Técnicos)
│   ├── Repository Implementations
│   ├── External API Clients
│   ├── Database Configurations
│   └── Third-party Integrations
│
└── Interface Layer (Entrypoints)
    ├── HTTP (REST API, Webhooks)
    ├── Workers (Background Jobs)
    └── CLI (se necessário)
```

### Camadas e Dependências

```
┌─────────────────────────────────────┐
│     Interface Layer (HTTP/CLI)      │
└────────────┬────────────────────────┘
             │ depends on
             ▼
┌─────────────────────────────────────┐
│     Application Layer (Use Cases)   │
└────────────┬────────────────────────┘
             │ depends on
             ▼
┌─────────────────────────────────────┐
│     Domain Layer (Business Logic)   │ ◄── CORE (sem dependências)
└─────────────────────────────────────┘
             ▲
             │ implements
             │
┌─────────────────────────────────────┐
│  Infrastructure Layer (Tech Details)│
└─────────────────────────────────────┘
```

**Regra de Ouro:** 
- Domínio **NUNCA** depende de infraestrutura
- Infraestrutura **implementa** interfaces definidas no domínio
- Fluxo de dependência: Interface → Application → Domain ← Infrastructure

---

## 🎯 BOUNDED CONTEXTS

Seguindo DDD, o sistema é dividido em contextos delimitados:

### 1. **Restaurant Context**
**Responsabilidade:** Gerenciar dados e configurações de restaurantes

**Entidades:**
- `Restaurant` (Aggregate Root)
- `Integration` (configuração de integração)

**Value Objects:**
- `IntegrationType` (JOIN=1, WHATSAPP_BUSINESS=2)
- `AutomationType` (BASIC=1, INTERMEDIATE=2, ADVANCED=3)
- `OpeningHours` (horários de funcionamento)

**Invariantes:**
- Restaurante deve ter nome único
- Deve ter pelo menos um tipo de integração
- Horários devem ser válidos (abertura < fechamento)

---

### 2. **Messaging Context**
**Responsabilidade:** Gerenciar conversas e mensagens com clientes

**Entidades:**
- `Conversation` (Aggregate Root)
- `Message`

**Domain Services:**
- `MessageBufferService` (agrupa mensagens em 3-5s)

**Invariantes:**
- Mensagens devem pertencer a uma conversa
- `fromMe=true` deve ser ignorado (não processar)
- `source=phone` desativa IA por 12h

---

### 3. **Assistant Context**
**Responsabilidade:** Orquestrar respostas da IA

**Domain Services:**
- `AssistantService` (coordena IA)
- `ResponseOrchestrator` (orquestra fluxo completo)
- `IntentDetectionService` (detecta intenção do usuário)

**Strategies:**
- `BasicStrategy` (apenas informações institucionais + link cardápio)
- `IntermediateStrategy` (institucional + RAG cardápio, sem pedidos) - **NÃO IMPLEMENTAR AGORA**
- `AdvancedStrategy` (tudo + criar pedidos) - **NÃO IMPLEMENTAR AGORA**

**Invariantes:**
- Deve verificar horário antes de processar
- Deve respeitar nível de automação do restaurante
- Fora do horário: retornar apenas horário do dia atual

---

### 4. **Memory Context**
**Responsabilidade:** Gerenciar memória da conversa em múltiplos níveis

**Domain Services:**
- `MemoryService`

**Estratégia Multi-level:**
- **Curto Prazo:** Redis (últimas N mensagens, TTL 1h)
- **Médio Prazo:** PostgreSQL (histórico conversas, 30 dias)
- **Longo Prazo:** pgvector (embeddings para RAG, permanente)

**Invariantes:**
- Memória deve ser isolada por restaurante
- Embeddings devem incluir metadata (restaurant_id, timestamp)

---

### 5. **Order Context**
**Responsabilidade:** Gerenciar pedidos (FUTURA - não priorizar agora)

**Entidades:**
- `Order` (Aggregate Root)
- `OrderItem`

**Status:** 🔮 Planejado para futuro

---

## 🔌 INTEGRAÇÕES EXTERNAS

### 1. **Join Developer API**

**Propósito:** Enviar/receber mensagens WhatsApp

**Base URL:** `https://api-prd.joindeveloper.com.br`

**Autenticação:** Token Cliente fixo
```
JOIN_TOKEN_CLIENTE=2221f6c4-c045-45cb-a745-aa494c761fba
```

**Endpoints Principais:**
- `POST /sendMessage` - Enviar mensagem
- `POST /sendPresence` - Simular digitação (composing/paused)
- `GET /init` - Criar instância
- `GET /qrcode?key={instance_key}` - Obter QR Code
- `GET /status?key={instance_key}` - Status da instância
- **Webhook:** Recebe mensagens via POST (configurar URL)

**Payloads Críticos:**

Webhook recebido:
```json
{
  "from": "5511999999999@c.us",
  "body": "Olá, quero fazer um pedido",
  "fromMe": false,
  "source": "app",
  "timestamp": 1234567890
}
```

**Regras de Processamento:**
- `fromMe=true` → **IGNORAR** (mensagem enviada pelo próprio número)
- `source=phone` → **DESATIVAR IA por 12h** (humano assumiu)
- Buffer: agrupar mensagens com < 5s de diferença

**Documentação:** https://documenter.getpostman.com/view/20242264/2sAXjDdEpW

---

### 2. **Tacto API Externa**

**Propósito:** Obter cardápio, dados institucionais e validar endereços

**Base URL:** `https://api-externa.tactonuvem.com.br`

**Swagger:** https://api-externa.tactonuvem.com.br/swagger/index.html

**Autenticação:** OAuth2 Client Credentials Flow

**Token Endpoint:** `https://accounts.tactonuvem.com.br/connect/token`

**Credenciais:**
```
client_id: integracao-externa
client_secret: d59883992608430081c5a632b0619826
grant_type: client_credentials
scope: (None/default)
```

**Headers Obrigatórios (TODAS as requests):**
```
Authorization: Bearer {token}
chave-origem: DA885FE3-44F8-46FE-BC8B-EF709F4EC2AA
Tacto-Grupo-Empresarial: {chave_grupo_empresarial}
EmpresaId: {empresa_base_id}
GrupoEmpresaId: {empresa_base_id}
Tacto-Grupo-Empresa-Id: {chave_grupo_empresarial}
```

**Endpoints Planejados:**
- `GET /menu/rag-full` → Cardápio completo para RAG
- `GET /institucional/wg` → Dados institucionais simplificados
- `POST /enderecos/validar` → Validar endereço de entrega

**Estratégia de Token:**
- Cache em Redis com TTL baseado em `expires_in`
- Renovar automaticamente 5min antes de expirar
- Retry com backoff exponencial em caso de 401

---

### 3. **Google Gemini AI**

**Propósito:** Processar mensagens e gerar respostas contextualizadas

**Modelo:** `gemini-2.5-flash`

**API Key:** `AIzaSyCj5TuZdgy8rmK5fCAyBoehwELfsDYBa8I`

**Embedding Model:** `models/embedding-001` (768 dimensões)

**Inputs para IA:**
1. `prompt_default` do restaurante
2. Contexto da conversa (últimas N mensagens)
3. Dados institucionais (da Tacto API)
4. Cardápio (se aplicável ao nível de automação)
5. `menu_url` para sugestão

**Output Esperado:**
- Texto da resposta
- Metadados (confiança, intenção detectada)

---

### 4. **Redis**

**Propósito:** Cache, buffer de mensagens, memória de curto prazo

**Uso:**
- **Message Buffer:** Armazenar mensagens temporariamente (5s TTL)
- **Token Cache:** OAuth2 tokens da Tacto API
- **Session State:** Estado da conversa ativa
- **AI State Toggle:** Controle se IA está ativa por conversa
- **Short-term Memory:** Últimas 10 mensagens (1h TTL)

---

### 5. **PostgreSQL + pgvector**

**Propósito:** Persistência e busca semântica

**Uso:**
- **Persistência:** Restaurantes, conversas, mensagens, pedidos
- **pgvector:** Embeddings para RAG (busca semântica em cardápio e histórico)

---

## ⚠️ REGRAS DE NEGÓCIO CRÍTICAS

### 1. Controle de Horário de Funcionamento

**Regra:** Se restaurante estiver fechado no momento da mensagem:
```python
# ❌ ERRADO
"Estamos fechados. Funcionamos de segunda a sexta das 11h às 23h"

# ✅ CORRETO
"Estamos fechados no momento. Hoje abrimos às 18h"
```

**Implementação:**
- Verificar horário ANTES de chamar IA
- Retornar apenas horário do **dia atual**
- Não processar pedidos fora do horário
- Permitir consultas institucionais mesmo fechado

---

### 2. Níveis de Automação (Strategy Pattern)

#### **BASIC (PRIORIDADE - IMPLEMENTAR AGORA)**

**Pode fazer:**
- ✅ Recepcionar cliente com cordialidade
- ✅ Fornecer informações institucionais (endereço, telefone, horários, formas de pagamento)
- ✅ Sugerir link do cardápio (evitar repetir sem cliente perguntar)
- ✅ Informar horário de funcionamento

**NÃO pode fazer:**
- ❌ Passar informações de produtos do cardápio
- ❌ Anotar pedidos
- ❌ Processar pagamentos

**RAG:** Apenas dados institucionais (endereço, horários, etc.)

---

#### **INTERMEDIATE (NÃO IMPLEMENTAR AGORA)**

**Adiciona:**
- ✅ RAG com cardápio completo
- ✅ Responder perguntas sobre produtos
- ✅ Sugerir combos/promoções

**Continua NÃO fazendo:**
- ❌ Anotar pedidos

---

#### **ADVANCED (NÃO IMPLEMENTAR AGORA)**

**Adiciona:**
- ✅ Anotar pedidos completos
- ✅ Validar endereço de entrega
- ✅ Calcular frete
- ✅ Integrar com sistema de pagamento

---

### 3. Buffer de Mensagens Inteligente

**Problema:**
```
[10:00:00] Cliente: "Oi"
[10:00:02] Cliente: "Tudo bem?"
[10:00:04] Cliente: "Quero fazer um pedido"
```

**Sem buffer:** 3 respostas separadas (ruim)

**Com buffer:** 1 resposta contextualizada
```
IA: "Olá! Tudo bem sim, obrigado por perguntar! 😊 
Fico feliz em ajudar com seu pedido. 
Você pode conferir nosso cardápio completo aqui: [link]"
```

**Implementação:**
- Timer de 3-5 segundos
- Cada mensagem nova **reseta** o timer
- Ao expirar: concatena todas mensagens e processa
- Usar Redis para coordenação

---

### 4. Controle de Intervenção Humana

**Regra:** Se humano (funcionário) responder pelo telefone:

```python
if message.get("source") == "phone":
    # Desativa IA por 12 horas
    redis.setex(f"ai_disabled:{chat_id}", 43200, "true")
    return  # Não processar
```

**Reativação:**
- Automática após 12h
- Manual via endpoint administrativo

---

### 5. Filtros de Conteúdo

**Proibições:**
- ❌ Palavrões ou linguagem ofensiva
- ❌ Mencionar ou sugerir concorrentes
- ❌ Gírias informais excessivas
- ❌ Informações falsas sobre produtos

**Tom de Voz:**
- ✅ Formal mas amigável
- ✅ Emojis com moderação (1-2 por mensagem)
- ✅ Respostas claras e diretas

---

### 6. Multi-tenancy

**Princípio:** TODO o sistema é isolado por `restaurant_id`

```python
# ❌ ERRADO - consulta global
messages = db.query(Message).all()

# ✅ CORRETO - sempre filtrar por tenant
messages = db.query(Message).filter(
    Message.restaurant_id == restaurant_id
).all()
```

**Aplicar em:**
- Queries de banco de dados
- Cache (incluir restaurant_id na chave)
- Logs (sempre logar restaurant_id)
- Métricas e observabilidade

---

## 🛠️ STACK TECNOLÓGICA

### Backend Core
- **Python 3.11+** (tipagem forte obrigatória)
- **FastAPI** (framework web assíncrono)
- **Pydantic v2** (validação e serialização)
- **dependency-injector** (DI container)

### Banco de Dados
- **PostgreSQL 16+** (persistência)
- **pgvector** (busca semântica)
- **Alembic** (migrations)
- **SQLAlchemy 2.0** (ORM - apenas infraestrutura)

### Cache & Queue
- **Redis 7+** (cache, buffer, session)
- **asyncio** (processamento assíncrono)

### IA & ML
- **google-generativeai** (Gemini SDK)
- **langchain** (RAG pipeline - considerar)

### HTTP Clients
- **httpx** (async HTTP client)
- **aiohttp** (alternativa)

### Observabilidade
- **structlog** (structured logging)
- **prometheus_client** (métricas - futuro)
- **opentelemetry** (tracing - futuro)

### Desenvolvimento
- **pytest** + **pytest-asyncio** (testes)
- **black** (formatação)
- **isort** (imports)
- **mypy** (type checking)
- **ruff** (linting)

### Infraestrutura
- **Docker** + **Docker Compose**
- **uvicorn** (ASGI server)

---

## 📊 STATUS ATUAL

### ✅ Concluído

- [x] Estrutura de pastas DDD criada
- [x] Arquivos boilerplate gerados
- [x] Documentação de integrações coletada
- [x] Credenciais de APIs obtidas
- [x] `.env` e `.env.example` configurados
- [x] **Configuração Pydantic Settings** (App, Database, Redis, APIs)
- [x] **Shared Kernel** (Result Monad, Exceptions, Value Objects base)
- [x] **Restaurant Context** (Entities, VOs, Repository Interface)
- [x] **Messaging Context** (Conversation, Message, Repositories)
- [x] **Assistant Context** (Ports, Strategies, ResponseOrchestrator)
- [x] **Infrastructure - Database** (SQLAlchemy models, connection management)
- [x] **Infrastructure - Redis** (Async client with typed operations)
- [x] **Infrastructure - External APIs** (Gemini, Join, Tacto clients)
- [x] **Docker Compose** para desenvolvimento (PostgreSQL:5433 + pgvector, Redis:6380)
- [x] **Main.py** com FastAPI e lifecycle management
- [x] **DI Container** para injeção de dependências
- [x] **Repository Implementations** (PostgreSQL) - RestaurantRepository, ConversationRepository, MessageRepository
- [x] **Application Layer - DTOs** (IncomingMessageDTO, CreateRestaurantDTO, etc.)
- [x] **Application Layer - Use Cases** (ProcessIncomingMessageUseCase, CreateRestaurantUseCase)
- [x] **Interfaces Layer - Webhook** (Join webhook handler com background processing)
- [x] **Interfaces Layer - HTTP Routes** (Restaurant CRUD routes)
- [x] **Dependencies** (FastAPI dependency injection para use cases)
- [x] **Alembic Migrations** (001_initial_schema.py com restaurants, conversations, messages)
- [x] **Message Buffer Service** (Domain + Redis implementation)
- [x] **Menu Provider** (TactoMenuProvider com cache Redis)
- [x] **Docker Production Setup** (Dockerfile.prod, docker-compose.prod.yml, Nginx)
- [x] **AI Agent Level 1 (BASIC)** - LangChain + Gemini, humanizado, multi-tenant
- [x] **Memory System** - 3 níveis (short/medium Redis, long PostgreSQL)
- [x] **Join Instance Management** - Endpoints para criar, listar, conectar, configurar webhook
- [x] **Migration 002** - customer_memories table para memória de longo prazo

### 🚧 Em Andamento

- [ ] Testes unitários e de integração
- [ ] AI Agents Level 2-4 (futuro)

### 📋 Backlog Próximos Sprints

**Sprint 1 - Testing**
- [ ] Unit tests (domain layer)
- [ ] Integration tests (infrastructure)
- [ ] E2E tests (use cases)

**Sprint 2 - Polish**
- [ ] Logging e observabilidade avançado
- [ ] Documentation final

---

## 📁 ARQUIVOS IMPLEMENTADOS (Sessão Atual)

### Infrastructure Layer - Persistence
- `tacto/infrastructure/persistence/__init__.py`
- `tacto/infrastructure/persistence/restaurant_repository.py` - PostgresRestaurantRepository
- `tacto/infrastructure/persistence/conversation_repository.py` - PostgresConversationRepository
- `tacto/infrastructure/persistence/message_repository.py` - PostgresMessageRepository

### Application Layer
- `tacto/application/__init__.py`
- `tacto/application/dto/__init__.py`
- `tacto/application/dto/message_dto.py` - IncomingMessageDTO, OutgoingMessageDTO, MessageResponseDTO
- `tacto/application/dto/restaurant_dto.py` - CreateRestaurantDTO, RestaurantResponseDTO
- `tacto/application/use_cases/__init__.py`
- `tacto/application/use_cases/create_restaurant.py` - CreateRestaurantUseCase
- `tacto/application/use_cases/process_incoming_message.py` - ProcessIncomingMessageUseCase (CORE)

### Interfaces Layer
- `tacto/interfaces/__init__.py`
- `tacto/interfaces/http/__init__.py`
- `tacto/interfaces/http/dependencies.py` - FastAPI dependency injection
- `tacto/interfaces/http/routes/__init__.py`
- `tacto/interfaces/http/routes/webhook_join.py` - Join webhook handler
- `tacto/interfaces/http/routes/restaurants.py` - Restaurant CRUD routes

### Database Migrations
- `alembic.ini`
- `tacto/infrastructure/database/migrations/env.py`
- `tacto/infrastructure/database/migrations/script.py.mako`
- `tacto/infrastructure/database/migrations/versions/001_initial_schema.py`

### Message Buffer Service
- `tacto/domain/messaging/services/__init__.py`
- `tacto/domain/messaging/services/message_buffer_service.py` - MessageBufferService, MessageBufferPort
- `tacto/infrastructure/redis/__init__.py`
- `tacto/infrastructure/redis/message_buffer.py` - RedisMessageBuffer

### AI Agent System (Multi-Tenant, Multi-Level)
- `tacto/domain/ai/__init__.py` - AI Domain exports
- `tacto/domain/ai/agents/__init__.py` - Agent exports
- `tacto/domain/ai/agents/base_agent.py` - BaseAgent, AgentContext, AgentResponse
- `tacto/domain/ai/agents/level1_agent.py` - Level1Agent (BASIC) com LangChain + Gemini
- `tacto/domain/ai/memory/__init__.py` - Memory exports
- `tacto/domain/ai/memory/memory_manager.py` - MemoryManager, MemoryPort, ConversationMemory
- `tacto/domain/ai/prompts/__init__.py` - Prompts exports
- `tacto/domain/ai/prompts/level1_prompts.py` - Level1Prompts (humanizado, menu triggers)

### AI Memory Infrastructure
- `tacto/infrastructure/ai/__init__.py` - AI infrastructure exports
- `tacto/infrastructure/ai/redis_memory.py` - RedisMemoryAdapter (short/medium term)
- `tacto/infrastructure/ai/postgres_memory.py` - PostgresMemoryAdapter (long term)

### Join Instance Management
- `tacto/infrastructure/messaging/__init__.py` - Messaging exports
- `tacto/infrastructure/messaging/join_instance_manager.py` - JoinInstanceManager, JoinInstance
- `tacto/interfaces/http/routes/instances.py` - Instance CRUD routes

### Database Migrations (Adicionais)
- `tacto/infrastructure/database/migrations/versions/002_customer_memories.py` - customer_memories table

---

## 🎯 PRÓXIMOS PASSOS IMEDIATOS

### 1. Completar Documentação (HOJE)
- [x] `project-context.md` (este arquivo)
- [ ] `architecture.md` - Arquitetura DDD detalhada
- [ ] `business-rules.md` - Regras de negócio expandidas
- [ ] `api-specification.md` - Endpoints REST
- [ ] `database-schema.md` - Tabelas e relacionamentos
- [ ] `backlog.md` - Product backlog detalhado
- [ ] `decisions/ADR-001-ddd-architecture.md`
- [ ] `decisions/ADR-002-message-buffer-strategy.md`
- [ ] `decisions/ADR-003-multi-level-memory.md`

### 2. Setup Inicial do Projeto
```bash
# Criar virtualenv
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editar .env com credenciais reais

# Iniciar PostgreSQL + Redis via Docker
docker-compose up -d postgres redis

# Rodar migrations
alembic upgrade head

# Iniciar servidor de desenvolvimento
uvicorn tacto.main:app --reload
```

### 3. Primeiro Endpoint Funcional
- [ ] Implementar `POST /api/v1/webhooks/join` (receber mensagens)
- [ ] Implementar `POST /api/v1/restaurants` (criar restaurante)
- [ ] Implementar `GET /health` (health check)

---

## 📚 REFERÊNCIAS

### Livros
- **Domain-Driven Design** - Eric Evans (2003)
- **Implementing Domain-Driven Design** - Vaughn Vernon (2013)
- **Clean Architecture** - Robert C. Martin (2017)
- **Architecture Patterns with Python** - Harry Percival & Bob Gregory (2020)

### Documentação Externa
- [Tacto API Swagger](https://api-externa.tactonuvem.com.br/swagger/index.html)
- [Join Developer API](https://documenter.getpostman.com/view/20242264/2sAXjDdEpW)
- [Google Gemini API](https://ai.google.dev/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [pgvector Docs](https://github.com/pgvector/pgvector)

### Documentação Interna
- [`docs/api-externa-tacto.md`](./api-externa-tacto.md) - Especificação Tacto API
- [`docs/join-integration.md`](./join-integration.md) - Especificação Join API
- [`docs/multi-tenant.md`](./multi-tenant.md) - Estratégia multi-tenant

---

## 📝 CHANGELOG

### [0.0.1] - 2026-03-27

#### Added
- Documentação inicial do projeto
- Estrutura de pastas DDD
- Configuração de ambiente
- Credenciais de APIs externas

#### Context
- Projeto em fase de **inception**
- Foco inicial: documentação e arquitetura
- Próximo milestone: implementação do core domain

---

**Mantido por:** Engineering Team  
**Contato:** [interno]  
**Última Revisão:** 2026-03-27  
**Próxima Revisão:** A cada sprint (quinzenal)
