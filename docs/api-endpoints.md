# 🌐 TactoFlow - API Endpoints Specification

**Versão:** 0.0.1  
**Última Atualização:** 2026-03-27  
**Base URL:** `http://localhost:8000/api/v1`  
**Framework:** FastAPI  
**Autenticação:** JWT Bearer Token (futuro), API Key para webhooks

---

## 📋 ÍNDICE

1. [Convenções Gerais](#convenções-gerais)
2. [Autenticação](#autenticação)
3. [Webhooks](#webhooks)
4. [Restaurant Management](#restaurant-management)
5. [Conversation & Messages](#conversation--messages)
6. [Admin & Control](#admin--control)
7. [Health & Monitoring](#health--monitoring)
8. [Error Responses](#error-responses)

---

## 🎯 CONVENÇÕES GERAIS

### HTTP Status Codes

| Código | Uso |
|--------|-----|
| `200 OK` | Sucesso em GET, PUT, PATCH |
| `201 Created` | Recurso criado com sucesso (POST) |
| `204 No Content` | Sucesso sem corpo de resposta (DELETE) |
| `400 Bad Request` | Dados inválidos |
| `401 Unauthorized` | Não autenticado |
| `403 Forbidden` | Sem permissão |
| `404 Not Found` | Recurso não encontrado |
| `409 Conflict` | Conflito (ex: duplicação) |
| `422 Unprocessable Entity` | Validação de negócio falhou |
| `500 Internal Server Error` | Erro do servidor |
| `503 Service Unavailable` | Serviço temporariamente indisponível |

### Response Format

**Sucesso:**
```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2026-03-27T10:15:30Z",
    "request_id": "uuid-here"
  }
}
```

**Erro:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Nome do restaurante é obrigatório",
    "details": {
      "field": "name",
      "constraint": "min_length"
    }
  },
  "metadata": {
    "timestamp": "2026-03-27T10:15:30Z",
    "request_id": "uuid-here"
  }
}
```

### Paginação

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

**Query Parameters:**
- `page`: Número da página (default: 1)
- `per_page`: Itens por página (default: 20, max: 100)
- `sort_by`: Campo para ordenação
- `order`: `asc` ou `desc` (default: desc)

---

## 🔐 AUTENTICAÇÃO

### POST /auth/token

**Descrição:** Obter JWT token (futuro - não implementar agora)

**Request:**
```json
{
  "username": "admin@tacto.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

---

## 📨 WEBHOOKS

### POST /webhooks/join

**Descrição:** Webhook para receber mensagens da Join Developer API

**Autenticação:** Verificação de assinatura (HMAC) ou IP whitelist

**Headers:**
```
Content-Type: application/json
X-Join-Signature: sha256=<signature>
```

**Request Body:**
```json
{
  "from": "5511999999999@c.us",
  "to": "5511888888888@c.us",
  "body": "Olá, quero fazer um pedido",
  "fromMe": false,
  "source": "app",
  "type": "text",
  "timestamp": 1711537230,
  "id": "msg_external_id_123",
  "canal_id": "canal-master-123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message_id": "uuid-interno",
    "status": "queued"
  }
}
```

**Status Codes:**
- `200`: Mensagem aceita e processada
- `202`: Mensagem aceita e enfileirada
- `400`: Payload inválido
- `401`: Assinatura inválida
- `404`: Restaurante não encontrado (canal_id inválido)

**Comportamento:**
1. Validar assinatura
2. Identificar restaurante pelo `canal_id`
3. Validar se deve processar (fromMe, source, etc.)
4. Adicionar ao buffer Redis
5. Retornar 202 imediatamente
6. Processar assincronamente

---

## 🏪 RESTAURANT MANAGEMENT

### POST /restaurants

**Descrição:** Criar novo restaurante

**Autenticação:** Requerida (Admin)

**Request:**
```json
{
  "name": "Pizzaria do João",
  "prompt_default": "Você é um assistente cordial da Pizzaria do João...",
  "menu_url": "https://cardapio.pizzariadojoao.com.br",
  "opening_hours": {
    "monday": {"opens_at": "18:00", "closes_at": "23:00"},
    "tuesday": {"opens_at": "18:00", "closes_at": "23:00"},
    "wednesday": {"is_closed": true},
    "thursday": {"opens_at": "18:00", "closes_at": "23:00"},
    "friday": {"opens_at": "18:00", "closes_at": "00:00"},
    "saturday": {"opens_at": "18:00", "closes_at": "00:00"},
    "sunday": {"opens_at": "18:00", "closes_at": "23:00"}
  },
  "integration_type": 2,
  "automation_type": 1,
  "chave_grupo_empresarial": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "canal_master_id": "canal-123",
  "empresa_base_id": "1"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": "rest_uuid_123",
    "name": "Pizzaria do João",
    "prompt_default": "Você é um assistente cordial...",
    "menu_url": "https://cardapio.pizzariadojoao.com.br",
    "opening_hours": {...},
    "integration_type": 2,
    "automation_type": 1,
    "chave_grupo_empresarial": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "canal_master_id": "canal-123",
    "empresa_base_id": "1",
    "is_active": true,
    "created_at": "2026-03-27T10:15:30Z",
    "updated_at": "2026-03-27T10:15:30Z"
  }
}
```

**Validações:**
- Nome único (409 se duplicado)
- `canal_master_id` único
- `chave_grupo_empresarial` válido UUID
- Horários válidos
- `menu_url` válida

---

### GET /restaurants

**Descrição:** Listar restaurantes

**Autenticação:** Requerida (Admin)

**Query Parameters:**
- `page`: Número da página
- `per_page`: Itens por página
- `is_active`: Filtrar por status (true/false)
- `search`: Buscar por nome

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": "rest_uuid_123",
      "name": "Pizzaria do João",
      "is_active": true,
      "automation_type": 1,
      "created_at": "2026-03-27T10:15:30Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### GET /restaurants/{restaurant_id}

**Descrição:** Obter detalhes de um restaurante

**Autenticação:** Requerida

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "rest_uuid_123",
    "name": "Pizzaria do João",
    "prompt_default": "...",
    "menu_url": "...",
    "opening_hours": {...},
    "integration_type": 2,
    "automation_type": 1,
    "chave_grupo_empresarial": "...",
    "canal_master_id": "canal-123",
    "empresa_base_id": "1",
    "is_active": true,
    "created_at": "2026-03-27T10:15:30Z",
    "updated_at": "2026-03-27T10:15:30Z",
    "stats": {
      "total_conversations": 150,
      "total_messages": 3200,
      "ai_active_conversations": 145
    }
  }
}
```

---

### PUT /restaurants/{restaurant_id}

**Descrição:** Atualizar restaurante

**Autenticação:** Requerida (Admin)

**Request:** (todos campos opcionais)
```json
{
  "name": "Pizzaria do João - Novo Nome",
  "prompt_default": "Prompt atualizado...",
  "automation_type": 2
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "rest_uuid_123",
    "name": "Pizzaria do João - Novo Nome",
    ...
  }
}
```

**Validações:**
- Se mudar `automation_type` para nível inferior, verificar pedidos em aberto
- Nome único (se alterado)

---

### PATCH /restaurants/{restaurant_id}/activate

**Descrição:** Ativar restaurante

**Response:** `200 OK`

---

### PATCH /restaurants/{restaurant_id}/deactivate

**Descrição:** Desativar restaurante

**Response:** `200 OK`

---

### DELETE /restaurants/{restaurant_id}

**Descrição:** Deletar restaurante (soft delete)

**Autenticação:** Requerida (Admin)

**Response:** `204 No Content`

**Comportamento:**
- Soft delete (marca `deleted_at`)
- Preserva dados para auditoria
- Desativa processamento imediato

---

## 💬 CONVERSATION & MESSAGES

### GET /conversations

**Descrição:** Listar conversas de um restaurante

**Autenticação:** Requerida

**Query Parameters:**
- `restaurant_id`: **OBRIGATÓRIO** (multi-tenancy)
- `customer_phone`: Filtrar por telefone
- `is_ai_active`: Filtrar conversas com IA ativa
- `from_date`: Conversas a partir de
- `to_date`: Conversas até

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": "conv_uuid_123",
      "restaurant_id": "rest_uuid_123",
      "customer_phone": "5511999999999",
      "is_ai_active": true,
      "ai_disabled_until": null,
      "last_message_at": "2026-03-27T10:15:30Z",
      "message_count": 15,
      "created_at": "2026-03-27T09:00:00Z"
    }
  ],
  "pagination": {...}
}
```

---

### GET /conversations/{conversation_id}

**Descrição:** Obter detalhes de uma conversa

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "conv_uuid_123",
    "restaurant_id": "rest_uuid_123",
    "customer_phone": "5511999999999",
    "is_ai_active": true,
    "ai_disabled_until": null,
    "created_at": "2026-03-27T09:00:00Z",
    "updated_at": "2026-03-27T10:15:30Z"
  }
}
```

---

### GET /conversations/{conversation_id}/messages

**Descrição:** Obter mensagens de uma conversa

**Query Parameters:**
- `limit`: Número de mensagens (default: 50, max: 200)
- `before`: Mensagens antes deste timestamp
- `after`: Mensagens depois deste timestamp

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": "msg_uuid_123",
      "conversation_id": "conv_uuid_123",
      "body": "Olá, quero fazer um pedido",
      "direction": "incoming",
      "source": "app",
      "from_me": false,
      "timestamp": "2026-03-27T10:15:30Z",
      "created_at": "2026-03-27T10:15:31Z"
    },
    {
      "id": "msg_uuid_124",
      "conversation_id": "conv_uuid_123",
      "body": "Olá! Bem-vindo à Pizzaria do João! Como posso ajudar? 😊",
      "direction": "outgoing",
      "source": "ai",
      "from_me": true,
      "timestamp": "2026-03-27T10:15:35Z",
      "created_at": "2026-03-27T10:15:36Z"
    }
  ],
  "pagination": {
    "has_next": true,
    "has_prev": false,
    "next_cursor": "timestamp_cursor_here"
  }
}
```

---

### POST /conversations/{conversation_id}/messages

**Descrição:** Enviar mensagem manualmente (para testes ou intervenção humana)

**Request:**
```json
{
  "body": "Mensagem do operador humano",
  "source": "phone"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": "msg_uuid_125",
    "conversation_id": "conv_uuid_123",
    "body": "Mensagem do operador humano",
    "direction": "outgoing",
    "source": "phone",
    "from_me": true,
    "timestamp": "2026-03-27T10:16:00Z"
  }
}
```

**Comportamento:**
- Se `source=phone`, desativa IA por 12h
- Envia mensagem via Join API
- Salva no histórico

---

## � INSTANCE MANAGEMENT (Join WhatsApp)

### POST /instances

**Descrição:** Criar nova instância WhatsApp

**Request:**
```json
{
  "instance_name": "pizzaria-joao-whatsapp"
}
```

**Response:** `201 Created`
```json
{
  "instance_key": "abc123xyz",
  "instance_name": "pizzaria-joao-whatsapp",
  "status": "created",
  "phone_number": null,
  "webhook_url": null,
  "is_connected": false
}
```

---

### GET /instances

**Descrição:** Listar todas as instâncias WhatsApp

**Response:** `200 OK`
```json
{
  "instances": [
    {
      "instance_key": "abc123xyz",
      "instance_name": "pizzaria-joao-whatsapp",
      "status": "connected",
      "phone_number": "5511999999999",
      "webhook_url": "https://api.tactoflow.com/api/v1/webhook/join",
      "is_connected": true
    }
  ],
  "total": 1
}
```

---

### GET /instances/{instance_key}/status

**Descrição:** Obter status de uma instância

**Response:** `200 OK`
```json
{
  "instance_key": "abc123xyz",
  "instance_name": "pizzaria-joao-whatsapp",
  "status": "connected",
  "phone_number": "5511999999999",
  "webhook_url": "https://api.tactoflow.com/api/v1/webhook/join",
  "is_connected": true
}
```

---

### GET /instances/{instance_key}/qrcode

**Descrição:** Obter QR Code para conectar WhatsApp

**Response:** `200 OK`
```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "instance_key": "abc123xyz",
  "expires_in": 60
}
```

**Uso:** Exibir QR Code para usuário escanear com WhatsApp

---

### POST /instances/webhook

**Descrição:** Configurar URL do webhook para receber mensagens

**Request:**
```json
{
  "instance_key": "abc123xyz",
  "webhook_url": "https://api.tactoflow.com/api/v1/webhook/join",
  "events": ["messages.upsert", "connection.update"]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Webhook configured successfully",
  "instance_key": "abc123xyz",
  "webhook_url": "https://api.tactoflow.com/api/v1/webhook/join"
}
```

---

### POST /instances/connect

**Descrição:** Conectar instância WhatsApp a um restaurante (multi-tenant)

**Request:**
```json
{
  "restaurant_id": "uuid-do-restaurante",
  "instancia": "abc123xyz"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Instance connected to restaurant",
  "restaurant_id": "uuid-do-restaurante",
  "restaurant_name": "Pizzaria do João",
  "instance_key": "abc123xyz"
}
```

**Comportamento:**
- Associa a instância WhatsApp ao restaurante
- Mensagens recebidas nesta instância serão processadas pelo AI Agent do restaurante
- Multi-tenant: cada restaurante pode ter sua própria instância

---

### DELETE /instances/{instance_key}

**Descrição:** Deletar uma instância WhatsApp

**Response:** `204 No Content`

---

### POST /instances/{instance_key}/logout

**Descrição:** Desconectar/logout de uma instância WhatsApp

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Instance logged out successfully",
  "instance_key": "abc123xyz"
}
```

---

## �🛠️ ADMIN & CONTROL

### PATCH /admin/conversations/{conversation_id}/enable-ai

**Descrição:** Reativar IA manualmente em uma conversa

**Autenticação:** Requerida (Admin)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "conversation_id": "conv_uuid_123",
    "is_ai_active": true,
    "ai_disabled_until": null
  }
}
```

---

### PATCH /admin/conversations/{conversation_id}/disable-ai

**Descrição:** Desativar IA manualmente

**Request:**
```json
{
  "hours": 24
}
```

**Response:** `200 OK`

---

### POST /admin/messages/reprocess

**Descrição:** Reprocessar mensagem (para debug/testes)

**Request:**
```json
{
  "message_id": "msg_uuid_123",
  "force": true
}
```

**Response:** `202 Accepted`

---

### GET /admin/buffer/status

**Descrição:** Verificar status do buffer Redis

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "active_buffers": 15,
    "buffers": [
      {
        "key": "rest_123:buffer:5511999999999",
        "message_count": 3,
        "ttl_seconds": 2
      }
    ]
  }
}
```

---

### DELETE /admin/cache/clear

**Descrição:** Limpar cache (Redis)

**Query Parameters:**
- `pattern`: Padrão de chave (ex: `rest_123:*`)
- `type`: `all`, `buffer`, `memory`, `tokens`

**Response:** `200 OK`

---

## 🏥 HEALTH & MONITORING

### GET /health

**Descrição:** Health check básico

**Autenticação:** Não requerida

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "0.0.1",
    "timestamp": "2026-03-27T10:15:30Z",
    "uptime_seconds": 86400
  }
}
```

---

### GET /health/detailed

**Descrição:** Health check detalhado com status de dependências

**Autenticação:** Requerida (Admin)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "0.0.1",
    "timestamp": "2026-03-27T10:15:30Z",
    "dependencies": {
      "postgres": {
        "status": "healthy",
        "latency_ms": 5
      },
      "redis": {
        "status": "healthy",
        "latency_ms": 2
      },
      "tacto_api": {
        "status": "healthy",
        "latency_ms": 150,
        "token_cached": true
      },
      "join_api": {
        "status": "healthy",
        "latency_ms": 100
      },
      "gemini_api": {
        "status": "healthy",
        "latency_ms": 300
      }
    }
  }
}
```

**Status Codes:**
- `200`: Tudo saudável
- `503`: Alguma dependência crítica falhou

---

### GET /metrics

**Descrição:** Métricas Prometheus (futuro)

**Response:** Formato Prometheus
```
# HELP tacto_messages_processed_total Total de mensagens processadas
# TYPE tacto_messages_processed_total counter
tacto_messages_processed_total{restaurant_id="rest_123",status="success"} 1523

# HELP tacto_ai_response_time_seconds Tempo de resposta da IA
# TYPE tacto_ai_response_time_seconds histogram
tacto_ai_response_time_seconds_bucket{le="0.5"} 100
tacto_ai_response_time_seconds_bucket{le="1.0"} 250
...
```

---

### GET /stats/restaurants/{restaurant_id}

**Descrição:** Estatísticas de um restaurante

**Query Parameters:**
- `from_date`: Data inicial
- `to_date`: Data final

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "restaurant_id": "rest_uuid_123",
    "period": {
      "from": "2026-03-01T00:00:00Z",
      "to": "2026-03-27T23:59:59Z"
    },
    "metrics": {
      "total_conversations": 150,
      "total_messages": 3200,
      "incoming_messages": 1600,
      "outgoing_messages": 1600,
      "ai_responses": 1500,
      "human_interventions": 10,
      "average_response_time_seconds": 3.5,
      "messages_per_conversation": 21.3,
      "most_active_hour": "20:00-21:00",
      "busiest_day": "friday"
    },
    "automation_stats": {
      "ai_handled_percentage": 93.75,
      "human_takeover_percentage": 6.25
    }
  }
}
```

---

## ❌ ERROR RESPONSES

### Error Codes

| Código | Descrição |
|--------|-----------|
| `VALIDATION_ERROR` | Dados inválidos |
| `RESTAURANT_NOT_FOUND` | Restaurante não encontrado |
| `CONVERSATION_NOT_FOUND` | Conversa não encontrada |
| `MESSAGE_NOT_FOUND` | Mensagem não encontrada |
| `DUPLICATE_RESOURCE` | Recurso duplicado |
| `INVALID_AUTOMATION_LEVEL` | Nível de automação inválido |
| `AI_DISABLED` | IA desativada para esta conversa |
| `EXTERNAL_API_ERROR` | Erro em API externa |
| `RATE_LIMIT_EXCEEDED` | Rate limit excedido |
| `UNAUTHORIZED` | Não autenticado |
| `FORBIDDEN` | Sem permissão |
| `INTERNAL_ERROR` | Erro interno do servidor |

### Exemplo de Erro Completo

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Falha na validação dos dados",
    "details": {
      "fields": [
        {
          "field": "name",
          "message": "Nome deve ter pelo menos 3 caracteres",
          "value": "AB"
        },
        {
          "field": "opening_hours.monday.opens_at",
          "message": "Formato de horário inválido",
          "value": "25:00"
        }
      ]
    }
  },
  "metadata": {
    "timestamp": "2026-03-27T10:15:30Z",
    "request_id": "req_uuid_789",
    "path": "/api/v1/restaurants",
    "method": "POST"
  }
}
```

---

## 🔒 RATE LIMITING

### Limites Globais

| Endpoint | Limite |
|----------|--------|
| Webhooks | 1000 req/min por restaurante |
| Admin API | 100 req/min por usuário |
| Public API | 60 req/min por IP |

### Headers de Rate Limit

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1711537890
```

### Response quando excedido: `429 Too Many Requests`

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Limite de requisições excedido",
    "details": {
      "limit": 100,
      "window_seconds": 60,
      "retry_after_seconds": 15
    }
  }
}
```

---

## 🚀 WEBHOOKS OUTGOING (Futuro)

### POST {configurado_pelo_cliente}

**Descrição:** Notificar eventos para sistemas externos

**Eventos:**
- `conversation.created`
- `conversation.ai_disabled`
- `message.received`
- `message.sent`
- `human_intervention.detected`
- `order.created` (futuro)

**Payload Exemplo:**
```json
{
  "event": "human_intervention.detected",
  "timestamp": "2026-03-27T10:15:30Z",
  "data": {
    "restaurant_id": "rest_uuid_123",
    "conversation_id": "conv_uuid_123",
    "customer_phone": "5511999999999",
    "ai_disabled_until": "2026-03-27T22:15:30Z"
  }
}
```

---

## 📝 CHANGELOG

### [0.0.1] - 2026-03-27

#### Definido
- Todos endpoints principais
- Webhooks Join
- CRUD de restaurantes
- Consulta de conversas e mensagens
- Endpoints administrativos
- Health checks

#### Planejado (Futuro)
- Autenticação JWT
- Endpoints de pedidos
- Webhooks outgoing
- Métricas Prometheus
- GraphQL API (considerar)

---

**Mantido por:** Engineering Team  
**Última Revisão:** 2026-03-27  
**Próxima Revisão:** Após primeira implementação
