# 📐 TactoFlow - Regras de Negócio

**Versão:** 0.0.1  
**Última Atualização:** 2026-03-27  
**Status:** Documentação Oficial de Regras de Negócio

---

## 📋 ÍNDICE

1. [Princípios Gerais](#princípios-gerais)
2. [Restaurant Management](#restaurant-management)
3. [Message Processing](#message-processing)
4. [AI Response Generation](#ai-response-generation)
5. [Opening Hours](#opening-hours)
6. [Automation Levels](#automation-levels)
7. [Human Intervention](#human-intervention)
8. [Message Buffer](#message-buffer)
9. [Content Filtering](#content-filtering)
10. [Multi-tenancy](#multi-tenancy)
11. [Memory Management](#memory-management)
12. [External API Integration](#external-api-integration)

---

## 🎯 PRINCÍPIOS GERAIS

### Linguagem Ubíqua (Ubiquitous Language)

Termos do negócio que **DEVEM** ser usados no código:

| Termo Negócio | Uso no Código | Definição |
|---------------|---------------|-----------|
| Restaurante | `Restaurant` | Tenant do sistema |
| Conversa | `Conversation` | Thread de mensagens com cliente |
| Mensagem | `Message` | Mensagem individual WhatsApp |
| Nível de Automação | `AutomationType` | BASIC/INTERMEDIATE/ADVANCED |
| Tipo de Integração | `IntegrationType` | JOIN/WHATSAPP_BUSINESS |
| Horário de Funcionamento | `OpeningHours` | Horários da semana |
| Cardápio | `Menu` | Lista de produtos/categorias |
| Dados Institucionais | `InstitutionalData` | Endereço, telefone, etc. |
| Assistente | `Assistant` | IA que responde clientes |
| Estratégia | `Strategy` | Lógica de resposta por nível |

### Invariantes Globais

**Regras que NUNCA podem ser violadas:**

1. ✅ **Todo dado pertence a um restaurante** (`restaurant_id` sempre presente)
2. ✅ **Mensagens `fromMe=true` são sempre ignoradas** (evitar loop infinito)
3. ✅ **Humano > IA** (intervenção humana desativa IA por 12h)
4. ✅ **Horário fora de funcionamento = resposta simplificada** (apenas horário do dia)
5. ✅ **Nível BASIC não fala de produtos** (apenas institucional + link)
6. ✅ **Buffer agrupa mensagens < 5s** (evitar múltiplas respostas)
7. ✅ **Conteúdo inadequado é bloqueado** (palavrões, concorrência)

---

## 🏪 RESTAURANT MANAGEMENT

### BR-R001: Criação de Restaurante

**Regra:** Todo restaurante deve ter configuração completa e válida

**Invariantes:**
- ✅ Nome único (case-insensitive)
- ✅ Nome com mínimo 3 caracteres
- ✅ `chave_grupo_empresarial` deve ser UUID válido
- ✅ `canal_master_id` deve ser único
- ✅ `menu_url` deve ser URL válida
- ✅ Pelo menos uma integração ativa
- ✅ Horários de funcionamento válidos

**Validação:**
```python
def validate_restaurant_creation(restaurant: Restaurant) -> Result[None, Exception]:
    if not restaurant.name or len(restaurant.name) < 3:
        return Result.failure(ValueError("Nome inválido"))
    
    if not is_valid_uuid(restaurant.chave_grupo_empresarial):
        return Result.failure(ValueError("chave_grupo_empresarial inválida"))
    
    if not restaurant.opening_hours.validate():
        return Result.failure(ValueError("Horários inválidos"))
    
    return Result.success(None)
```

**Exemplo Válido:**
```json
{
  "name": "Pizzaria do João",
  "prompt_default": "Você é um atendente cordial da Pizzaria do João...",
  "menu_url": "https://cardapio.pizzariadojoao.com.br",
  "opening_hours": {
    "monday": {"opens_at": "18:00", "closes_at": "23:00"},
    "tuesday": {"opens_at": "18:00", "closes_at": "23:00"},
    "wednesday": {"is_closed": true},
    ...
  },
  "integration_type": 2,
  "automation_type": 1,
  "chave_grupo_empresarial": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "canal_master_id": "canal-123",
  "empresa_base_id": "1"
}
```

---

### BR-R002: Ativação/Desativação

**Regra:** Restaurante pode ser desativado temporariamente

**Comportamento:**
- **Ativo (`is_active=true`):** Processa mensagens normalmente
- **Inativo (`is_active=false`):** Não processa mensagens (mas mantém histórico)

**Casos de Uso:**
- Manutenção temporária
- Período de férias
- Suspensão por inadimplência (futuro)

---

### BR-R003: Mudança de Nível de Automação

**Regra:** Pode mudar nível, mas com validações

**Restrições:**
- ❌ **Downgrade ADVANCED→BASIC:** Não permitir se houver pedidos em aberto
- ✅ **Upgrade BASIC→INTERMEDIATE:** Permitir sempre
- ✅ **Upgrade INTERMEDIATE→ADVANCED:** Permitir se integração com pagamento configurada (futuro)

**Implementação:**
```python
def change_automation_type(
    restaurant: Restaurant,
    new_type: AutomationType,
    order_repository: OrderRepository
) -> Result[None, Exception]:
    
    # Verificar downgrade
    if new_type.value < restaurant.automation_type.value:
        # Verificar pedidos em aberto
        open_orders = order_repository.count_open_orders(restaurant.id)
        if open_orders > 0:
            return Result.failure(
                ValueError(f"Não pode fazer downgrade com {open_orders} pedidos em aberto")
            )
    
    restaurant.automation_type = new_type
    return Result.success(None)
```

---

## 💬 MESSAGE PROCESSING

### BR-M001: Validação de Mensagem Recebida

**Regra:** Nem todas mensagens recebidas devem ser processadas

**Fluxo de Decisão:**
```
Mensagem Recebida
    │
    ├─→ fromMe == true? ────→ IGNORAR (não processar)
    │
    ├─→ source == "phone"? ─→ DESATIVAR IA por 12h + IGNORAR
    │
    ├─→ IA desativada? ─────→ IGNORAR
    │
    ├─→ Restaurante inativo? → IGNORAR
    │
    └─→ PROCESSAR
```

**Implementação:**
```python
def should_process_message(
    message: IncomingMessage,
    conversation: Conversation,
    restaurant: Restaurant
) -> bool:
    # 1. Mensagem enviada por nós mesmos
    if message.from_me:
        return False
    
    # 2. Humano assumiu (desativar IA)
    if message.source == "phone":
        conversation.disable_ai_for_hours(12)
        return False
    
    # 3. IA desativada
    if not conversation.should_ai_respond():
        return False
    
    # 4. Restaurante inativo
    if not restaurant.is_active:
        return False
    
    return True
```

---

### BR-M002: Estrutura de Mensagem

**Regra:** Mensagens seguem estrutura padronizada

**Campos Obrigatórios:**
- `id`: UUID único
- `conversation_id`: FK para conversa
- `body`: Texto da mensagem
- `direction`: INCOMING | OUTGOING
- `source`: APP | PHONE | AI
- `from_me`: boolean
- `timestamp`: datetime UTC

**Campos Opcionais:**
- `external_id`: ID da plataforma (Join/WhatsApp)
- `media_url`: URL de mídia (imagem, áudio, etc.)
- `metadata`: JSON com dados extras

---

### BR-M003: Ordenação de Mensagens

**Regra:** Mensagens devem ser cronologicamente ordenadas

**Invariante:** Não pode adicionar mensagem com `timestamp` anterior à última

```python
def add_message_to_conversation(
    conversation: Conversation,
    message: Message
) -> Result[None, Exception]:
    
    if conversation.messages:
        last_message = conversation.messages[-1]
        if message.timestamp < last_message.timestamp:
            return Result.failure(
                ValueError("Mensagem fora de ordem cronológica")
            )
    
    conversation.messages.append(message)
    return Result.success(None)
```

---

## 🤖 AI RESPONSE GENERATION

### BR-AI001: Fluxo de Geração de Resposta

**Regra:** Resposta passa por pipeline de validações

**Pipeline:**
```
1. Verificar horário de funcionamento
    ├─→ Fechado? → Retornar "Estamos fechados. Hoje abrimos às XX:XX"
    └─→ Aberto? → Continuar
    
2. Buscar contexto (últimas 10 mensagens)

3. Buscar dados institucionais (Tacto API)
    └─→ Cache por 1h

4. Selecionar estratégia (baseada em automation_type)
    ├─→ BASIC → BasicStrategy
    ├─→ INTERMEDIATE → IntermediateStrategy (futuro)
    └─→ ADVANCED → AdvancedStrategy (futuro)

5. Gerar resposta (IA)

6. Validar conteúdo
    ├─→ Palavrões? → Filtrar
    ├─→ Menção a concorrente? → Rejeitar
    └─→ Válido? → Continuar

7. Simular digitação (2-4s)

8. Enviar resposta

9. Salvar no histórico
```

---

### BR-AI002: Prompt System

**Regra:** Prompt é montado dinamicamente com contexto

**Estrutura do Prompt:**
```
[CONFIGURAÇÃO DO RESTAURANTE]
- Nome: {restaurant.name}
- Prompt personalizado: {restaurant.prompt_default}

[DADOS INSTITUCIONAIS]
- Endereço: {institutional_data.address}
- Telefone: {institutional_data.phone}
- Formas de pagamento: {institutional_data.payment_methods}
- Link do cardápio: {restaurant.menu_url}

[RESTRIÇÕES DO NÍVEL DE AUTOMAÇÃO]
{automation_level_restrictions}

[REGRAS DE TOM DE VOZ]
- Formal mas amigável
- Máximo 1-2 emojis por mensagem
- Sem gírias informais
- Sem palavrões
- Não mencionar concorrentes

[CONTEXTO DA CONVERSA]
{last_10_messages}

[MENSAGEM DO USUÁRIO]
{user_message}
```

---

### BR-AI003: Detecção de Intenção

**Regra:** Sistema tenta detectar intenção do usuário

**Intenções Principais:**
- `GREETING` - Saudação inicial
- `ASK_MENU` - Pergunta sobre cardápio
- `ASK_HOURS` - Pergunta sobre horário
- `ASK_ADDRESS` - Pergunta sobre localização
- `ASK_PAYMENT` - Pergunta sobre formas de pagamento
- `PLACE_ORDER` - Tentar fazer pedido (apenas ADVANCED)
- `COMPLAINT` - Reclamação
- `OTHER` - Não classificada

**Uso:**
- Ajustar tom da resposta
- Routing para estratégia específica
- Métricas e analytics

```python
def detect_intent(message: str) -> Intent:
    # Usar IA ou regex patterns
    if any(word in message.lower() for word in ["oi", "olá", "bom dia"]):
        return Intent.GREETING
    
    if any(word in message.lower() for word in ["cardápio", "menu", "produtos"]):
        return Intent.ASK_MENU
    
    # ... outros patterns
    
    return Intent.OTHER
```

---

## 🕐 OPENING HOURS

### BR-OH001: Validação de Horários

**Regra:** Horários devem ser logicamente válidos

**Validações:**
```python
def validate_opening_hours(hours: OpeningHours) -> Result[None, Exception]:
    for day_name, schedule in hours.to_dict().items():
        if not schedule.is_closed:
            # Deve ter abertura e fechamento
            if not schedule.opens_at or not schedule.closes_at:
                return Result.failure(
                    ValueError(f"{day_name}: falta horário de abertura ou fechamento")
                )
            
            # Não pode abrir e fechar no mesmo horário
            if schedule.opens_at == schedule.closes_at:
                return Result.failure(
                    ValueError(f"{day_name}: horários iguais")
                )
    
    return Result.success(None)
```

**Casos Especiais:**
- ✅ **Overnight:** `opens_at="23:00"`, `closes_at="02:00"` (válido)
- ✅ **24 horas:** Usar `opens_at="00:00"`, `closes_at="23:59"`

---

### BR-OH002: Resposta Fora do Horário

**Regra:** Se fechado, retornar APENAS horário do dia atual

**❌ ERRADO:**
```
"Estamos fechados. Funcionamos:
Segunda a Sexta: 11h às 23h
Sábado: 12h às 00h
Domingo: Fechado"
```

**✅ CORRETO:**
```
"Estamos fechados no momento. Hoje abrimos às 18h"
```

**Implementação:**
```python
def generate_closed_message(restaurant: Restaurant) -> str:
    opening_time = restaurant.get_opening_time_today()
    
    if opening_time:
        return f"Estamos fechados no momento. Hoje abrimos às {opening_time}"
    else:
        return "Estamos fechados hoje. Volte amanhã!"
```

**Razão:** Evitar informação excessiva e confusão do cliente

---

### BR-OH003: Timezone

**Regra:** Sempre usar timezone do restaurante (futuro)

**Implementação Atual:**
- Usar `America/Sao_Paulo` (UTC-3) como padrão
- **Futuro:** Adicionar campo `timezone` em Restaurant

```python
from zoneinfo import ZoneInfo

def is_open_now(restaurant: Restaurant) -> bool:
    tz = ZoneInfo(restaurant.timezone or "America/Sao_Paulo")
    now = datetime.now(tz)
    # ... verificar horário
```

---

## 🎚️ AUTOMATION LEVELS

### BR-AL001: Nível BASIC (Delivery Básico)

**Implementar AGORA - Prioridade Total**

**Pode fazer:**
- ✅ Recepcionar cliente cordialmente
- ✅ Informar endereço, telefone, horários
- ✅ Informar formas de pagamento
- ✅ Sugerir link do cardápio (evitar repetir)
- ✅ Responder dúvidas institucionais

**NÃO pode fazer:**
- ❌ Falar sobre produtos específicos do cardápio
- ❌ Responder "qual o preço da pizza de calabresa?"
- ❌ Anotar pedidos
- ❌ Calcular preços ou frete

**RAG (Retrieval Augmented Generation):**
- Apenas dados institucionais
- Não incluir cardápio

**Exemplo de Conversa:**
```
Cliente: Olá!
Bot: Olá! Bem-vindo à Pizzaria do João! Como posso ajudar? 😊

Cliente: Qual o preço da pizza de calabresa?
Bot: Para consultar nossos produtos e preços, acesse nosso cardápio: 
     https://cardapio.pizzariadojoao.com.br
     
Cliente: Qual o endereço?
Bot: Estamos localizados na Rua das Flores, 123 - Centro
     Funcionamos de terça a domingo, das 18h às 23h
```

---

### BR-AL002: Nível INTERMEDIATE (Delivery Intermediário)

**NÃO IMPLEMENTAR AGORA - Backlog Futuro**

**Adiciona ao BASIC:**
- ✅ RAG com cardápio completo
- ✅ Responder perguntas sobre produtos
- ✅ Sugerir combos/promoções
- ✅ Informar ingredientes, tamanhos, preços

**Continua NÃO fazendo:**
- ❌ Anotar pedidos

**Exemplo:**
```
Cliente: Qual o preço da pizza de calabresa?
Bot: Temos a Pizza de Calabresa nos seguintes tamanhos:
     - Pequena (4 fatias): R$ 25,00
     - Média (6 fatias): R$ 35,00
     - Grande (8 fatias): R$ 45,00
     
     Para fazer seu pedido, acesse: [link]
```

---

### BR-AL003: Nível ADVANCED (Delivery Avançado)

**NÃO IMPLEMENTAR AGORA - Backlog Futuro**

**Adiciona ao INTERMEDIATE:**
- ✅ Anotar pedido completo
- ✅ Validar endereço de entrega
- ✅ Calcular frete
- ✅ Gerar link de pagamento
- ✅ Confirmar pedido via API Tacto

**Flow de Pedido:**
```
1. Cliente escolhe produtos
2. Bot confirma itens e calcula subtotal
3. Bot pergunta endereço
4. Bot valida endereço (API Tacto)
5. Bot calcula frete
6. Bot apresenta total
7. Bot pergunta forma de pagamento
8. Bot gera link de pagamento (se PIX/cartão)
9. Bot cria pedido na API Tacto
10. Bot confirma pedido e tempo estimado
```

---

## 👤 HUMAN INTERVENTION

### BR-HI001: Detecção de Intervenção Humana

**Regra:** Se funcionário responder pelo telefone, IA deve pausar

**Detecção:**
```python
if message.source == "phone":
    # Humano assumiu
    conversation.disable_ai_for_hours(12)
    log.info(f"Human intervention detected for {conversation.id}")
    return  # Não processar
```

**Indicadores:**
- `source == "phone"` (mensagem veio do celular físico)
- **Não usar `fromMe`** (pode ser confundido com bot)

---

### BR-HI002: Duração da Pausa

**Regra:** IA fica pausada por 12 horas

**Comportamento:**
```python
@dataclass
class Conversation:
    is_ai_active: bool
    ai_disabled_until: Optional[datetime]
    
    def disable_ai_for_hours(self, hours: int = 12):
        self.is_ai_active = False
        self.ai_disabled_until = datetime.utcnow() + timedelta(hours=hours)
```

**Reativação:**
- **Automática:** Após 12h
- **Manual:** Endpoint admin `POST /admin/conversations/{id}/enable-ai`

---

### BR-HI003: Notificação de Takeover

**Regra:** Quando humano assume, notificar equipe (futuro)

**Implementação Futura:**
- Webhook para sistema interno
- Email/SMS para gerente
- Dashboard com takeovers em tempo real

---

## 🔄 MESSAGE BUFFER

### BR-BUF001: Agrupamento de Mensagens

**Regra:** Mensagens com < 5s de diferença são agrupadas

**Objetivo:** Evitar múltiplas respostas fragmentadas

**Comportamento:**
```
[10:00:00] Cliente: "Oi"
           → Timer inicia (5s)
           
[10:00:02] Cliente: "Tudo bem?"
           → Timer reseta (5s)
           
[10:00:04] Cliente: "Quero fazer um pedido"
           → Timer reseta (5s)
           
[10:00:09] → Timer expira
           → Buffer flush: "Oi Tudo bem? Quero fazer um pedido"
           → IA processa TUDO de uma vez
           → Envia UMA resposta contextualizada
```

---

### BR-BUF002: Implementação com Redis

**Regra:** Buffer usa Redis com TTL

**Estrutura:**
```python
# Key pattern
buffer_key = f"buffer:{restaurant_id}:{customer_phone}"

# Value: lista de mensagens
messages = ["Oi", "Tudo bem?", "Quero fazer um pedido"]

# TTL: 5 segundos
redis.setex(buffer_key, 5, json.dumps(messages))

# Timer: Background task verifica expiração
```

**Algoritmo:**
```python
async def add_to_buffer(
    restaurant_id: str,
    customer_phone: str,
    message: str,
    redis: Redis
):
    buffer_key = f"buffer:{restaurant_id}:{customer_phone}"
    
    # Adicionar mensagem ao buffer
    redis.lpush(buffer_key, message)
    
    # Resetar TTL
    redis.expire(buffer_key, 5)
    
    # Agendar flush (se ainda não agendado)
    if not redis.exists(f"timer:{buffer_key}"):
        await schedule_flush(buffer_key, delay=5)
```

---

### BR-BUF003: Flush do Buffer

**Regra:** Ao expirar timer, processar todas mensagens juntas

```python
async def flush_buffer(
    buffer_key: str,
    redis: Redis,
    process_message_use_case: ProcessIncomingMessage
):
    # Obter todas mensagens
    messages = redis.lrange(buffer_key, 0, -1)
    
    if not messages:
        return
    
    # Concatenar
    full_message = " ".join(messages)
    
    # Deletar buffer
    redis.delete(buffer_key)
    
    # Processar
    await process_message_use_case.execute(
        message_body=full_message,
        # ... outros params
    )
```

---

## 🚫 CONTENT FILTERING

### BR-CF001: Palavrões e Linguagem Inadequada

**Regra:** Sistema não deve usar linguagem inadequada

**Validação:**
```python
BLOCKED_WORDS = [
    "palavrão1", "palavrão2", ...
]

def contains_profanity(text: str) -> bool:
    text_lower = text.lower()
    return any(word in text_lower for word in BLOCKED_WORDS)

def filter_response(response: str) -> Result[str, Exception]:
    if contains_profanity(response):
        return Result.failure(
            ValueError("Resposta contém linguagem inadequada")
        )
    
    return Result.success(response)
```

**Ação:** Se IA gerar resposta inadequada, rejeitar e pedir nova geração

---

### BR-CF002: Menção a Concorrentes

**Regra:** Nunca mencionar ou sugerir concorrentes

**Validação:**
```python
COMPETITOR_KEYWORDS = [
    "ifood", "uber eats", "rappi", "pizzahut", ...
]

def mentions_competitor(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in COMPETITOR_KEYWORDS)
```

**Ação:** Rejeitar resposta e gerar novamente

---

### BR-CF003: Tom de Voz

**Regra:** Formal mas amigável, sem gírias

**Diretrizes:**
- ✅ Usar "você" (não "tu" ou "senhor(a)")
- ✅ Máximo 1-2 emojis por mensagem
- ✅ Pontuação correta
- ❌ Não usar "mano", "cara", "véi", etc.
- ❌ Não usar CAPS LOCK (parece gritar)
- ❌ Não usar múltiplos !!! ou ???

**Validação:**
```python
def validate_tone(text: str) -> Result[None, Exception]:
    # Verificar CAPS LOCK excessivo
    if sum(1 for c in text if c.isupper()) > len(text) * 0.5:
        return Result.failure(ValueError("Excesso de maiúsculas"))
    
    # Verificar emojis excessivos
    emoji_count = count_emojis(text)
    if emoji_count > 3:
        return Result.failure(ValueError("Excesso de emojis"))
    
    # Verificar gírias
    INFORMAL_SLANG = ["mano", "cara", "véi", "tipo assim"]
    if any(slang in text.lower() for slang in INFORMAL_SLANG):
        return Result.failure(ValueError("Gírias informais detectadas"))
    
    return Result.success(None)
```

---

## 🏘️ MULTI-TENANCY

### BR-MT001: Isolamento de Dados

**Regra:** TODO dado DEVE estar vinculado a `restaurant_id`

**Invariante Global:**
```python
# ❌ NUNCA fazer queries globais
conversations = db.query(Conversation).all()

# ✅ SEMPRE filtrar por tenant
conversations = db.query(Conversation).filter(
    Conversation.restaurant_id == restaurant_id
).all()
```

**Aplicar em:**
- Queries de banco
- Cache (incluir restaurant_id na key)
- Logs (sempre logar restaurant_id)
- Métricas
- Filas de processamento

---

### BR-MT002: Identificação do Tenant

**Regra:** Webhook identifica tenant via `canal_master_id`

**Fluxo:**
```
1. Webhook recebe mensagem da Join
2. Extrai canal_id da mensagem
3. Busca Restaurant por canal_master_id
4. Injeta restaurant_id no contexto
5. Processa mensagem no contexto do tenant
```

**Implementação:**
```python
@router.post("/webhooks/join")
async def join_webhook(
    payload: JoinWebhookPayload,
    restaurant_repo: RestaurantRepository
):
    # Identificar tenant
    restaurant = await restaurant_repo.find_by_canal_master_id(
        payload.canal_id
    )
    
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    
    # Processar no contexto do tenant
    await process_message(
        restaurant_id=restaurant.id,
        message=payload.message
    )
```

---

### BR-MT003: Cache Keys

**Regra:** Incluir `restaurant_id` em todas cache keys

**Pattern:**
```python
# ❌ ERRADO
cache_key = f"conversation:{customer_phone}"

# ✅ CORRETO
cache_key = f"{restaurant_id}:conversation:{customer_phone}"
```

**Evita:** Vazamento de dados entre tenants

---

## 🧠 MEMORY MANAGEMENT

### BR-MEM001: Níveis de Memória

**Regra:** Sistema usa 3 níveis de memória

**1. Curto Prazo (Redis)**
- **Duração:** 1 hora
- **Conteúdo:** Últimas 10 mensagens
- **Propósito:** Contexto imediato da conversa
- **Key:** `{restaurant_id}:memory:short:{conversation_id}`

**2. Médio Prazo (PostgreSQL)**
- **Duração:** 30 dias
- **Conteúdo:** Histórico completo de mensagens
- **Propósito:** Analytics, auditoria, ML
- **Tabela:** `messages`

**3. Longo Prazo (pgvector)**
- **Duração:** Permanente
- **Conteúdo:** Embeddings de mensagens importantes
- **Propósito:** RAG, busca semântica
- **Tabela:** `message_embeddings`

---

### BR-MEM002: Short-term Memory (Redis)

**Regra:** Cache de contexto em Redis

```python
async def store_short_term_memory(
    restaurant_id: str,
    conversation_id: str,
    messages: List[Message],
    redis: Redis
):
    key = f"{restaurant_id}:memory:short:{conversation_id}"
    
    # Serializar mensagens
    serialized = [msg.to_dict() for msg in messages[-10:]]
    
    # Armazenar com TTL de 1h
    await redis.setex(
        key,
        3600,  # 1 hora
        json.dumps(serialized)
    )
```

---

### BR-MEM003: Long-term Memory (pgvector)

**Regra:** Mensagens importantes viram embeddings

**Critérios de Importância:**
- Pedidos concluídos
- Reclamações
- Elogios
- Informações valiosas do cliente

```python
async def store_long_term_memory(
    message: Message,
    embedding_service: EmbeddingService
):
    # Gerar embedding
    embedding = await embedding_service.generate(message.body)
    
    # Armazenar em pgvector
    await db.execute(
        """
        INSERT INTO message_embeddings 
        (message_id, restaurant_id, embedding, metadata)
        VALUES ($1, $2, $3, $4)
        """,
        message.id,
        message.restaurant_id,
        embedding,
        json.dumps({"intent": message.intent, "timestamp": message.timestamp})
    )
```

---

## 🔗 EXTERNAL API INTEGRATION

### BR-EXT001: Tacto API OAuth2

**Regra:** Token deve ser cached e renovado automaticamente

**Fluxo:**
```
1. Verificar cache
   └→ Token válido? → Usar cached token
   └→ Expirado/inexistente? → Obter novo token

2. Obter novo token
   └→ POST https://accounts.tactonuvem.com.br/connect/token
   └→ Cache com TTL = expires_in - 5min (margem de segurança)

3. Usar token em requests
   └→ Header: Authorization: Bearer {token}
```

**Implementação:**
```python
class TactoOAuth2Handler:
    async def get_access_token(self) -> str:
        # Verificar cache
        cached = await self.redis.get("tacto:oauth:token")
        if cached:
            return cached
        
        # Obter novo token
        response = await self.http_client.post(
            "https://accounts.tactonuvem.com.br/connect/token",
            data={
                "client_id": "integracao-externa",
                "client_secret": settings.tacto_client_secret,
                "grant_type": "client_credentials"
            }
        )
        
        token = response.json()["access_token"]
        expires_in = response.json()["expires_in"]
        
        # Cache (com 5min de margem)
        await self.redis.setex(
            "tacto:oauth:token",
            expires_in - 300,
            token
        )
        
        return token
```

---

### BR-EXT002: Headers Obrigatórios Tacto API

**Regra:** Toda request à Tacto API deve incluir headers específicos

**Headers:**
```python
headers = {
    "Authorization": f"Bearer {access_token}",
    "chave-origem": "DA885FE3-44F8-46FE-BC8B-EF709F4EC2AA",  # FIXO
    "Tacto-Grupo-Empresarial": restaurant.chave_grupo_empresarial,
    "EmpresaId": restaurant.empresa_base_id,
    "GrupoEmpresaId": restaurant.empresa_base_id,
    "Tacto-Grupo-Empresa-Id": restaurant.chave_grupo_empresarial,
}
```

**Validação:**
```python
def validate_tacto_headers(headers: dict) -> Result[None, Exception]:
    required = [
        "Authorization",
        "chave-origem",
        "Tacto-Grupo-Empresarial",
        "EmpresaId"
    ]
    
    missing = [h for h in required if h not in headers]
    
    if missing:
        return Result.failure(
            ValueError(f"Missing headers: {missing}")
        )
    
    return Result.success(None)
```

---

### BR-EXT003: Retry Policy

**Regra:** Requests falhadas devem ter retry com backoff exponencial

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPError)
)
async def call_tacto_api(url: str, **kwargs):
    response = await http_client.get(url, **kwargs)
    response.raise_for_status()
    return response.json()
```

**Configuração:**
- Máximo 3 tentativas
- Backoff: 2s, 4s, 8s
- Retry em: 5xx, timeout, connection error
- **Não** retry em: 4xx (exceto 401)

---

### BR-EXT004: Join API Typing Simulation

**Regra:** Simular digitação antes de enviar resposta

**Comportamento:**
```
1. Enviar presence: "composing"
2. Aguardar 2-4 segundos (proporcional ao tamanho da resposta)
3. Enviar mensagem
4. Enviar presence: "paused"
```

**Implementação:**
```python
async def send_message_with_typing(
    phone: str,
    message: str,
    join_client: JoinClient
):
    # 1. Iniciar digitação
    await join_client.send_presence(phone, "composing")
    
    # 2. Calcular delay (0.05s por caractere, max 4s)
    delay = min(len(message) * 0.05, 4.0)
    await asyncio.sleep(delay)
    
    # 3. Enviar mensagem
    await join_client.send_message(phone, message)
    
    # 4. Parar digitação
    await join_client.send_presence(phone, "paused")
```

**Objetivo:** Humanizar interação, não parecer bot

---

## 📊 METRICS & OBSERVABILITY

### BR-OBS001: Logging Estruturado

**Regra:** Todos logs devem incluir contexto estruturado

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "message_processed",
    restaurant_id=restaurant.id,
    conversation_id=conversation.id,
    message_id=message.id,
    processing_time_ms=elapsed,
    automation_level=restaurant.automation_type.name
)
```

**Campos Obrigatórios:**
- `restaurant_id`: Sempre
- `conversation_id`: Quando aplicável
- `user_id`: Quando aplicável
- `duration_ms`: Para operações longas

---

### BR-OBS002: Error Tracking

**Regra:** Erros devem ser categorizados e rastreados

**Categorias:**
- `EXTERNAL_API_ERROR`: Erro em API externa (Tacto, Join, Gemini)
- `VALIDATION_ERROR`: Violação de regra de negócio
- `DATA_ERROR`: Problema com dados (duplicação, inconsistência)
- `INFRASTRUCTURE_ERROR`: DB, Redis, etc.
- `UNEXPECTED_ERROR`: Não categorizado

```python
try:
    result = await process_message(...)
except TactoAPIException as e:
    logger.error(
        "external_api_error",
        category="EXTERNAL_API_ERROR",
        provider="tacto",
        error_code=e.status_code,
        error_message=str(e)
    )
except Exception as e:
    logger.exception(
        "unexpected_error",
        category="UNEXPECTED_ERROR"
    )
```

---

## 📝 CHANGELOG

### [0.0.1] - 2026-03-27

#### Added
- Todas regras de negócio documentadas
- Validações definidas
- Fluxos de processamento especificados
- Invariantes globais estabelecidos

---

**Mantido por:** Engineering Team  
**Próxima Revisão:** Após implementação inicial  
**Última Atualização:** 2026-03-27
