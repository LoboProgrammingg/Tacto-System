# Plano de Refatoração DDD — Tacto-System
**Autor:** Engineering Standards
**Data:** 2026-03-28 | **Revisado:** 2026-03-28
**Baseado em:** Domain-Driven Design (Eric Evans, 2003) + Clean Architecture (Robert Martin)

> **Princípio absoluto (Evans):** A Camada de Domínio contém APENAS lógica de negócio pura. Zero I/O, zero frameworks, zero APIs externas, zero Redis, zero Postgres. Qualquer coisa que toque infraestrutura pertence à Infra ou Aplicação.

---

## 1. Diagnóstico — Violações de Camada

### 1.1 CRÍTICO — `MemoryManager` no Domínio com responsabilidade de Infraestrutura
`domain/ai/memory/memory_manager.py` orquestra Redis + PostgreSQL diretamente. Isso é um **Serviço de Aplicação** (orquestra I/O), não um Domain Service.

- **Fica no Domínio:** `MemoryPort` (interface pura), `MemoryEntry` (Value Object), `ConversationMemory` (Value Object)
- **Sai do Domínio → `application/services/`:** `MemoryManager` (renomear para `MemoryOrchestrationService`)
- **Fica na Infra:** `RedisMemoryAdapter`, `PostgresMemoryAdapter` (implementações dos ports)

### 1.2 CRÍTICO — Execução de Agentes de IA no Domínio
`domain/ai/agents/level1_agent.py` realiza chamadas a APIs LLM externas. A Camada de Domínio nunca faz I/O de rede.

- **Fica no Domínio:** `AgentContext` (VO), `AgentResponse` (VO), `level1_prompts.py` (lógica pura de construção de prompt), ports: `AIClient`, `EmbeddingClient`, `VectorStore`, `MessagingClient`, `MenuProvider`
- **Sai do Domínio → `infrastructure/agents/`:** `Level1Agent`, `BaseAgent` (executam chamadas LLM)
- **Sai do Domínio → `application/services/`:** `AgentExecutionService` (orquestra a execução)

### 1.3 CRÍTICO — Dead Code com imports quebrados

| Arquivo | Status | Problema |
|---|---|---|
| `domain/assistant/strategies/*.py` | **ÓRFÃO** | Nunca chamados — substituídos por `Level1Agent` |
| `domain/assistant/services/response_orchestrator.py` | **ÓRFÃO** | Nunca instanciado no `dependencies.py` |
| `domain/assistant/services/assistant_service.py` | **ÓRFÃO** | Stub vazio, import quebrado (`from domain.shared...`) |
| `domain/memory/repository.py` | **ÓRFÃO** | Import quebrado, substituído por `MemoryPort` |
| `domain/memory/services/memory_service.py` | **SUSPEITO** | Verificar com grep |
| `domain/messaging/services/message_buffer_service.py` | **ÓRFÃO** | Duplicado — versão ativa em `application/services/` |
| `infrastructure/persistence/postgres/` | **ÓRFÃO** | Pasta duplica repositórios da raiz |

### 1.4 GRAVE — Dois contextos de IA paralelos sem integração
`domain/assistant/` e `domain/ai/` coexistem. `domain/memory/` e `domain/ai/memory/` duplicados.

### 1.5 MODERADO — Ports com assinaturas que vazam tecnologia
Alguns ports retornam `list[dict]` (vaza JSON/Postgres) em vez de Value Objects do domínio. Ports devem expressar contratos de **negócio puro**.

---

## 2. Modelo de Camadas Correto

```
┌────────────────────────────────────────────────────────────┐
│                    INTERFACES LAYER                        │
│  HTTP Routes, Webhooks, Workers                            │
│  → Recebe requests, converte para DTOs, delega             │
└──────────────────────────┬─────────────────────────────────┘
                           │ DTOs
┌──────────────────────────▼─────────────────────────────────┐
│                  APPLICATION LAYER                         │
│  Use Cases: orquestram fluxos de negócio                   │
│  Application Services: coordenam múltiplos domínios        │
│  → MemoryOrchestrationService  (Redis + Postgres memory)   │
│  → AgentExecutionService       (executa Level1Agent)       │
│  → MessageBufferService ✅     (já está aqui)              │
└──────────────────────────┬─────────────────────────────────┘
                           │ Domain Objects
┌──────────────────────────▼─────────────────────────────────┐
│               DOMAIN LAYER  ← NÚCLEO PURO                  │
│  Entities, Value Objects, Domain Services (stateless)      │
│  Repository Interfaces (Ports de Persistência)             │
│  Ports para serviços externos (AIClient, etc.)             │
│  Domain Events                                             │
│  REGRA: zero imports de infra, zero I/O, zero frameworks   │
└──────────────────────────┬─────────────────────────────────┘
                           │ implementa Ports
┌──────────────────────────▼─────────────────────────────────┐
│               INFRASTRUCTURE LAYER                         │
│  PostgreSQL, Redis, Gemini, Join API, Tacto API            │
│  Adapters que implementam contratos do Domínio             │
│  → GeminiClient implements AIClient                        │
│  → JoinClient implements MessagingClient                   │
│  → RedisMemoryAdapter implements MemoryPort                │
│  → Level1Agent (execução LLM) vive aqui                    │
└────────────────────────────────────────────────────────────┘
```

---

## 3. Bounded Contexts

| Context | Aggregate Root | O que fica no Domínio | O que sai |
|---|---|---|---|
| **Restaurant** | `Restaurant` | `Restaurant` (root), `Integration` (filha), VOs, `RestaurantRepository` port | `PostgresRestaurantRepository` (infra) |
| **Messaging** | `Conversation` | `Conversation` (root), `Message` (filha), VOs, `ConversationRepository` port | `PostgresConversationRepository` (infra) |
| **AI Assistance** | — | `AgentContext` VO, `AgentResponse` VO, prompts (lógica pura), ports: `AIClient`, `EmbeddingClient`, `VectorStore`, `MessagingClient`, `MenuProvider` | `Level1Agent` → infra; `AgentExecutionService` → application |
| **Customer Memory** | — | `MemoryEntry` VO, `ConversationMemory` VO, `MemoryPort` interface | `MemoryOrchestrationService` → application; `RedisMemoryAdapter`, `PostgresMemoryAdapter` → infra |
| **Ordering** | `Order` | `Order` (root), `OrderItem` (filha), `OrderRepository` port | implementação futura |

> **Sobre Aggregates e a pasta `entities/`:** Segundo Evans, o Aggregate Root *é uma Entidade*. Não existe pasta `aggregates/` separada. A raiz e suas entidades filhas ficam **juntas em `entities/`**, no mesmo módulo. A distinção é lógica (quem é root vs. filha), não estrutural.

---

## 4. Estrutura de Pastas Target

```
tacto/
├── config/
│   └── settings.py                        # ✅ mantém
│
├── domain/                                # NÚCLEO PURO — zero imports de infra
│   ├── restaurant/
│   │   ├── entities/
│   │   │   ├── restaurant.py              # ✅ Aggregate Root
│   │   │   └── integration.py             # ✅ Entity filha
│   │   ├── value_objects/
│   │   │   ├── opening_hours.py
│   │   │   ├── automation_type.py
│   │   │   └── integration_type.py
│   │   ├── events/                        # 🆕
│   │   │   └── restaurant_created.py
│   │   └── repository.py                  # ✅ interface pura
│   │
│   ├── messaging/
│   │   ├── entities/
│   │   │   ├── conversation.py            # ✅ Aggregate Root
│   │   │   └── message.py                 # ✅ Entity filha
│   │   ├── value_objects/
│   │   │   ├── message_direction.py
│   │   │   └── message_source.py
│   │   ├── events/                        # 🆕
│   │   │   ├── message_received.py
│   │   │   ├── ai_disabled.py
│   │   │   └── ai_enabled.py
│   │   └── repository.py                  # ✅ interface pura
│   │
│   ├── ai_assistance/                     # 🆕 (unifica domain/assistant/ + domain/ai/)
│   │   ├── value_objects/
│   │   │   ├── agent_context.py           # 🆕 mover de base_agent.py — VO puro
│   │   │   └── agent_response.py          # 🆕 mover de base_agent.py — VO puro
│   │   ├── prompts/
│   │   │   └── level1_prompts.py          # ✅ lógica pura de construção de prompt
│   │   └── ports/                         # contratos de negócio puros, sem dict/JSON
│   │       ├── ai_client.py               # ✅ mover de assistant/ports/
│   │       ├── embedding_client.py
│   │       ├── menu_provider.py
│   │       ├── messaging_client.py
│   │       └── vector_store.py
│   │   # ⚠️ Level1Agent e BaseAgent SAEM daqui → infrastructure/agents/
│   │
│   ├── customer_memory/                   # 🆕 (unifica domain/memory/ + domain/ai/memory/)
│   │   ├── value_objects/
│   │   │   ├── memory_entry.py            # ✅ VO puro — sem I/O
│   │   │   └── conversation_memory.py     # ✅ VO puro — sem I/O
│   │   └── ports/
│   │       └── memory_port.py             # interface pura — sem mencionar Redis/dict
│   │   # ⚠️ MemoryManager SAI daqui → application/services/
│   │
│   ├── ordering/                          # futuro
│   │   ├── entities/
│   │   │   ├── order.py
│   │   │   └── order_item.py
│   │   ├── events/
│   │   │   └── order_created.py
│   │   └── repository.py
│   │
│   └── shared/
│       ├── value_objects/
│       │   ├── identifiers.py
│       │   ├── phone_number.py
│       │   └── base.py
│       ├── events/
│       │   └── domain_event.py            # 🆕 classe base imutável
│       ├── exceptions.py
│       └── result.py
│
├── application/                           # Orquestração — sem lógica de negócio
│   ├── use_cases/
│   │   ├── process_incoming_message.py    # ✅
│   │   ├── create_restaurant.py           # ✅
│   │   ├── sync_tacto_menu.py             # ✅
│   │   ├── fetch_tacto_restaurant_data.py # verificar uso real
│   │   └── create_order.py               # implementar ou remover
│   ├── services/
│   │   ├── message_buffer_service.py      # ✅
│   │   ├── agent_execution_service.py     # 🆕 recebe Level1Agent via injeção
│   │   └── memory_orchestration_service.py # 🆕 recebe MemoryManager (saiu do domínio)
│   └── dto/
│       ├── message_dto.py
│       └── restaurant_dto.py
│
├── infrastructure/                        # Adapters — implementam ports do domínio
│   ├── agents/                            # 🆕 execução de agentes LLM (saiu do domínio)
│   │   ├── base_agent.py                  # mover de domain/ai/agents/
│   │   └── level1_agent.py               # mover de domain/ai/agents/
│   ├── ai/
│   │   ├── gemini_client.py               # ✅ implements AIClient
│   │   ├── redis_memory.py                # ✅ implements MemoryPort
│   │   └── postgres_memory.py             # ✅ implements MemoryPort
│   ├── database/
│   │   ├── models/
│   │   ├── migrations/
│   │   └── connection.py
│   ├── external/
│   │   ├── tacto_client.py
│   │   └── tacto_menu_provider.py
│   ├── messaging/
│   │   ├── join_client.py                 # ✅ implements MessagingClient
│   │   ├── join_instance_manager.py
│   │   └── sent_message_tracker.py
│   ├── persistence/
│   │   ├── conversation_repository.py
│   │   ├── message_repository.py
│   │   └── restaurant_repository.py
│   ├── redis/
│   └── vector_store/
│
├── interfaces/
│   ├── http/
│   │   ├── routes/
│   │   └── dependencies.py
│   └── workers/
│
├── container.py
└── main.py
```

---

## 5. Arquivos para DELETAR

> ⚠️ Executar verificações grep antes de deletar (Fase 1).

| Arquivo | Motivo |
|---|---|
| `domain/assistant/strategies/` (pasta inteira) | Nunca chamados — substituídos pelo `Level1Agent` |
| `domain/assistant/services/assistant_service.py` | Stub vazio, import quebrado |
| `domain/assistant/services/response_orchestrator.py` | Nunca instanciado no fluxo ativo |
| `domain/assistant/services/intent_detection_service.py` | Verificar grep |
| `domain/memory/` (pasta inteira) | Imports quebrados, substituído |
| `domain/messaging/services/message_buffer_service.py` | Duplicado |
| `infrastructure/persistence/postgres/` (pasta inteira) | Duplicata dos repositórios da raiz |
| `setup_project_structure.py` | Script de scaffolding |
| `IMPLEMENTACAO_COMPLETA.txt` | Rascunho na raiz |
| `RESUMO_PARA_WINDSURF.txt` | Rascunho na raiz |

---

## 6. Plano de Execução Faseado

### FASE 1 — Limpeza de Dead Code (Risco: Baixíssimo) ✅ COMPLETA
**Status:** Concluída em 2026-03-28 | **Commit:** `01f6d3a`
**Resultado:** 21 arquivos alterados, 1119 linhas de dead code removidas.

```bash
# Verificações executadas antes das deleções
grep -r "response_orchestrator\|assistant_service\|BasicStrategy" tacto/ --include="*.py"
grep -r "from tacto.domain.memory" tacto/ --include="*.py"
grep -r "message_buffer_service" tacto/domain/ --include="*.py"
grep -r "from tacto.infrastructure.persistence.postgres" tacto/ --include="*.py"
```

- [x] Deletar `domain/assistant/strategies/`
- [x] Deletar `domain/assistant/services/assistant_service.py`
- [x] Deletar `domain/assistant/services/response_orchestrator.py`
- [x] Deletar `domain/assistant/services/intent_detection_service.py`
- [x] Deletar `domain/memory/` (pasta inteira)
- [x] Deletar `domain/messaging/services/message_buffer_service.py`
- [x] Deletar `infrastructure/persistence/postgres/`
- [x] Deletar `infrastructure/redis/message_buffer.py` (dead code adicional descoberto)
- [x] Limpar `__init__.py` com imports quebrados
- [x] Limpar `container.py` (remover import não usado)
- [x] **Checkpoint:** Container sobe, fluxo de mensagem testado e funcionando

### FASE 2 — Expulsar MemoryManager do Domínio (Risco: Médio) ✅ COMPLETA
**Status:** Concluída em 2026-03-28
**Objetivo:** Zero orquestração de I/O na camada de domínio.

- [x] Criar `domain/customer_memory/value_objects/memory_entry.py` — `MemoryEntry`, `MemoryType`, `ConversationMemory` (VOs puros)
- [x] Criar `domain/customer_memory/ports/memory_port.py` — `MemoryPort` interface pura
- [x] Criar `application/services/memory_orchestration_service.py` — `MemoryManager` movido para cá
- [x] Atualizar imports em `redis_memory.py`, `postgres_memory.py`, `process_incoming_message.py`, `level1_agent.py`
- [x] Atualizar `domain/ai/memory/__init__.py` e `domain/ai/__init__.py` para re-exportar do novo local (backward compat)
- [x] Deletar `domain/ai/memory/memory_manager.py`
- [x] **Checkpoint:** Container sobe, aguardando teste de fluxo

### FASE 3 — Expulsar Execução de Agentes do Domínio (Risco: Médio)
**Objetivo:** Zero chamadas de rede na camada de domínio.

- [ ] Criar `domain/ai_assistance/value_objects/agent_context.py` — extrair `AgentContext` como VO
- [ ] Criar `domain/ai_assistance/value_objects/agent_response.py` — extrair `AgentResponse` como VO
- [ ] Mover `domain/assistant/ports/` → `domain/ai_assistance/ports/` (revisar assinaturas — sem `dict`/JSON)
- [ ] Mover `domain/ai/prompts/` → `domain/ai_assistance/prompts/`
- [ ] Mover `domain/ai/agents/` → `infrastructure/agents/`
- [ ] Criar `application/services/agent_execution_service.py`
- [ ] Atualizar `process_incoming_message.py` e `dependencies.py`
- [ ] Deletar `domain/ai/agents/`, `domain/assistant/`
- [ ] **Checkpoint:** fluxo completo de mensagem funciona

### FASE 4 — Consolidar Contextos e Limpar (Risco: Baixo)
- [ ] Integrar resíduos de `domain/ai/` em `domain/ai_assistance/`
- [ ] Verificar `domain/order/` — implementar esqueleto mínimo ou mover para backlog
- [ ] `grep -r "from tacto.domain.assistant" tacto/` → deve retornar zero
- [ ] `grep -r "from tacto.domain.ai" tacto/` → deve retornar zero

### FASE 5 — Domain Events (Risco: Baixo)
- [ ] Criar `domain/shared/events/domain_event.py` — dataclass imutável base
- [ ] Criar eventos: `MessageReceived`, `AIDisabled`, `AIEnabled`, `RestaurantCreated`
- [ ] Publicar eventos nas entidades (sem quebrar fluxo existente)
- [ ] Documentar em ADR-005

---

## 7. Regras DDD para Todo Novo Código

### 7.1 Domínio — O que pode e o que não pode

| ✅ Pode | ❌ Nunca |
|---|---|
| Entidades com identidade | Imports de `infrastructure.*` |
| Value Objects imutáveis | Imports de `sqlalchemy`, `redis`, `httpx` |
| Domain Services stateless (lógica pura) | Chamadas a APIs externas |
| Repository interfaces (Ports) | Retornar `dict` nos Ports (use VOs) |
| Domain Events (dataclasses imutáveis) | Estado mutável em Value Objects |
| Ports com assinaturas de negócio puro | `async def` que faz I/O real |

### 7.2 Aggregates e Entities

- Aggregate Root é uma Entidade — ficam **juntos em `entities/`** no mesmo módulo
- Acesso externo ao Aggregate **somente** pelo Root
- `Conversation` é root — `Message` não é acessada diretamente de fora do contexto
- Um Repository por Aggregate Root — nunca por entidade filha

### 7.3 Ports — Contratos Puros

```python
# ❌ ERRADO — vaza tecnologia (dict = JSON/Postgres)
async def search_menu(self, query_embedding: list[float], limit: int) -> list[dict]:

# ✅ CORRETO — contrato de negócio puro
async def search_menu(self, query_embedding: list[float], limit: int) -> Success[list[MenuItem]] | Failure[Exception]:
```

### 7.4 Naming Conventions

```
Entity / Aggregate Root → domain/<context>/entities/<name>.py
Value Object            → domain/<context>/value_objects/<name>.py
Domain Service          → domain/<context>/services/<name>_service.py
Domain Event            → domain/<context>/events/<name>.py
Repository Port         → domain/<context>/repository.py
External Port           → domain/<context>/ports/<name>.py
Use Case                → application/use_cases/<verb>_<noun>.py
Application Service     → application/services/<name>_service.py
Infra Adapter           → infrastructure/<category>/<name>.py
Repository Impl         → infrastructure/persistence/<name>_repository.py
```

---

## 8. Critérios de Sucesso

- [ ] `grep -r "from tacto.infrastructure" tacto/domain/` → **zero resultados**
- [ ] `grep -r "from tacto.infrastructure" tacto/application/` → **zero resultados**
- [ ] `grep -r "import redis\|import sqlalchemy\|import httpx" tacto/domain/` → **zero resultados**
- [ ] Zero arquivos órfãos com imports quebrados
- [ ] Zero duplicação de responsabilidades entre contextos
- [ ] Container sobe sem warnings, fluxo de mensagem funciona após cada fase

---

## 9. ADRs Relacionados

- `ADR-001-ddd-architecture.md` — decisão original de usar DDD
- `ADR-004-bounded-contexts.md` — **🆕 criar** — 5 contextos definidos e suas fronteiras
- `ADR-005-layer-violations-fix.md` — **🆕 criar** — justificativa para mover MemoryManager e Level1Agent
