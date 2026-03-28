# 🚀 PROMPT PARA WINDSURF — Continuação Tacto-System

**Data**: 2026-03-28
**Status**: Claude finalizou 60% das correções; Windsurf continua os 40%
**Créditos usados**: ~70% do budget

---

## 📚 Context Rápido

**Tacto-System** = Sistema de automação WhatsApp para restaurantes (multi-tenant).

**Fase**: Correções pré-go-live (6 problemas identificados; 2,5 resolvidos; 3,5 pendentes)

**Arquitetura**: FastAPI + Clean Architecture + DDD + PostgreSQL + Redis + Google Gemini

Leia:
1. `docs/PROJETO_CONTEXTO.md` — contexto geral completo
2. `docs/STATUS_IMPLEMENTACAO.md` — status detalhado de cada problema

---

## ✅ Já Feito (Claude)

### 1. Timezone (COMPLETO)
- ✅ Restaurant tem field `timezone` (default: "America/Sao_Paulo")
- ✅ Migration `004_restaurant_timezone` criada + rodada
- ✅ `OpeningHours.is_open_now(tz)` + `get_next_opening(tz)`
- ✅ `datetime.utcnow()` → `datetime.now(timezone.utc)`
- ✅ Docker: `TZ=America/Sao_Paulo`

### 2. IA Humanizada (COMPLETO)
- ✅ SYSTEM_PROMPT reescrito (Maria, 1 emoji max, sem repetir nome)
- ✅ `get_closed_response()` em Level1Prompts
- ✅ AgentContext tem `is_open`, `next_opening_text`
- ✅ Level1Agent verifica fechamento ANTES do LLM
- ✅ ProcessIncomingMessageUseCase desativa AI quando fechado

### 3. Settings (PARCIAL)
- ✅ Fields criados em `AppSettings`, `RedisSettings`, `GeminiSettings`
- ❌ Mas NÃO estão sendo usados ainda (ainda hardcoded nos arquivos)

---

## 🔄 Trabalho Para Windsurf

### **Task 1: Settings — Usar em Todos os Arquivos** (CRÍTICO)

Estes arquivos ainda usam valores hardcoded. Altere para ler de `settings`:

#### 1.1 `tacto/domain/messaging/entities/conversation.py`
**Procure por**:
```python
AI_DISABLE_DURATION_HOURS = 12  # Line ~17
```

**Altere para**:
```python
# Remove hardcode; use settings ao chamar disable_ai()
# Em process_incoming_message.py quando detectar "restaurant_closed":
# conversation.disable_ai(reason="restaurant_closed", duration_hours=settings.app.ai_disable_hours)
```

Ou adicione duration_hours como param de `disable_ai()`.

#### 1.2 `tacto/interfaces/http/routes/webhook_join.py`
**Procure por** (linhas ~150-160):
```python
_BUFFER_WINDOW_SECONDS = 5
_BUFFER_TTL_SECONDS = 30
# lock TTL = 10
```

**Altere para**:
```python
settings = get_settings()
BUFFER_WINDOW_SECONDS = settings.redis.buffer_window_seconds
BUFFER_LOCK_TTL = settings.redis.buffer_lock_ttl
BUFFER_TTL = settings.redis.buffer_ttl
```

#### 1.3 `tacto/infrastructure/messaging/sent_message_tracker.py`
**Procure por**:
```python
_TTL_MESSAGE_ID = 300
_TTL_PHONE = 5
```

**Altere para**:
```python
# Receba settings no __init__ ou como param
_TTL_MESSAGE_ID = settings.redis.message_id_tracker_ttl  # 300
_TTL_PHONE = settings.redis.echo_tracker_ttl  # 5
```

#### 1.4 `tacto/domain/ai/agents/level1_agent.py`
**Procure por** (linhas 74-75):
```python
self._llm = ChatGoogleGenerativeAI(
    model=self._model_name,
    google_api_key=settings.gemini.api_key,
    temperature=0.7,           # ← Hardcoded
    max_tokens=1024,           # ← Diferente de settings.gemini.max_tokens=2048
    convert_system_message_to_human=True,
)
```

**Altere para**:
```python
self._llm = ChatGoogleGenerativeAI(
    model=self._model_name,
    google_api_key=settings.gemini.api_key,
    temperature=settings.gemini.level1_temperature,      # 0.7
    max_tokens=settings.gemini.level1_max_tokens,        # 2048
    convert_system_message_to_human=True,
)
```

#### 1.5 `tacto/application/use_cases/process_incoming_message.py`
**Procure por** (linhas ~190-195):
```python
search_result = await self._pgvector_store.search_menu(
    restaurant.id.value, embed_result.value, limit=6  # ← Hardcoded
)
```

**Altere para**:
```python
settings = get_settings()
search_result = await self._pgvector_store.search_menu(
    restaurant.id.value, embed_result.value, limit=settings.app.rag_search_limit
)
```

E também para conversation_history (linha ~172):
```python
recent_messages_result = await self._message_repo.find_recent_by_conversation(
    conversation.id, limit=10  # ← Hardcoded
)
```

Altere para:
```python
recent_messages_result = await self._message_repo.find_recent_by_conversation(
    conversation.id, limit=settings.app.conversation_history_limit
)
```

#### 1.6 Criar `.env.example`
**Crie arquivo** `/.env.example` com:
```bash
# Application
APP_NAME=TactoFlow
APP_VERSION=0.0.1
DEBUG=false
SECRET_KEY=change-me-in-production
AI_DISABLE_HOURS=12
RAG_SEARCH_LIMIT=6
CONVERSATION_HISTORY_LIMIT=10

# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=tacto
DB_PASSWORD=tacto
DB_NAME=tacto_db
DB_ECHO=false
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_BUFFER_TTL=5
REDIS_MEMORY_TTL=3600
REDIS_BUFFER_WINDOW_SECONDS=5
REDIS_BUFFER_LOCK_TTL=10
REDIS_ECHO_TRACKER_TTL=5
REDIS_MSG_ID_TRACKER_TTL=300

# Google Gemini
GOOGLE_API_KEY=
LLM_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/gemini-embedding-001
EMBEDDING_DIMENSION=768
GEMINI_MAX_TOKENS=2048
GEMINI_TEMPERATURE=0.7
LEVEL1_TEMPERATURE=0.7
LEVEL1_MAX_TOKENS=2048

# Join API (WhatsApp)
JOIN_API_BASE_URL=https://api-prd.joindeveloper.com.br
JOIN_TOKEN_CLIENTE=
JOIN_HTTP_TIMEOUT=30

# Tacto External API (Cardápios)
TACTO_API_BASE_URL=https://api-externa.tactonuvem.com.br
TACTO_AUTH_URL=https://accounts.tactonuvem.com.br/connect/token
TACTO_CLIENT_ID=integracao-externa
TACTO_CLIENT_SECRET=
TACTO_CHAVE_ORIGEM=
TACTO_HTTP_TIMEOUT=120

# LangSmith (Observabilidade)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=Tacto-System
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

---

### **Task 2: LangChain LCEL Chain — Level1Agent Refactor** (ALTO)

**Objetivo**: Converter `Level1Agent.process()` para usar LCEL chain com `RunnableConfig` para observabilidade estruturada.

**Arquivo**: `tacto/domain/ai/agents/level1_agent.py`

**Mudanças**:

#### 2.1 Adicionar imports
```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
```

#### 2.2 Em `__init__` ou novo método `_build_chain()`
```python
def _build_chain(self):
    """Build LCEL chain for structured observability."""
    self._chain = (
        ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ])
        | self._llm
        | StrOutputParser()
    )
```

Chame `_build_chain()` no final de `initialize()`.

#### 2.3 Em `process()`, refatore a chamada do LLM

**Antes**:
```python
messages = [SystemMessage(content=system_prompt)]
for msg in conversation_history[-10:]:
    role = msg.get("role", "user")
    content = msg.get("content", "")
    if role == "user":
        messages.append(HumanMessage(content=content))
    elif role == "assistant":
        messages.append(AIMessage(content=content))

messages.append(HumanMessage(content=message))

response = await self._llm.ainvoke(messages)
response_text = response.content
```

**Depois**:
```python
# Convert history to LangChain messages format
langchain_history = []
for msg in conversation_history[-10:]:
    role = msg.get("role", "user")
    content = msg.get("content", "")
    if role == "user":
        langchain_history.append(HumanMessage(content=content))
    elif role == "assistant":
        langchain_history.append(AIMessage(content=content))

# Build RunnableConfig with tags for LangSmith
config = RunnableConfig(
    tags=["level1", f"restaurant:{context.restaurant_id}"],
    metadata={
        "restaurant_id": str(context.restaurant_id),
        "restaurant_name": context.restaurant_name,
        "customer_phone": context.customer_phone,
    },
    run_name=f"Level1Agent/{context.restaurant_name}",
)

# Invoke chain with structured config
response_text = await self._chain.ainvoke(
    {
        "system_prompt": system_prompt,
        "history": langchain_history,
        "input": message,
    },
    config=config,
)
```

**Resultado esperado no LangSmith**:
```
Level1Agent/Pizzaria da Praça
├── ChatPromptTemplate (system + history + input)
├── ChatGoogleGenerativeAI (gemini-2.5-flash)
└── StrOutputParser (extrai texto)
```

Com tags `level1`, `restaurant:{id}` filtráveis.

---

### **Task 3: DDD Ports — Criar Interfaces Abstratas** (MÉDIO)

**Objetivo**: Mover dependências concretas da infra para abstrações (ports) no domínio.

**Arquivos a criar**:

#### 3.1 `tacto/domain/assistant/ports/__init__.py`
```python
"""Ports (abstract interfaces) for assistant domain."""
```

#### 3.2 `tacto/domain/assistant/ports/embedding_client.py`
```python
"""Abstract embedding client interface."""

from abc import ABC, abstractmethod
from tacto.domain.shared.result import Failure, Success


class EmbeddingClient(ABC):
    """Port for AI embedding generation."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> Success[list[float]] | Failure[Exception]:
        """
        Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            Success with list of floats (embedding vector) or Failure
        """
        ...
```

#### 3.3 `tacto/domain/assistant/ports/vector_store.py`
```python
"""Abstract vector store interface."""

from abc import ABC, abstractmethod
from uuid import UUID
from typing import Any, Optional
from tacto.domain.shared.result import Failure, Success


class VectorStore(ABC):
    """Port for vector similarity search and storage."""

    @abstractmethod
    async def upsert_menu_embeddings(
        self,
        restaurant_id: UUID,
        items: list[dict[str, Any]],
    ) -> Success[bool] | Failure[Exception]:
        """Upsert menu items with embeddings."""
        ...

    @abstractmethod
    async def search_menu(
        self,
        restaurant_id: UUID,
        embedding: list[float],
        limit: int = 6,
    ) -> Success[list[dict[str, Any]]] | Failure[Exception]:
        """Search menu items by similarity."""
        ...

    @abstractmethod
    async def count(
        self,
        restaurant_id: UUID,
    ) -> Success[int] | Failure[Exception]:
        """Count embeddings for restaurant."""
        ...
```

#### 3.4 `tacto/domain/assistant/ports/messaging_client.py`
```python
"""Abstract messaging client interface."""

from abc import ABC, abstractmethod
from tacto.domain.shared.result import Failure, Success


class MessagingClient(ABC):
    """Port for messaging operations (WhatsApp, etc)."""

    @abstractmethod
    async def send_message(
        self,
        instance_key: str,
        phone: str,
        message: str,
        simulate_typing: bool = False,
    ) -> Success[dict] | Failure[Exception]:
        """Send message via WhatsApp."""
        ...

    @abstractmethod
    async def send_reply(
        self,
        instance_key: str,
        phone: str,
        message: str,
        reply_to_message_id: str,
    ) -> Success[dict] | Failure[Exception]:
        """Send reply to specific message."""
        ...
```

#### 3.5 Atualizar `ProcessIncomingMessageUseCase`

**Alterações no `__init__`**:
```python
def __init__(
    self,
    restaurant_repository: RestaurantRepository,
    conversation_repository: ConversationRepository,
    message_repository: MessageRepository,
    messaging_client: MessagingClient,  # ← Agora port, não JoinClient
    ai_agent: Optional[BaseAgent] = None,
    memory_manager: Optional[MemoryManager] = None,
    menu_provider: Optional[MenuProvider] = None,
    vector_store: Optional[VectorStore] = None,  # ← Agora port, não PgvectorStore
    embedding_client: Optional[EmbeddingClient] = None,  # ← Agora port, não GeminiClient
) -> None:
    self._restaurant_repo = restaurant_repository
    self._conversation_repo = conversation_repository
    self._message_repo = message_repository
    self._messaging_client = messaging_client
    self._ai_agent = ai_agent or Level1Agent(memory_manager=memory_manager)
    self._memory_manager = memory_manager
    self._menu_provider = menu_provider
    self._vector_store = vector_store
    self._embedding_client = embedding_client
```

**Alterar imports**:
```python
# Remover:
# from tacto.infrastructure.ai.gemini_client import GeminiClient
# from tacto.infrastructure.vector_store.pgvector_store import PgvectorStore
# from tacto.infrastructure.messaging.join_client import JoinClient

# Adicionar:
from tacto.domain.assistant.ports.embedding_client import EmbeddingClient
from tacto.domain.assistant.ports.vector_store import VectorStore
from tacto.domain.assistant.ports.messaging_client import MessagingClient
```

#### 3.6 Injetar implementações em `interfaces/http/dependencies.py`

Exemplo (onde ProcessIncomingMessageUseCase é instanciado):
```python
from tacto.infrastructure.ai.gemini_client import GeminiClient
from tacto.infrastructure.vector_store.pgvector_store import PgvectorStore
from tacto.infrastructure.messaging.join_client import JoinClient

# Injetar implementações concretas
use_case = ProcessIncomingMessageUseCase(
    restaurant_repository=postgres_restaurant_repo,
    conversation_repository=postgres_conversation_repo,
    message_repository=postgres_message_repo,
    messaging_client=JoinClient(...),  # ← Implementação concreta
    vector_store=PgvectorStore(...),   # ← Implementação concreta
    embedding_client=GeminiClient(...), # ← Implementação concreta
)
```

---

### **Task 4: Buffer no Domain** (BAIXO — Opcional)

Se houver tempo:
- Verificar `domain/messaging/services/message_buffer_service.py`
- Simplificar `webhook_join.py` (atualmente ~200 linhas de buffer logic inline)
- Mover tudo para application service

---

## 🧪 Testes Manuais

Após cada task, teste:

```bash
# 1. Iniciar containers
docker-compose up -d

# 2. Rodar migrations (se necessário)
DB_HOST=localhost DB_PORT=5433 python -m alembic upgrade head

# 3. Verificar app está saudável
curl http://localhost:8100/health

# 4. Test timezone
# - Enviar mensagem fora do horário
# - Verificar: IA responde com "Opa! No momento estamos fechados"

# 5. Test nome
# - Enviar mensagem
# - Verificar: IA não repete nome em cada frase

# 6. Test emoji
# - Enviar várias mensagens
# - Verificar: máx 1 emoji por resposta

# 7. Test settings
# - Alterar RAG_SEARCH_LIMIT=3 no .env
# - Restart container
# - Enviar mensagem
# - Verificar: busca retorna 3 itens (não 6)

# 8. Test LangSmith
# - Abrir https://smith.langchain.com/
# - Projeto "Tacto-System"
# - Verificar trace com tags ["level1", "restaurant:xxx"]
```

---

## 📋 Checklist Para Windsurf

- [ ] Leu `docs/PROJETO_CONTEXTO.md`
- [ ] Leu `docs/STATUS_IMPLEMENTACAO.md`
- [ ] **Task 1**: Settings — Usar em 6 arquivos
- [ ] **Task 1**: Criar `.env.example`
- [ ] **Task 2**: LCEL chain — refatorar Level1Agent
- [ ] **Task 3**: DDD ports — criar 3 interfaces
- [ ] **Task 3**: Atualizar ProcessIncomingMessageUseCase
- [ ] **Task 3**: Injetar em dependencies.py
- [ ] **Task 4** (opcional): Buffer no domain
- [ ] Testes manuais: Timezone
- [ ] Testes manuais: Humanização (nome, emoji)
- [ ] Testes manuais: Settings
- [ ] Testes manuais: LangSmith trace
- [ ] Commit tudo com mensagem clara

---

## 🎯 Estimativa de Tempo

- **Task 1** (Settings): 30 min
- **Task 2** (LCEL): 45 min
- **Task 3** (DDD Ports): 1h 15min
- **Task 4** (Buffer): 30 min (opcional)
- **Testes**: 30 min

**Total**: ~2h 30min para completar tudo (exceto Task 4)

---

## 🔗 Referências Rápidas

- FastAPI Dependency Injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- LangChain LCEL: https://python.langchain.com/docs/expression_language/
- RunnableConfig: https://api.python.langchain.com/en/latest/runnables/langchain_core.runnables.config.RunnableConfig.html
- Python zoneinfo: https://docs.python.org/3/library/zoneinfo.html

---

## 💬 Dúvidas?

Se algo não estiver claro, revise:
1. `docs/PROJETO_CONTEXTO.md` — contexto geral
2. `docs/STATUS_IMPLEMENTACAO.md` — status detalhado
3. Código dos arquivos já implementados (timezone, humanização)

**Boa sorte! Sistema está quase pronto para go-live! 🚀**
