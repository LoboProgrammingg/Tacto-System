# 📊 Status de Implementação — Tacto-System

**Data**: 2026-03-28
**Fase**: Correções pré-go-live multi-tenant
**Realizado por**: Claude (Haiku 4.5) + Windsurf (continuação)

---

## 🎯 6 Problemas Identificados & Status

### ✅ Problema 3 — Timezone (COMPLETO)

**Problema Original**:
- `OpeningHours.is_open_now()` usava `datetime.now()` (hora local do servidor, UTC em prod)
- Restaurant não tinha campo `timezone`
- Docker não tinha variável `TZ`
- Domain usava `datetime.utcnow()` (naive), infra usava `datetime.now(timezone.utc)` (aware)

**Solução Implementada**:

| Arquivo | Mudança | Status |
|---------|---------|--------|
| `domain/restaurant/entities/restaurant.py` | Adicionado field `timezone: str = "America/Sao_Paulo"` | ✅ |
| `domain/restaurant/value_objects/opening_hours.py` | `is_open_now(tz)` agora aceita timezone; adicionado `get_next_opening(tz)` | ✅ |
| `infrastructure/database/models/restaurant.py` | Adicionada coluna `timezone: String(63)` | ✅ |
| `infrastructure/database/migrations/versions/004_restaurant_timezone.py` | Migration criada + rodada | ✅ |
| `docker-compose.yml` | Adicionado `TZ: America/Sao_Paulo` ao serviço api | ✅ |
| `domain/restaurant/entities/restaurant.py` | Substituído `datetime.utcnow()` → `datetime.now(timezone.utc)` | ✅ |
| `application/use_cases/process_incoming_message.py` | Passa `is_open` e `next_opening_text` ao AgentContext | ✅ |

**Resultado**:
```python
# Agora funciona corretamente:
is_open = restaurant.is_open_now()  # Usa restaurant.timezone
next_opening = restaurant.opening_hours.get_next_opening(restaurant.timezone)
# Retorna: "Abrimos hoje às 18:00" ou "Abrimos amanhã, segunda-feira, às 11:00"
```

---

### ✅ Problema 5 — IA Mais Humanizada (COMPLETO)

**Problemas Originais**:
- SYSTEM_PROMPT dizia "SEMPRE chame cliente pelo nome" → repetição em cada mensagem
- IA não tinha nome próprio (identidade)
- Emojis excessivos (1-2 por mensagem era muita)
- `Level1Agent` nunca verificava se restaurante estava fechado
- Sem resposta pré-pronta para fechamento

**Solução Implementada**:

| Arquivo | Mudança | Status |
|---------|---------|--------|
| `domain/ai/prompts/level1_prompts.py` | SYSTEM_PROMPT reescrito: "Você é Maria"; máx 1 emoji; sem repetir nome | ✅ |
| `domain/ai/prompts/level1_prompts.py` | Adicionado `get_closed_response(menu_url, next_opening)` | ✅ |
| `domain/ai/agents/base_agent.py` | Adicionados fields `is_open: bool` e `next_opening_text: str` ao AgentContext | ✅ |
| `domain/ai/agents/level1_agent.py` | Verifica `context.is_open` ANTES do LLM; retorna resposta pré-pronta se fechado | ✅ |
| `application/use_cases/process_incoming_message.py` | Calcula `is_open` e `next_opening_text`; passa ao AgentContext | ✅ |
| `application/use_cases/process_incoming_message.py` | Detecta `"restaurant_closed"` em triggered_actions; desativa AI | ✅ |

**Novo SYSTEM_PROMPT**:
```
Você é a **Maria**, atendente virtual do restaurante {restaurant_name}.

## PERSONALIDADE
- Seu nome é Maria (sempre mantenha essa identidade)
- Seja simpática, educada e prestativa
- Respostas CURTAS (máximo 2 frases por mensagem)
- **Use NO MÁXIMO 1 emoji por mensagem, e apenas quando muito expressivo**
- Use nome cliente APENAS na saudação inicial
- Nunca revele que você é IA a menos que perguntado
```

**Fluxo de Fechamento**:
```
1. Mensagem chega → Process agora calcula: is_open = restaurant.is_open_now()
2. Passa is_open + next_opening_text ao Level1Agent
3. Level1Agent verifica ANTES do LLM:
   if not context.is_open:
       return resposta fechada + triggered_actions=["restaurant_closed"]
4. Use case detecta "restaurant_closed" → conversation.disable_ai()
```

---

### ⏳ Problema 2 — Settings & Variáveis de Ambiente (PARCIALMENTE COMPLETO)

**Problemas Originais**:
- 10+ valores hardcoded espalhados pelo código
- Difícil ajustar para diferentes ambientes

**Implementado**:

| Arquivo | Campo | Valor Default | Alias | Status |
|---------|-------|----------------|-------|--------|
| `AppSettings` | `ai_disable_hours` | 12 | `AI_DISABLE_HOURS` | ✅ |
| `AppSettings` | `rag_search_limit` | 6 | `RAG_SEARCH_LIMIT` | ✅ |
| `AppSettings` | `conversation_history_limit` | 10 | `CONVERSATION_HISTORY_LIMIT` | ✅ |
| `RedisSettings` | `buffer_window_seconds` | 5 | `REDIS_BUFFER_WINDOW_SECONDS` | ✅ |
| `RedisSettings` | `buffer_lock_ttl` | 10 | `REDIS_BUFFER_LOCK_TTL` | ✅ |
| `RedisSettings` | `echo_tracker_ttl` | 5 | `REDIS_ECHO_TRACKER_TTL` | ✅ |
| `RedisSettings` | `message_id_tracker_ttl` | 300 | `REDIS_MSG_ID_TRACKER_TTL` | ✅ |
| `GeminiSettings` | `level1_temperature` | 0.7 | `LEVEL1_TEMPERATURE` | ✅ |
| `GeminiSettings` | `level1_max_tokens` | 2048 | `LEVEL1_MAX_TOKENS` | ✅ |

**Ainda Precisa**:
- [ ] Usar `settings.app.ai_disable_hours` em `conversation.py`
- [ ] Usar `settings.redis.*` em `webhook_join.py`
- [ ] Usar `settings.redis.*` em `sent_message_tracker.py`
- [ ] Usar `settings.gemini.level1_*` em `level1_agent.py`
- [ ] Usar `settings.app.rag_search_limit` em `process_incoming_message.py`
- [ ] Criar `.env.example` com todas

---

### 🔄 Problema 6 — LangChain LCEL Chain (PENDENTE)

**Status**: Não iniciado

**O que precisa**:
1. Refatorar `Level1Agent.process()` para usar LCEL
2. Converter history para formato `HumanMessage`/`AIMessage`
3. Adicionar `RunnableConfig` com tags de rastreamento
4. Resultado: trace estruturado no LangSmith

**Exemplo do que será**:
```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig

# Em __init__:
self._chain = (
    ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}"),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ])
    | self._llm
    | StrOutputParser()
)

# Em process():
config = RunnableConfig(
    tags=["level1", f"restaurant:{context.restaurant_id}"],
    metadata={
        "restaurant_id": str(context.restaurant_id),
        "restaurant_name": context.restaurant_name,
        "customer_phone": context.customer_phone,
    },
    run_name=f"Level1Agent/{context.restaurant_name}",
)
response_text = await self._chain.ainvoke({
    "system_prompt": system_prompt,
    "history": langchain_history,
    "input": message,
}, config=config)
```

---

### 🔄 Problema 1 — DDD Ports Cleanup (PENDENTE)

**Status**: Não iniciado

**Problema**:
- `ProcessIncomingMessageUseCase` importa direto de `infrastructure`:
  ```python
  from tacto.infrastructure.ai.gemini_client import GeminiClient
  from tacto.infrastructure.vector_store.pgvector_store import PgvectorStore
  from tacto.infrastructure.messaging.join_client import JoinClient
  ```
- Viola Dependency Rule: Application não deve conhecer Infrastructure

**Solução**:
1. Criar ports (interfaces) em `domain/assistant/ports/`:
   - `embedding_client.py` → `EmbeddingClient(ABC)`
   - `vector_store.py` → `VectorStore(ABC)`
   - `messaging_client.py` → `MessagingClient(ABC)`
2. Use cases recebem ports no `__init__`
3. Implementations injetadas pela camada de Interface

**Arquivos a tocar**:
- `tacto/domain/assistant/ports/embedding_client.py` (criar)
- `tacto/domain/assistant/ports/vector_store.py` (criar)
- `tacto/domain/assistant/ports/messaging_client.py` (criar)
- `tacto/application/use_cases/process_incoming_message.py` (atualizar imports)
- `tacto/application/use_cases/sync_tacto_menu.py` (atualizar imports)
- `tacto/interfaces/http/dependencies.py` (injetar implementações)

---

### 🔄 Problema 4 — Buffer no Domain (PENDENTE)

**Status**: Não iniciado (Baixa prioridade)

**Problema**:
- `webhook_join.py` tem `_buffer_and_process()` com 160+ linhas de lógica inline
- Lógica de negócio no router (camada Interface)

**Solução**:
1. Verificar `domain/messaging/services/message_buffer_service.py`
2. Mover buffer logic para Application Service
3. Router fica simples: validar → delegar → return 200

---

## 📁 Arquivos Modificados

### ✅ Completos

```
✅ tacto/domain/restaurant/entities/restaurant.py
   - Adicionado: timezone field, factory method param
   - Alterado: datetime.utcnow() → datetime.now(timezone.utc)
   - Alterado: is_open_now() passa timezone ao opening_hours

✅ tacto/domain/restaurant/value_objects/opening_hours.py
   - Adicionado: zoneinfo import
   - Alterado: is_open_now(tz) com ZoneInfo
   - Adicionado: get_next_opening(tz) com lógica humanizada

✅ tacto/infrastructure/database/models/restaurant.py
   - Adicionado: timezone column (String(63))

✅ tacto/infrastructure/database/migrations/versions/004_restaurant_timezone.py
   - Migration criada (upgrade + downgrade)
   - Rodada com sucesso: ✅ 004_restaurant_timezone applied

✅ docker-compose.yml
   - Adicionado: TZ: America/Sao_Paulo ao api service

✅ tacto/domain/ai/prompts/level1_prompts.py
   - Reescrito: SYSTEM_PROMPT (Maria, 1 emoji, sem repetir nome)
   - Adicionado: get_closed_response(menu_url, next_opening)

✅ tacto/domain/ai/agents/base_agent.py
   - Adicionado: is_open, next_opening_text ao AgentContext

✅ tacto/domain/ai/agents/level1_agent.py
   - Adicionado: check de restaurante fechado ANTES do LLM
   - Retorna: restaurant_closed response pré-pronta

✅ tacto/application/dto/restaurant_dto.py
   - Adicionado: timezone em CreateRestaurantDTO, UpdateRestaurantDTO, RestaurantResponseDTO
   - Alterado: from_entity() inclui timezone

✅ tacto/application/use_cases/create_restaurant.py
   - Alterado: passa timezone ao Restaurant.create()

✅ tacto/application/use_cases/process_incoming_message.py
   - Adicionado: calcula is_open e next_opening_text
   - Adicionado: passa ao AgentContext
   - Adicionado: detecta restaurant_closed action; desativa AI

✅ tacto/infrastructure/persistence/restaurant_repository.py
   - Alterado: _to_model() inclui timezone
   - Alterado: _to_entity() inclui timezone

✅ tacto/config/settings.py
   - Adicionado: AppSettings fields (ai_disable_hours, rag_search_limit, conversation_history_limit)
   - Adicionado: RedisSettings fields (buffer_window_seconds, buffer_lock_ttl, echo_tracker_ttl, message_id_tracker_ttl)
   - Adicionado: GeminiSettings fields (level1_temperature, level1_max_tokens)
```

### 🔄 Parciais (Precisa Usar Settings)

```
🔄 tacto/domain/messaging/entities/conversation.py
   - Ainda hardcoded: AI_DISABLE_DURATION_HOURS=12
   - TODO: ler de settings.app.ai_disable_hours

🔄 tacto/interfaces/http/routes/webhook_join.py
   - Ainda hardcoded: _BUFFER_WINDOW_SECONDS=5, _BUFFER_TTL_SECONDS=30, lock TTL=10
   - TODO: ler de settings.redis.buffer_window_seconds, etc

🔄 tacto/infrastructure/messaging/sent_message_tracker.py
   - Ainda hardcoded: _TTL_MESSAGE_ID=300, _TTL_PHONE=5
   - TODO: ler de settings.redis.message_id_tracker_ttl, echo_tracker_ttl

🔄 tacto/domain/ai/agents/level1_agent.py
   - Linha 74-75: temperature=0.7, max_tokens=1024
   - TODO: ler de settings.gemini.level1_temperature, level1_max_tokens

🔄 tacto/application/use_cases/process_incoming_message.py
   - Linha 195: limit=6 (RAG search)
   - TODO: ler de settings.app.rag_search_limit
```

### ❌ Não Iniciados

```
❌ .env.example
   - Criar com TODAS as variáveis do projeto

❌ Problema 6 — LangChain LCEL Chain
   - Refatorar Level1Agent para usar ChatPromptTemplate | LLM | StrOutputParser
   - Adicionar RunnableConfig com tags

❌ Problema 1 — DDD Ports
   - Criar interfaces em domain/assistant/ports/
   - Atualizar use cases para usar ports
   - Injetar implementações em dependencies.py
```

---

## 🧪 Testes Manuais Necessários

| Teste | Descrição | Status |
|-------|-----------|--------|
| Timezone | Enviar mensagem fora do horário → IA responde com fechamento | ⏳ Pendente |
| Nome | IA se apresenta como "Maria", não repete nome cliente | ⏳ Pendente |
| Emojis | Máximo 1 emoji por resposta | ⏳ Pendente |
| LangSmith | Trace com tags de restaurant no projeto "Tacto-System" | ⏳ Pendente |
| Settings | Alterar `RAG_SEARCH_LIMIT=3` no .env → busca retorna 3 itens | ⏳ Pendente |
| Multi-tenant | 2+ restaurantes simultâneos, sem vazamento de dados | ⏳ Pendente |
| Echo Detection | Ignore bot's own echo, process human operator messages | ⏳ Pendente |

---

## 📦 Environment Variables Necessárias

**Mínimo para rodar localmente**:
```bash
# App
APP_NAME=TactoFlow
APP_VERSION=0.0.1
DEBUG=true
AI_DISABLE_HOURS=12
RAG_SEARCH_LIMIT=6
CONVERSATION_HISTORY_LIMIT=10

# Database
DB_HOST=localhost
DB_PORT=5433
DB_USER=tacto
DB_PASSWORD=tacto
DB_NAME=tacto_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_BUFFER_WINDOW_SECONDS=5
REDIS_BUFFER_LOCK_TTL=10
REDIS_ECHO_TRACKER_TTL=5
REDIS_MSG_ID_TRACKER_TTL=300

# Gemini
GOOGLE_API_KEY=[your-key]
LLM_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/gemini-embedding-001
EMBEDDING_DIMENSION=768
GEMINI_MAX_TOKENS=2048
GEMINI_TEMPERATURE=0.7
LEVEL1_TEMPERATURE=0.7
LEVEL1_MAX_TOKENS=2048

# Join
JOIN_API_BASE_URL=https://api-prd.joindeveloper.com.br
JOIN_TOKEN_CLIENTE=[your-token]

# Tacto External API
TACTO_API_BASE_URL=https://api-externa.tactonuvem.com.br
TACTO_AUTH_URL=https://accounts.tactonuvem.com.br/connect/token
TACTO_CLIENT_ID=[your-id]
TACTO_CLIENT_SECRET=[your-secret]

# LangSmith (opcional, para observabilidade)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=[your-key]
LANGSMITH_PROJECT=Tacto-System
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

---

## 🚀 Próximos Passos Para Windsurf

### Priority 1 (Hoje)
- [ ] Usar `settings.*` em todos os arquivos parciais
- [ ] Criar `.env.example`
- [ ] Testar timezone localmente

### Priority 2 (Semana)
- [ ] Refatorar Level1Agent para LCEL chain
- [ ] Criar ports DDD (embedding, vector_store, messaging)
- [ ] Testes manuais de timezone, humanização, emoji

### Priority 3 (Próxima)
- [ ] Buffer logic no domain
- [ ] Testes de integração (pytest)
- [ ] E2E tests (webhook → resposta)

---

**Última atualização**: 2026-03-28 22:30 (PT)
**Próxima revisão**: Após Windsurf completar Priority 1
