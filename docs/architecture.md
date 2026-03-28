# 🏛️ TactoFlow - Arquitetura DDD Detalhada

**Versão:** 0.0.1  
**Última Atualização:** 2026-03-27  
**Baseado em:** Domain-Driven Design (Eric Evans) + Clean Architecture (Uncle Bob)

---

## 📋 ÍNDICE

1. [Visão Arquitetural](#visão-arquitetural)
2. [Camadas da Arquitetura](#camadas-da-arquitetura)
3. [Bounded Contexts Detalhados](#bounded-contexts-detalhados)
4. [Aggregates e Entities](#aggregates-e-entities)
5. [Value Objects](#value-objects)
6. [Domain Services](#domain-services)
7. [Repository Pattern](#repository-pattern)
8. [Use Cases (Application Layer)](#use-cases-application-layer)
9. [Infrastructure Layer](#infrastructure-layer)
10. [Dependency Flow](#dependency-flow)
11. [Patterns Aplicados](#patterns-aplicados)

---

## 🎯 VISÃO ARQUITETURAL

### Princípios Fundamentais

**1. Clean Architecture (Onion Architecture)**
```
┌─────────────────────────────────────────────────┐
│         Interface Layer (HTTP/CLI/Workers)      │
│  ┌───────────────────────────────────────────┐  │
│  │    Application Layer (Use Cases)          │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │   Domain Layer (Business Logic)     │  │  │
│  │  │   - Entities                        │  │  │
│  │  │   - Value Objects                   │  │  │
│  │  │   - Aggregates                      │  │  │
│  │  │   - Domain Services                 │  │  │
│  │  │   - Repository Interfaces           │  │  │
│  │  └─────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
         ▲
         │ implements
         │
┌─────────────────────────────────────────────────┐
│    Infrastructure Layer (External Details)      │
│    - DB Implementations                         │
│    - API Clients                                │
│    - Redis, Message Queues                      │
└─────────────────────────────────────────────────┘
```

**2. Domain-Driven Design**
- **Ubiquitous Language:** Mesma linguagem entre negócio e código
- **Bounded Contexts:** Fronteiras explícitas entre subdomínios
- **Aggregates:** Clusters de objetos tratados como unidade
- **Entities:** Objetos com identidade própria
- **Value Objects:** Objetos sem identidade, imutáveis

**3. SOLID Principles**
- **S**ingle Responsibility
- **O**pen/Closed
- **L**iskov Substitution
- **I**nterface Segregation
- **D**ependency Inversion

---

## 🏗️ CAMADAS DA ARQUITETURA

### 1️⃣ Domain Layer (Camada de Domínio)

**Localização:** `tacto/domain/`

**Responsabilidade:** Regras de negócio puras, sem dependências externas

**Conteúdo:**
```
domain/
├── restaurant/
│   ├── entities/
│   │   ├── restaurant.py          # Aggregate Root
│   │   └── integration.py         # Entity
│   ├── value_objects/
│   │   ├── integration_type.py
│   │   ├── automation_type.py
│   │   └── opening_hours.py
│   ├── services/
│   │   └── opening_hours_validator.py
│   └── repository.py              # Interface apenas
│
├── messaging/
│   ├── entities/
│   │   ├── conversation.py        # Aggregate Root
│   │   └── message.py             # Entity
│   ├── value_objects/
│   │   ├── message_status.py
│   │   └── message_source.py
│   ├── services/
│   │   └── message_buffer_service.py
│   └── repository.py
│
├── assistant/
│   ├── services/
│   │   ├── assistant_service.py
│   │   ├── response_orchestrator.py
│   │   └── intent_detection_service.py
│   └── strategies/
│       ├── base_strategy.py       # Abstract
│       ├── basic_strategy.py
│       ├── intermediate_strategy.py
│       └── advanced_strategy.py
│
├── memory/
│   ├── entities/
│   │   └── conversation_memory.py
│   ├── services/
│   │   └── memory_service.py
│   └── repository.py
│
├── order/                         # FUTURO
│   ├── entities/
│   │   ├── order.py               # Aggregate Root
│   │   └── order_item.py
│   └── repository.py
│
└── shared/
    ├── value_objects/
    │   ├── phone_number.py
    │   └── tenant_id.py
    └── result.py                  # Result<T, E> monad
```

**Regras:**
- ✅ Pode depender de outras entidades do domínio
- ✅ Pode depender de value objects
- ❌ NÃO pode depender de infraestrutura
- ❌ NÃO pode depender de frameworks
- ❌ NÃO pode ter import de FastAPI, SQLAlchemy, etc.

---

### 2️⃣ Application Layer (Camada de Aplicação)

**Localização:** `tacto/application/`

**Responsabilidade:** Orquestrar casos de uso, coordenar domain services

**Conteúdo:**
```
application/
├── use_cases/
│   ├── restaurant/
│   │   ├── create_restaurant.py
│   │   ├── update_restaurant.py
│   │   └── get_restaurant.py
│   │
│   ├── messaging/
│   │   ├── process_incoming_message.py    # CORE
│   │   ├── send_message.py
│   │   └── get_conversation_history.py
│   │
│   ├── assistant/
│   │   └── generate_response.py
│   │
│   └── memory/
│       ├── store_memory.py
│       └── retrieve_context.py
│
├── dto/
│   ├── restaurant_dto.py
│   ├── message_dto.py
│   └── response_dto.py
│
└── services/
    └── application_coordinator.py
```

**Características:**
- Recebe DTOs da interface layer
- Converte DTOs em domain objects
- Chama domain services e repositories
- Retorna Results com sucesso/erro
- **Transaction boundary** (se aplicável)

---

### 3️⃣ Infrastructure Layer (Camada de Infraestrutura)

**Localização:** `tacto/infrastructure/`

**Responsabilidade:** Implementar detalhes técnicos

**Conteúdo:**
```
infrastructure/
├── persistence/
│   ├── postgres/
│   │   ├── models/                    # SQLAlchemy models
│   │   │   ├── restaurant_model.py
│   │   │   ├── conversation_model.py
│   │   │   └── message_model.py
│   │   ├── repositories/
│   │   │   ├── restaurant_repository.py
│   │   │   ├── messaging_repository.py
│   │   │   └── memory_repository.py
│   │   └── database.py                # Connection pool
│   │
│   └── migrations/                    # Alembic
│       └── versions/
│
├── cache/
│   └── redis/
│       ├── redis_client.py
│       ├── message_buffer_cache.py
│       └── token_cache.py
│
├── vector_store/
│   └── pgvector/
│       ├── pgvector_store.py
│       └── embedding_service.py
│
├── external_apis/
│   ├── tacto/
│   │   ├── tacto_client.py
│   │   ├── oauth2_handler.py
│   │   ├── menu_service.py
│   │   └── institutional_service.py
│   │
│   └── join/
│       ├── join_client.py
│       ├── webhook_parser.py
│       └── message_sender.py
│
├── ai/
│   ├── gemini/
│   │   ├── gemini_client.py
│   │   ├── embedding_generator.py
│   │   └── prompt_builder.py
│   │
│   └── rag/
│       ├── rag_pipeline.py
│       └── context_retriever.py
│
└── config/
    ├── settings.py                    # Pydantic Settings
    └── logging_config.py
```

**Regras:**
- ✅ Implementa interfaces do domínio
- ✅ Conhece frameworks (SQLAlchemy, Redis, etc.)
- ✅ Faz I/O (HTTP, DB, file system)
- ❌ NÃO contém lógica de negócio

---

### 4️⃣ Interface Layer (Camada de Interface)

**Localização:** `tacto/interfaces/`

**Responsabilidade:** Expor funcionalidades para o mundo externo

**Conteúdo:**
```
interfaces/
├── http/
│   ├── api/
│   │   └── v1/
│   │       ├── restaurants.py         # CRUD restaurantes
│   │       ├── conversations.py       # Histórico conversas
│   │       └── admin.py               # Endpoints admin
│   │
│   ├── webhooks/
│   │   └── join_webhook.py            # Receber msgs Join
│   │
│   ├── middleware/
│   │   ├── tenant_middleware.py       # Injetar restaurant_id
│   │   └── error_handler.py
│   │
│   └── dependencies.py                # FastAPI dependencies
│
├── workers/
│   ├── message_worker.py              # Processar fila de msgs
│   └── memory_indexer.py              # Indexar embeddings
│
└── cli/                               # Se necessário
    └── admin_cli.py
```

---

## 🎯 BOUNDED CONTEXTS DETALHADOS

### 1. Restaurant Context

**Aggregate Root:** `Restaurant`

**Responsabilidade:** Gerenciar configuração e estado de restaurantes

#### Aggregate: Restaurant

```python
# domain/restaurant/entities/restaurant.py

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from domain.restaurant.value_objects.integration_type import IntegrationType
from domain.restaurant.value_objects.automation_type import AutomationType
from domain.restaurant.value_objects.opening_hours import OpeningHours
from domain.restaurant.entities.integration import Integration
from domain.shared.result import Result


@dataclass
class Restaurant:
    """
    Restaurant Aggregate Root.
    
    Invariantes:
    - Deve ter nome único
    - Deve ter pelo menos uma integração ativa
    - Horários devem ser válidos
    - chave_grupo_empresarial deve ser UUID válido
    """
    
    id: Optional[str]
    name: str
    prompt_default: str
    menu_url: str
    opening_hours: OpeningHours
    integration_type: IntegrationType
    automation_type: AutomationType
    chave_grupo_empresarial: UUID
    canal_master_id: str
    empresa_base_id: str
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    # Integrations (parte do aggregate)
    integrations: List[Integration]
    
    def __post_init__(self):
        """Validar invariantes após criação."""
        self._validate_invariants()
    
    def _validate_invariants(self) -> None:
        """Validar regras de negócio do aggregate."""
        if not self.name or len(self.name) < 3:
            raise ValueError("Nome do restaurante deve ter pelo menos 3 caracteres")
        
        if not self.integrations:
            raise ValueError("Restaurante deve ter pelo menos uma integração")
        
        # Validar que opening_hours é consistente
        self.opening_hours.validate()
    
    def is_open_now(self) -> bool:
        """
        Verifica se restaurante está aberto no momento.
        
        Domain Service seria melhor para isso se envolver lógica complexa.
        """
        return self.opening_hours.is_open_now()
    
    def get_opening_time_today(self) -> Optional[str]:
        """Retorna horário de abertura de hoje."""
        return self.opening_hours.get_opening_time_today()
    
    def change_automation_type(self, new_type: AutomationType) -> Result[None, Exception]:
        """
        Mudar nível de automação.
        
        Regra: Não pode downgrade de ADVANCED para BASIC se houver pedidos em aberto.
        """
        # TODO: Verificar pedidos em aberto (quando Order context existir)
        self.automation_type = new_type
        self.updated_at = datetime.utcnow()
        return Result.success(None)
    
    def activate(self) -> None:
        """Ativar restaurante."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Desativar restaurante."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
```

#### Value Object: IntegrationType

```python
# domain/restaurant/value_objects/integration_type.py

from enum import IntEnum


class IntegrationType(IntEnum):
    """
    Tipo de integração de mensageria.
    
    Value Object - imutável, sem identidade.
    """
    
    META_OFICIAL = 1      # WhatsApp Business API Oficial
    JOIN_DEVELOPER = 2    # Join Developer (atual)
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def display_name(self) -> str:
        """Nome amigável para exibição."""
        return {
            self.META_OFICIAL: "Meta - Oficial",
            self.JOIN_DEVELOPER: "Join Developer"
        }[self]
    
    def supports_typing_indicator(self) -> bool:
        """Verifica se integração suporta indicador de digitação."""
        return self in [self.JOIN_DEVELOPER, self.META_OFICIAL]
```

#### Value Object: AutomationType

```python
# domain/restaurant/value_objects/automation_type.py

from enum import IntEnum


class AutomationType(IntEnum):
    """
    Nível de automação do atendimento.
    
    Value Object - imutável, sem identidade.
    """
    
    BASIC = 1           # Institucional + Link cardápio
    INTERMEDIATE = 2    # + RAG cardápio (sem pedidos)
    ADVANCED = 3        # + Criar pedidos
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def display_name(self) -> str:
        return {
            self.BASIC: "Delivery Básico",
            self.INTERMEDIATE: "Delivery Intermediário",
            self.ADVANCED: "Delivery Avançado"
        }[self]
    
    def can_answer_menu_questions(self) -> bool:
        """Pode responder perguntas sobre produtos do cardápio."""
        return self in [self.INTERMEDIATE, self.ADVANCED]
    
    def can_create_orders(self) -> bool:
        """Pode criar pedidos."""
        return self == self.ADVANCED
```

#### Value Object: OpeningHours

```python
# domain/restaurant/value_objects/opening_hours.py

from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime, time
import json


@dataclass(frozen=True)
class DaySchedule:
    """Horário de um dia específico."""
    opens_at: Optional[time]
    closes_at: Optional[time]
    is_closed: bool = False
    
    def is_open_at(self, check_time: time) -> bool:
        """Verifica se está aberto em determinado horário."""
        if self.is_closed or not self.opens_at or not self.closes_at:
            return False
        
        # Handle overnight schedules (e.g., 23:00 - 02:00)
        if self.closes_at < self.opens_at:
            return check_time >= self.opens_at or check_time <= self.closes_at
        
        return self.opens_at <= check_time <= self.closes_at


@dataclass(frozen=True)
class OpeningHours:
    """
    Horários de funcionamento da semana.
    
    Value Object - imutável, sem identidade.
    
    Exemplo:
    {
        "monday": {"opens_at": "11:00", "closes_at": "23:00"},
        "tuesday": {"opens_at": "11:00", "closes_at": "23:00"},
        "wednesday": {"is_closed": true},
        ...
    }
    """
    
    monday: DaySchedule
    tuesday: DaySchedule
    wednesday: DaySchedule
    thursday: DaySchedule
    friday: DaySchedule
    saturday: DaySchedule
    sunday: DaySchedule
    
    def validate(self) -> None:
        """Validar que horários fazem sentido."""
        for day_name, schedule in self.to_dict().items():
            if not schedule.is_closed:
                if not schedule.opens_at or not schedule.closes_at:
                    raise ValueError(f"{day_name}: deve ter horário de abertura e fechamento")
    
    def is_open_now(self) -> bool:
        """Verifica se está aberto agora."""
        now = datetime.now()
        current_day = now.strftime("%A").lower()
        current_time = now.time()
        
        schedule = getattr(self, current_day)
        return schedule.is_open_at(current_time)
    
    def get_opening_time_today(self) -> Optional[str]:
        """
        Retorna horário de abertura de hoje.
        
        Regra de negócio: Se fechado, retornar apenas horário de HOJE.
        """
        now = datetime.now()
        current_day = now.strftime("%A").lower()
        schedule = getattr(self, current_day)
        
        if schedule.is_closed:
            return None
        
        return schedule.opens_at.strftime("%H:%M") if schedule.opens_at else None
    
    def to_dict(self) -> Dict[str, DaySchedule]:
        """Converter para dicionário."""
        return {
            "monday": self.monday,
            "tuesday": self.tuesday,
            "wednesday": self.wednesday,
            "thursday": self.thursday,
            "friday": self.friday,
            "saturday": self.saturday,
            "sunday": self.sunday,
        }
    
    @classmethod
    def from_json(cls, json_str: str) -> "OpeningHours":
        """Criar a partir de JSON."""
        data = json.loads(json_str)
        # TODO: Parse e criar DaySchedule objects
        pass
```

---

### 2. Messaging Context

**Aggregate Root:** `Conversation`

**Responsabilidade:** Gerenciar conversas e mensagens com clientes

#### Aggregate: Conversation

```python
# domain/messaging/entities/conversation.py

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from uuid import uuid4

from domain.messaging.entities.message import Message
from domain.shared.value_objects.phone_number import PhoneNumber
from domain.shared.result import Result


@dataclass
class Conversation:
    """
    Conversation Aggregate Root.
    
    Invariantes:
    - Deve ter pelo menos uma mensagem
    - Messages são ordenadas por timestamp
    - Não pode ter gaps no histórico
    """
    
    id: str
    restaurant_id: str
    customer_phone: PhoneNumber
    is_ai_active: bool
    ai_disabled_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Messages (entidades dentro do aggregate)
    messages: List[Message] = field(default_factory=list)
    
    def add_message(self, message: Message) -> Result[None, Exception]:
        """
        Adicionar mensagem à conversa.
        
        Invariante: Mensagens devem ser cronológicas.
        """
        if self.messages and message.timestamp < self.messages[-1].timestamp:
            return Result.failure(
                ValueError("Mensagem fora de ordem cronológica")
            )
        
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return Result.success(None)
    
    def should_ai_respond(self) -> bool:
        """
        Verificar se IA deve responder.
        
        Regras:
        - Se ai_disabled_until está no futuro: NÃO
        - Se is_ai_active é False: NÃO
        - Caso contrário: SIM
        """
        if not self.is_ai_active:
            return False
        
        if self.ai_disabled_until and datetime.utcnow() < self.ai_disabled_until:
            return False
        
        return True
    
    def disable_ai_for_hours(self, hours: int = 12) -> None:
        """
        Desativar IA por N horas.
        
        Caso de uso: Humano assumiu a conversa.
        """
        self.is_ai_active = False
        self.ai_disabled_until = datetime.utcnow() + timedelta(hours=hours)
        self.updated_at = datetime.utcnow()
    
    def enable_ai(self) -> None:
        """Reativar IA."""
        self.is_ai_active = True
        self.ai_disabled_until = None
        self.updated_at = datetime.utcnow()
    
    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Obter últimas N mensagens para contexto."""
        return self.messages[-limit:] if self.messages else []
    
    def get_messages_after(self, timestamp: datetime) -> List[Message]:
        """Obter mensagens após determinado timestamp."""
        return [msg for msg in self.messages if msg.timestamp > timestamp]
```

#### Entity: Message

```python
# domain/messaging/entities/message.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class MessageDirection(str, Enum):
    """Direção da mensagem."""
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class MessageSource(str, Enum):
    """Fonte da mensagem."""
    APP = "app"          # WhatsApp app
    PHONE = "phone"      # Telefone (humano)
    AI = "ai"            # Bot/IA


@dataclass
class Message:
    """
    Message Entity (parte do Conversation aggregate).
    
    Não é um Aggregate Root, sempre acessada via Conversation.
    """
    
    id: str
    conversation_id: str
    body: str
    direction: MessageDirection
    source: MessageSource
    from_me: bool
    timestamp: datetime
    created_at: datetime
    
    # Metadata
    external_id: Optional[str] = None  # ID da Join/WhatsApp
    media_url: Optional[str] = None
    
    def is_from_customer(self) -> bool:
        """Mensagem veio do cliente."""
        return self.direction == MessageDirection.INCOMING and not self.from_me
    
    def is_from_human_operator(self) -> bool:
        """Mensagem enviada por humano (funcionário)."""
        return self.source == MessageSource.PHONE
    
    def should_ignore(self) -> bool:
        """
        Verificar se mensagem deve ser ignorada.
        
        Regras:
        - from_me=True → IGNORAR
        - source=phone → IGNORAR (e desativar IA)
        """
        return self.from_me or self.source == MessageSource.PHONE
```

---

### 3. Assistant Context

**Responsabilidade:** Orquestrar respostas da IA

#### Domain Service: ResponseOrchestrator

```python
# domain/assistant/services/response_orchestrator.py

from typing import Optional
from datetime import datetime

from domain.restaurant.entities.restaurant import Restaurant
from domain.messaging.entities.conversation import Conversation
from domain.assistant.strategies.base_strategy import BaseStrategy
from domain.assistant.strategies.basic_strategy import BasicStrategy
from domain.shared.result import Result


class ResponseOrchestrator:
    """
    Domain Service para orquestrar geração de respostas.
    
    Fluxo:
    1. Verificar horário de funcionamento
    2. Buscar contexto (memória)
    3. Selecionar estratégia adequada
    4. Gerar resposta
    """
    
    def __init__(
        self,
        basic_strategy: BasicStrategy,
        # intermediate_strategy: IntermediateStrategy,  # Futuro
        # advanced_strategy: AdvancedStrategy,          # Futuro
    ):
        self.basic_strategy = basic_strategy
    
    def orchestrate_response(
        self,
        restaurant: Restaurant,
        conversation: Conversation,
        user_message: str,
        context: Optional[dict] = None
    ) -> Result[str, Exception]:
        """
        Orquestrar geração de resposta.
        
        Args:
            restaurant: Restaurante do tenant
            conversation: Conversa atual
            user_message: Mensagem do usuário
            context: Contexto adicional (memória, etc.)
        
        Returns:
            Result com resposta gerada ou erro
        """
        # 1. Verificar horário
        if not restaurant.is_open_now():
            opening_time = restaurant.get_opening_time_today()
            if opening_time:
                return Result.success(
                    f"Estamos fechados no momento. Hoje abrimos às {opening_time}"
                )
            else:
                return Result.success(
                    "Estamos fechados hoje. Confira nosso horário de funcionamento."
                )
        
        # 2. Verificar se IA pode responder
        if not conversation.should_ai_respond():
            return Result.failure(
                Exception("IA desativada para esta conversa")
            )
        
        # 3. Selecionar estratégia
        strategy = self._select_strategy(restaurant.automation_type)
        
        # 4. Gerar resposta
        return strategy.generate_response(
            restaurant=restaurant,
            conversation=conversation,
            user_message=user_message,
            context=context or {}
        )
    
    def _select_strategy(self, automation_type) -> BaseStrategy:
        """Selecionar estratégia baseada no nível de automação."""
        # Por enquanto, apenas BASIC
        return self.basic_strategy
        
        # Futuro:
        # if automation_type == AutomationType.BASIC:
        #     return self.basic_strategy
        # elif automation_type == AutomationType.INTERMEDIATE:
        #     return self.intermediate_strategy
        # elif automation_type == AutomationType.ADVANCED:
        #     return self.advanced_strategy
```

#### Strategy: BasicStrategy

```python
# domain/assistant/strategies/basic_strategy.py

from abc import ABC, abstractmethod
from domain.restaurant.entities.restaurant import Restaurant
from domain.messaging.entities.conversation import Conversation
from domain.shared.result import Result


class BaseStrategy(ABC):
    """
    Strategy abstrata para geração de respostas.
    
    Strategy Pattern: Encapsula algoritmos diferentes.
    """
    
    @abstractmethod
    def generate_response(
        self,
        restaurant: Restaurant,
        conversation: Conversation,
        user_message: str,
        context: dict
    ) -> Result[str, Exception]:
        """Gerar resposta baseada na estratégia."""
        pass


class BasicStrategy(BaseStrategy):
    """
    Estratégia BÁSICA de automação.
    
    Pode fazer:
    - Recepcionar cliente
    - Informações institucionais
    - Sugerir link do cardápio
    
    NÃO pode:
    - Falar sobre produtos
    - Anotar pedidos
    """
    
    def __init__(self, ai_client, institutional_data_service):
        """
        Args:
            ai_client: Cliente da IA (Gemini)
            institutional_data_service: Serviço para buscar dados da Tacto API
        """
        self.ai_client = ai_client
        self.institutional_data_service = institutional_data_service
    
    def generate_response(
        self,
        restaurant: Restaurant,
        conversation: Conversation,
        user_message: str,
        context: dict
    ) -> Result[str, Exception]:
        """
        Gerar resposta usando IA com limitações do nível BASIC.
        
        Fluxo:
        1. Buscar dados institucionais (Tacto API)
        2. Montar prompt com restrições
        3. Chamar IA
        4. Validar resposta (não deve falar de produtos)
        """
        try:
            # 1. Buscar dados institucionais
            institutional_result = self.institutional_data_service.get_data(
                restaurant.chave_grupo_empresarial,
                restaurant.empresa_base_id
            )
            
            if not institutional_result.is_success:
                return Result.failure(institutional_result.error)
            
            institutional_data = institutional_result.value
            
            # 2. Montar prompt
            system_prompt = self._build_system_prompt(restaurant, institutional_data)
            conversation_history = self._format_conversation(conversation)
            
            # 3. Chamar IA
            ai_response = self.ai_client.generate(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message=user_message
            )
            
            # 4. Validar resposta (garantir que não fala de produtos)
            validated_response = self._validate_response(ai_response)
            
            return Result.success(validated_response)
        
        except Exception as e:
            return Result.failure(e)
    
    def _build_system_prompt(self, restaurant: Restaurant, institutional_data: dict) -> str:
        """
        Construir prompt do sistema com restrições do nível BASIC.
        """
        return f"""
Você é um assistente virtual do restaurante {restaurant.name}.

IMPORTANTE - REGRAS OBRIGATÓRIAS:
1. Você PODE:
   - Recepcionar clientes com cordialidade
   - Informar endereço: {institutional_data.get('address', 'N/A')}
   - Informar telefone: {institutional_data.get('phone', 'N/A')}
   - Informar horário de funcionamento
   - Informar formas de pagamento: {institutional_data.get('payment_methods', 'N/A')}
   - Sugerir link do cardápio: {restaurant.menu_url} (evite repetir sem o cliente pedir)

2. Você NÃO PODE:
   - Falar sobre produtos específicos do cardápio
   - Anotar pedidos
   - Prometer entregas ou prazos
   - Mencionar concorrentes
   - Usar palavrões ou linguagem inadequada
   - Usar gírias informais

3. TOM DE VOZ:
   - Formal mas amigável
   - Use no máximo 1-2 emojis por mensagem
   - Respostas claras e diretas

{restaurant.prompt_default}
"""
    
    def _format_conversation(self, conversation: Conversation) -> list:
        """Formatar histórico da conversa para a IA."""
        recent_messages = conversation.get_recent_messages(limit=10)
        
        return [
            {
                "role": "user" if msg.is_from_customer() else "assistant",
                "content": msg.body
            }
            for msg in recent_messages
        ]
    
    def _validate_response(self, response: str) -> str:
        """
        Validar que resposta não viola regras do nível BASIC.
        
        TODO: Implementar verificações de conteúdo inadequado.
        """
        # Verificar palavrões
        # Verificar menção a produtos (se necessário)
        # Por enquanto, retornar direto
        return response
```

---

## 🗄️ REPOSITORY PATTERN

### Interface (Domain Layer)

```python
# domain/restaurant/repository.py

from abc import ABC, abstractmethod
from typing import List, Optional
from domain.restaurant.entities.restaurant import Restaurant
from domain.shared.result import Result


class RestaurantRepository(ABC):
    """
    Repository interface para Restaurant.
    
    Padrão: Repository Pattern
    - Interface no domínio
    - Implementação na infraestrutura
    """
    
    @abstractmethod
    async def save(self, restaurant: Restaurant) -> Result[Restaurant, Exception]:
        """Salvar ou atualizar restaurante."""
        pass
    
    @abstractmethod
    async def find_by_id(self, restaurant_id: str) -> Result[Optional[Restaurant], Exception]:
        """Buscar restaurante por ID."""
        pass
    
    @abstractmethod
    async def find_by_canal_master_id(self, canal_master_id: str) -> Result[Optional[Restaurant], Exception]:
        """Buscar restaurante por canal_master_id (usado no webhook)."""
        pass
    
    @abstractmethod
    async def find_all(self) -> Result[List[Restaurant], Exception]:
        """Listar todos restaurantes."""
        pass
    
    @abstractmethod
    async def delete(self, restaurant_id: str) -> Result[bool, Exception]:
        """Deletar restaurante."""
        pass
```

### Implementação (Infrastructure Layer)

```python
# infrastructure/persistence/postgres/repositories/restaurant_repository.py

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.restaurant.entities.restaurant import Restaurant
from domain.restaurant.repository import RestaurantRepository
from domain.shared.result import Result
from infrastructure.persistence.postgres.models.restaurant_model import RestaurantModel


class PostgresRestaurantRepository(RestaurantRepository):
    """
    Implementação PostgreSQL do RestaurantRepository.
    
    Responsabilidades:
    - Mapear domain entities <-> SQLAlchemy models
    - Executar queries
    - Transaction management (se necessário)
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(self, restaurant: Restaurant) -> Result[Restaurant, Exception]:
        """Salvar restaurante."""
        try:
            # Converter domain entity -> SQLAlchemy model
            model = self._to_model(restaurant)
            
            self.session.add(model)
            await self.session.flush()
            
            # Converter de volta para domain entity
            saved_restaurant = self._to_entity(model)
            
            return Result.success(saved_restaurant)
        
        except Exception as e:
            return Result.failure(e)
    
    async def find_by_id(self, restaurant_id: str) -> Result[Optional[Restaurant], Exception]:
        """Buscar por ID."""
        try:
            stmt = select(RestaurantModel).where(RestaurantModel.id == restaurant_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if not model:
                return Result.success(None)
            
            restaurant = self._to_entity(model)
            return Result.success(restaurant)
        
        except Exception as e:
            return Result.failure(e)
    
    def _to_model(self, restaurant: Restaurant) -> RestaurantModel:
        """Converter domain entity -> SQLAlchemy model."""
        return RestaurantModel(
            id=restaurant.id,
            name=restaurant.name,
            prompt_default=restaurant.prompt_default,
            menu_url=restaurant.menu_url,
            opening_hours_json=restaurant.opening_hours.to_json(),
            integration_type=restaurant.integration_type.value,
            automation_type=restaurant.automation_type.value,
            chave_grupo_empresarial=str(restaurant.chave_grupo_empresarial),
            canal_master_id=restaurant.canal_master_id,
            empresa_base_id=restaurant.empresa_base_id,
            is_active=restaurant.is_active,
            created_at=restaurant.created_at,
            updated_at=restaurant.updated_at
        )
    
    def _to_entity(self, model: RestaurantModel) -> Restaurant:
        """Converter SQLAlchemy model -> domain entity."""
        return Restaurant(
            id=model.id,
            name=model.name,
            prompt_default=model.prompt_default,
            menu_url=model.menu_url,
            opening_hours=OpeningHours.from_json(model.opening_hours_json),
            integration_type=IntegrationType(model.integration_type),
            automation_type=AutomationType(model.automation_type),
            chave_grupo_empresarial=UUID(model.chave_grupo_empresarial),
            canal_master_id=model.canal_master_id,
            empresa_base_id=model.empresa_base_id,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            integrations=[]  # TODO: carregar integrations
        )
```

---

## 🔄 DEPENDENCY FLOW

### Regra de Ouro

```
Interface Layer    →  depends on  →  Application Layer
Application Layer  →  depends on  →  Domain Layer
Infrastructure     →  implements  →  Domain Interfaces

Domain NUNCA depende de nada externo
```

### Dependency Injection Container

```python
# tacto/container.py

from dependency_injector import containers, providers
from infrastructure.config.settings import Settings
from infrastructure.persistence.postgres.database import Database
from infrastructure.cache.redis.redis_client import RedisClient
from infrastructure.external_apis.tacto.tacto_client import TactoClient
from infrastructure.ai.gemini.gemini_client import GeminiClient

# Repositories
from infrastructure.persistence.postgres.repositories.restaurant_repository import (
    PostgresRestaurantRepository
)

# Domain Services
from domain.assistant.services.response_orchestrator import ResponseOrchestrator
from domain.assistant.strategies.basic_strategy import BasicStrategy

# Use Cases
from application.use_cases.messaging.process_incoming_message import ProcessIncomingMessage


class Container(containers.DeclarativeContainer):
    """
    Dependency Injection Container.
    
    Padrão: Dependency Inversion Principle (SOLID)
    """
    
    # Config
    config = providers.Configuration()
    settings = providers.Singleton(Settings)
    
    # Infrastructure - Database
    database = providers.Singleton(
        Database,
        settings=settings
    )
    
    # Infrastructure - Redis
    redis_client = providers.Singleton(
        RedisClient,
        url=settings.provided.redis_url
    )
    
    # Infrastructure - External APIs
    tacto_client = providers.Singleton(
        TactoClient,
        settings=settings
    )
    
    gemini_client = providers.Singleton(
        GeminiClient,
        api_key=settings.provided.gemini_api_key
    )
    
    # Repositories (Infrastructure implements Domain interfaces)
    restaurant_repository = providers.Factory(
        PostgresRestaurantRepository,
        session=database.provided.session
    )
    
    # Domain Services
    basic_strategy = providers.Factory(
        BasicStrategy,
        ai_client=gemini_client,
        institutional_data_service=tacto_client.provided.institutional_service
    )
    
    response_orchestrator = providers.Factory(
        ResponseOrchestrator,
        basic_strategy=basic_strategy
    )
    
    # Use Cases
    process_incoming_message = providers.Factory(
        ProcessIncomingMessage,
        restaurant_repository=restaurant_repository,
        conversation_repository=...,  # TODO
        response_orchestrator=response_orchestrator,
        message_buffer_service=...,  # TODO
    )
```

---

## 🎨 PATTERNS APLICADOS

### 1. **Aggregate Pattern** (DDD)
- `Restaurant` é Aggregate Root
- `Conversation` é Aggregate Root
- Entities dentro do aggregate só são acessadas via root

### 2. **Value Object Pattern** (DDD)
- `IntegrationType`, `AutomationType`, `OpeningHours`
- Imutáveis, sem identidade própria
- Comparação por valor

### 3. **Repository Pattern** (DDD)
- Interface no domínio
- Implementação na infraestrutura
- Abstração de persistência

### 4. **Strategy Pattern** (GoF)
- `BasicStrategy`, `IntermediateStrategy`, `AdvancedStrategy`
- Encapsula algoritmos intercambiáveis
- Seleção em runtime

### 5. **Result Pattern** (Functional)
- `Result<T, E>` para error handling
- Evita exceptions para fluxo de negócio
- Composable (map, flatMap)

### 6. **Dependency Inversion** (SOLID)
- Domínio define interfaces
- Infraestrutura implementa
- Injeção via DI container

### 7. **Use Case Pattern** (Clean Architecture)
- Cada caso de uso é uma classe
- Encapsula lógica da aplicação
- Orquestra domain services

---

## 📏 CONVENÇÕES DE CÓDIGO

### Naming

```python
# Entities: PascalCase
class Restaurant:
    pass

# Value Objects: PascalCase
class OpeningHours:
    pass

# Services: Sufixo "Service"
class MessageBufferService:
    pass

# Repositories: Sufixo "Repository"
class RestaurantRepository:
    pass

# Use Cases: Verbo no infinitivo
class ProcessIncomingMessage:
    async def execute(self, ...):
        pass
```

### Type Hints (Obrigatório)

```python
from typing import List, Optional, Dict, Any

def process(
    message: str,
    restaurant_id: str,
    context: Optional[Dict[str, Any]] = None
) -> Result[Response, Exception]:
    ...
```

### Async/Await

```python
# Use async para I/O-bound operations
async def find_by_id(self, id: str) -> Result[Optional[Restaurant], Exception]:
    result = await self.session.execute(stmt)
    ...
```

---

## 🚀 PRÓXIMOS PASSOS

1. Implementar todas as entities e value objects
2. Criar repository interfaces
3. Implementar repositories (PostgreSQL)
4. Criar domain services
5. Implementar use cases
6. Criar testes unitários (domínio)
7. Criar testes de integração (infraestrutura)

---

**Mantido por:** Engineering Team  
**Última Revisão:** 2026-03-27
