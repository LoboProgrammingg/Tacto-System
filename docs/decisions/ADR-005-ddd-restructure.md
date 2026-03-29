# ADR-005: Reestruturação DDD e Clean Architecture

**Data:** 2026-03-29  
**Status:** ✅ Implemented  
**Data de Implementação:** 2026-03-29  
**Autores:** Engineering Team  
**Referências:** Eric Evans (DDD), Robert C. Martin (Clean Architecture), Vaughn Vernon (Implementing DDD)

## Implementation Summary

A reestruturação foi implementada com sucesso em 5 commits:

| Commit | Fase | Descrição |
|--------|------|-----------|
| `ef17706` | 1 | Criar `shared/` kernel com shims |
| `221d975` | 2 | Mover ports para `application/ports/` |
| `b3ba901` | 3 | Mover prompts para `infrastructure/ai/prompts/` |
| `c28a363` | 4 | Criar `interfaces/http/schemas/` |
| (final) | 5 | Migrar todos imports e remover shims |

### Estrutura Final Implementada

```
tacto/
├── shared/                          # ✅ Shared Kernel
│   ├── domain/                      # Value Objects, Events, Exceptions
│   ├── application/                 # Result types (Ok, Err, Success, Failure)
│   └── infrastructure/              # (placeholder)
│
├── application/
│   ├── ports/                       # ✅ Interfaces para Infrastructure
│   │   ├── agent_port.py
│   │   ├── ai_client.py
│   │   ├── embedding_client.py
│   │   ├── menu_provider.py
│   │   ├── messaging_client.py
│   │   └── vector_store.py
│   ├── dto/
│   └── use_cases/
│
├── domain/
│   ├── restaurant/
│   ├── messaging/
│   ├── ai_assistance/
│   └── customer_memory/
│
├── infrastructure/
│   ├── ai/
│   │   ├── prompts/                 # ✅ Level1Prompts movido para cá
│   │   ├── gemini_client.py
│   │   └── ...
│   └── ...
│
└── interfaces/
    └── http/
        ├── schemas/                 # ✅ Pydantic API models
        │   ├── restaurant.py
        │   ├── chat.py
        │   ├── instance.py
        │   └── webhook.py
        └── routes/
```

---

---

## 1. Contexto

O projeto Tacto-System precisa de uma reorganização para seguir fielmente os princípios de **Domain-Driven Design (Eric Evans)** e **Clean Architecture (Uncle Bob)**. A estrutura atual tem alguns problemas de organização e violações sutis dos princípios.

---

## 2. Análise da Estrutura Atual

```
tacto/
├── application/
│   ├── dto/
│   ├── services/
│   └── use_cases/
├── config/
├── domain/
│   ├── ai_assistance/
│   │   ├── ports/          ← ⚠️ PROBLEMA: Ports devem estar na raiz ou em application
│   │   ├── prompts/        ← ⚠️ PROBLEMA: Prompts são infra/templates
│   │   └── value_objects/
│   ├── customer_memory/
│   ├── messaging/
│   │   ├── entities/
│   │   ├── events/
│   │   ├── repository.py   ← ⚠️ PROBLEMA: Deveria ser uma interface/port
│   │   ├── services/
│   │   └── value_objects/
│   ├── restaurant/
│   │   ├── entities/
│   │   ├── events/
│   │   ├── repository.py   ← ⚠️ PROBLEMA: Deveria ser uma interface/port
│   │   ├── services/
│   │   └── value_objects/
│   └── shared/             ← ✅ BOM: Shared Kernel existe
│       ├── events/
│       ├── exceptions.py
│       ├── result.py
│       └── value_objects/
├── infrastructure/
│   ├── agents/             ← ⚠️ PROBLEMA: Agents são use cases ou domain services
│   ├── ai/
│   ├── circuit_breaker.py  ← ✅ OK: Pattern de infra
│   ├── config/
│   ├── database/
│   ├── external/
│   ├── messaging/
│   ├── persistence/        ← ⚠️ PROBLEMA: Duplicado com database/
│   ├── redis/
│   └── vector_store/       ← ⚠️ PROBLEMA: Movido mas ainda existe shim
├── interfaces/
│   ├── http/
│   │   ├── dependencies.py ← ⚠️ PROBLEMA: DI deveria estar em container/
│   │   └── routes/
│   └── middlewares/
├── container.py            ← ✅ OK: DI container
└── main.py
```

---

## 3. Problemas Identificados

### 3.1 Violações de DDD

| Problema | Localização | Violação |
|----------|-------------|----------|
| Ports dentro de bounded context | `domain/ai_assistance/ports/` | Ports são contratos da Application layer, não Domain |
| Repository como classe concreta | `domain/*/repository.py` | Repository no Domain deve ser INTERFACE, não implementação |
| Prompts no Domain | `domain/ai_assistance/prompts/` | Templates são Infrastructure, não regras de negócio |
| Agents em Infrastructure | `infrastructure/agents/` | Agents orquestram lógica, pertencem a Application |

### 3.2 Violações de Clean Architecture

| Problema | Localização | Violação |
|----------|-------------|----------|
| Dependencies em Interfaces | `interfaces/http/dependencies.py` | Composição de dependências pertence ao Composition Root |
| Config duplicado | `config/` e `infrastructure/config/` | Configuração deve ter um único local |
| Persistence duplicado | `infrastructure/persistence/` e `infrastructure/database/` | Redundância de responsabilidade |

### 3.3 Estruturais

| Problema | Descrição |
|----------|-----------|
| Falta `shared/` global | Shared deveria estar na raiz, não só dentro de domain |
| Falta separação de ports/adapters | Ports (interfaces) misturados com adapters (implementações) |
| Bounded contexts incompletos | Alguns BCs não têm estrutura consistente |

---

## 4. Princípios DDD (Eric Evans)

### 4.1 Camadas do DDD

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                             │
│  (Controllers, Views, REST endpoints, CLI, WebSockets)          │
├─────────────────────────────────────────────────────────────────┤
│                      APPLICATION                                │
│  (Use Cases, Application Services, DTOs, Commands, Queries)     │
│  - Orquestra domain objects                                     │
│  - Não contém regras de negócio                                 │
│  - Define PORTS (interfaces para infra)                         │
├─────────────────────────────────────────────────────────────────┤
│                        DOMAIN                                   │
│  (Entities, Value Objects, Aggregates, Domain Services,         │
│   Domain Events, Repository Interfaces, Specifications)         │
│  - Coração do sistema                                           │
│  - Regras de negócio PURAS                                      │
│  - ZERO dependências externas                                   │
├─────────────────────────────────────────────────────────────────┤
│                     INFRASTRUCTURE                              │
│  (Repositories impl, External APIs, Database, Cache, Queue)     │
│  - Implementa os PORTS                                          │
│  - Detalhes técnicos                                            │
│  - Frameworks e bibliotecas                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Regra de Dependência

```
Interfaces → Application → Domain ← Infrastructure
                 ↓
         [Dependency Inversion]
                 ↓
    Domain define INTERFACES
    Infrastructure IMPLEMENTA
```

### 4.3 Bounded Contexts

Cada bounded context deve ser **autossuficiente**:

```
bounded_context/
├── __init__.py
├── entities/           # Aggregates e Entities
├── value_objects/      # Value Objects do contexto
├── events/             # Domain Events
├── services/           # Domain Services (lógica entre agregados)
├── repository.py       # INTERFACE do repository (ABC)
├── specifications/     # Specifications/Policies (opcional)
└── exceptions.py       # Exceções específicas do contexto
```

---

## 5. Nova Estrutura Proposta

```
tacto/
├── shared/                         # 🆕 SHARED KERNEL (global)
│   ├── __init__.py
│   ├── domain/                     # Conceitos de domínio compartilhados
│   │   ├── value_objects/          # EntityId, PhoneNumber, etc.
│   │   ├── events/                 # Base classes para eventos
│   │   └── exceptions.py           # DomainException base
│   ├── application/                # Conceitos de aplicação compartilhados
│   │   ├── result.py               # Result[T], Success, Failure
│   │   ├── command.py              # Command base class
│   │   └── query.py                # Query base class
│   └── infrastructure/             # Utils de infra compartilhados
│       ├── logging.py              # Configuração structlog
│       └── datetime.py             # Timezone helpers
│
├── domain/                         # DOMAIN LAYER (Pure Business Logic)
│   ├── __init__.py
│   │
│   ├── restaurant/                 # Bounded Context: Restaurant
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── restaurant.py       # Aggregate Root
│   │   │   └── menu_item.py        # Entity
│   │   ├── value_objects/
│   │   │   ├── business_hours.py
│   │   │   ├── automation_level.py
│   │   │   └── menu_url.py
│   │   ├── events/
│   │   │   ├── restaurant_created.py
│   │   │   └── menu_synced.py
│   │   ├── services/               # Domain Services
│   │   │   └── business_hours_checker.py
│   │   ├── repository.py           # INTERFACE (ABC) - not implementation!
│   │   └── exceptions.py
│   │
│   ├── conversation/               # Bounded Context: Conversation (rename from messaging)
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── conversation.py     # Aggregate Root
│   │   │   └── message.py          # Entity
│   │   ├── value_objects/
│   │   │   ├── message_content.py
│   │   │   └── conversation_state.py
│   │   ├── events/
│   │   │   ├── message_received.py
│   │   │   ├── message_sent.py
│   │   │   └── ai_disabled.py
│   │   ├── services/
│   │   │   └── message_filter.py
│   │   ├── repository.py           # INTERFACE
│   │   └── exceptions.py
│   │
│   └── customer_memory/            # Bounded Context: Customer Memory
│       ├── __init__.py
│       ├── entities/
│       │   └── customer_profile.py
│       ├── value_objects/
│       │   └── preference.py
│       ├── repository.py           # INTERFACE
│       └── exceptions.py
│
├── application/                    # APPLICATION LAYER
│   ├── __init__.py
│   │
│   ├── ports/                      # 🆕 PORTS (interfaces para infra)
│   │   ├── __init__.py
│   │   ├── messaging_client.py     # Interface para WhatsApp
│   │   ├── ai_model.py             # Interface para LLM
│   │   ├── vector_store.py         # Interface para embeddings
│   │   ├── external_api.py         # Interface para Tacto API
│   │   └── cache.py                # Interface para Redis
│   │
│   ├── use_cases/                  # Use Cases (Commands)
│   │   ├── __init__.py
│   │   ├── process_message/
│   │   │   ├── __init__.py
│   │   │   ├── command.py          # ProcessMessageCommand
│   │   │   └── handler.py          # ProcessMessageHandler
│   │   ├── sync_menu/
│   │   │   ├── __init__.py
│   │   │   ├── command.py
│   │   │   └── handler.py
│   │   └── create_restaurant/
│   │       ├── __init__.py
│   │       ├── command.py
│   │       └── handler.py
│   │
│   ├── queries/                    # 🆕 CQRS: Queries
│   │   ├── __init__.py
│   │   ├── get_restaurant.py
│   │   └── search_menu.py
│   │
│   ├── services/                   # Application Services
│   │   ├── __init__.py
│   │   ├── message_buffer.py       # Buffer de mensagens
│   │   └── ai_orchestrator.py      # 🆕 Orquestração de AI (move from infra/agents)
│   │
│   └── dto/                        # Data Transfer Objects
│       ├── __init__.py
│       ├── message_dto.py
│       └── restaurant_dto.py
│
├── infrastructure/                 # INFRASTRUCTURE LAYER (Adapters)
│   ├── __init__.py
│   │
│   ├── persistence/                # Database implementations
│   │   ├── __init__.py
│   │   ├── sqlalchemy/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   ├── models/             # ORM models
│   │   │   │   ├── restaurant_model.py
│   │   │   │   ├── conversation_model.py
│   │   │   │   └── message_model.py
│   │   │   └── repositories/       # Repository implementations
│   │   │       ├── restaurant_repository.py
│   │   │       ├── conversation_repository.py
│   │   │       └── message_repository.py
│   │   ├── redis/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── cache_repository.py
│   │   └── pgvector/
│   │       ├── __init__.py
│   │       └── vector_store.py
│   │
│   ├── external/                   # External API clients
│   │   ├── __init__.py
│   │   ├── join/                   # Join WhatsApp API
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── message_tracker.py
│   │   ├── tacto/                  # Tacto API
│   │   │   ├── __init__.py
│   │   │   └── client.py
│   │   └── gemini/                 # Gemini AI
│   │       ├── __init__.py
│   │       ├── client.py
│   │       └── embeddings.py
│   │
│   ├── resilience/                 # 🆕 Resiliência
│   │   ├── __init__.py
│   │   └── circuit_breaker.py
│   │
│   ├── ai/                         # AI/LLM implementations
│   │   ├── __init__.py
│   │   ├── prompts/                # 🆕 Templates (movido de domain)
│   │   │   ├── system_prompt.py
│   │   │   └── rag_prompt.py
│   │   └── level1_agent.py
│   │
│   └── migrations/                 # Database migrations
│       └── versions/
│
├── interfaces/                     # INTERFACE LAYER (Controllers)
│   ├── __init__.py
│   │
│   ├── http/                       # REST API
│   │   ├── __init__.py
│   │   ├── app.py                  # FastAPI app factory
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── restaurants.py
│   │   │   └── webhooks/
│   │   │       ├── __init__.py
│   │   │       └── join.py
│   │   ├── schemas/                # 🆕 Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── restaurant_schema.py
│   │   │   └── webhook_schema.py
│   │   └── middlewares/
│   │       ├── __init__.py
│   │       ├── logging.py
│   │       └── rate_limit.py
│   │
│   └── cli/                        # 🆕 CLI commands (opcional)
│       └── __init__.py
│
├── config/                         # 🆕 Configuration (único local)
│   ├── __init__.py
│   ├── settings.py                 # Pydantic Settings
│   └── logging.py
│
├── container.py                    # Composition Root (DI)
└── main.py                         # Entry point
```

---

## 6. Regras de Cada Camada

### 6.1 DOMAIN (Coração)

```python
# ✅ PODE conter:
- Entities (com identidade)
- Value Objects (imutáveis, sem identidade)
- Aggregates (cluster de entities)
- Domain Services (lógica entre aggregates)
- Domain Events (fatos do domínio)
- Repository INTERFACES (ABC)
- Specifications/Policies
- Exceções de domínio

# ❌ NÃO PODE conter:
- Imports de frameworks (FastAPI, SQLAlchemy, Redis)
- Imports de infrastructure
- Chamadas HTTP, banco, cache
- Logging (exceto domain events)
- Configurações de ambiente
```

### 6.2 APPLICATION (Orquestração)

```python
# ✅ PODE conter:
- Use Cases / Command Handlers
- Application Services
- DTOs (Data Transfer Objects)
- Ports (interfaces para infra)
- Orquestração de domain objects
- Transações (Unit of Work)

# ❌ NÃO PODE conter:
- Regras de negócio (vai para Domain)
- Detalhes de implementação (vai para Infra)
- HTTP request/response handling (vai para Interfaces)
```

### 6.3 INFRASTRUCTURE (Implementações)

```python
# ✅ PODE conter:
- Implementação de Repository
- Clients de APIs externas
- Configuração de banco
- ORM models
- Cache implementations
- Message queue
- Frameworks e libraries

# ❌ NÃO PODE conter:
- Regras de negócio
- Lógica de orquestração
```

### 6.4 INTERFACES (Entrada/Saída)

```python
# ✅ PODE conter:
- REST Controllers/Routes
- WebSocket handlers
- CLI commands
- Request/Response schemas
- Middlewares
- Serialização/Deserialização

# ❌ NÃO PODE conter:
- Regras de negócio
- Acesso direto a banco
- Lógica de aplicação
```

---

## 7. Shared Kernel

O **Shared Kernel** (pasta `shared/`) contém código que é compartilhado entre bounded contexts:

```python
# shared/domain/value_objects/entity_id.py
from abc import ABC
from uuid import UUID, uuid4

class EntityId(ABC):
    """Base class for all entity identifiers."""
    
    def __init__(self, value: UUID | None = None):
        self._value = value or uuid4()
    
    @property
    def value(self) -> UUID:
        return self._value
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, EntityId):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        return hash(self._value)
```

```python
# shared/application/result.py
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)

class Result(Generic[T]):
    """Functional error handling without exceptions."""
    ...
```

---

## 8. Ports e Adapters (Hexagonal)

### Port (Interface na Application)

```python
# application/ports/messaging_client.py
from abc import ABC, abstractmethod
from tacto.shared.application.result import Result

class MessagingClient(ABC):
    """Port for WhatsApp messaging."""
    
    @abstractmethod
    async def send_message(
        self, instance: str, phone: str, text: str
    ) -> Result[str]:
        """Send message. Returns message_id."""
        ...
    
    @abstractmethod
    async def send_typing(self, instance: str, phone: str) -> Result[None]:
        """Send typing indicator."""
        ...
```

### Adapter (Implementação na Infrastructure)

```python
# infrastructure/external/join/client.py
from tacto.application.ports.messaging_client import MessagingClient

class JoinWhatsAppClient(MessagingClient):
    """Join API implementation of MessagingClient port."""
    
    async def send_message(
        self, instance: str, phone: str, text: str
    ) -> Result[str]:
        # Implementação concreta usando httpx
        ...
```

---

## 9. Plano de Migração

### Fase 1: Criar Estrutura Base
1. Criar pasta `shared/` na raiz
2. Mover `domain/shared/` → `shared/domain/`
3. Criar `shared/application/` e `shared/infrastructure/`

### Fase 2: Reorganizar Domain
1. Renomear `domain/messaging/` → `domain/conversation/`
2. Converter `repository.py` de classe para ABC (interface)
3. Mover `prompts/` de domain → `infrastructure/ai/prompts/`
4. Mover `ports/` de domain → `application/ports/`

### Fase 3: Reorganizar Infrastructure
1. Consolidar `database/` e `persistence/` em `persistence/`
2. Mover `agents/` → `application/services/` ou `infrastructure/ai/`
3. Organizar por tecnologia: `persistence/sqlalchemy/`, `persistence/redis/`
4. Criar `resilience/` para circuit breaker

### Fase 4: Reorganizar Application
1. Criar estrutura de use cases por feature
2. Criar pasta `ports/` com todas interfaces
3. Criar pasta `queries/` para CQRS

### Fase 5: Reorganizar Interfaces
1. Mover `dependencies.py` → `container.py` (composition root)
2. Criar `schemas/` para Pydantic models de request/response
3. Organizar routes por recurso

### Fase 6: Configuração
1. Unificar `config/` e `infrastructure/config/`
2. Garantir que todas configs estão em `config/settings.py`

---

## 10. Decisão

**Aprovar** a reestruturação seguindo esta ADR para garantir:

- ✅ Separação clara de responsabilidades
- ✅ Domain layer 100% puro (zero dependências externas)
- ✅ Inversão de dependência correta
- ✅ Testabilidade (mocks fáceis via ports)
- ✅ Flexibilidade para trocar implementações
- ✅ Código mais legível e manutenível

---

## 11. Consequências

### Positivas
- Código organizado seguindo padrões reconhecidos
- Facilidade de onboarding para novos devs
- Testes unitários mais simples
- Bounded contexts bem definidos
- Fácil evolução do sistema

### Negativas
- Trabalho significativo de refatoração
- Alguns imports vão mudar
- Curva de aprendizado inicial

---

## 12. Referências

1. **Eric Evans** - Domain-Driven Design: Tackling Complexity in the Heart of Software (2003)
2. **Robert C. Martin** - Clean Architecture: A Craftsman's Guide to Software Structure and Design (2017)
3. **Vaughn Vernon** - Implementing Domain-Driven Design (2013)
4. **Alistair Cockburn** - Hexagonal Architecture (Ports & Adapters)
5. **Martin Fowler** - Patterns of Enterprise Application Architecture
