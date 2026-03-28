# ADR-002: Message Buffer Strategy with Redis

**Status:** Accepted  
**Date:** 2026-03-27  
**Deciders:** Engineering Team, Tech Lead  
**Context:** Agrupamento inteligente de mensagens do usuário

---

## Context

Quando um cliente envia mensagens via WhatsApp, é comum enviar múltiplas mensagens rápidas em sequência:

```
[10:00:00] Cliente: "Oi"
[10:00:02] Cliente: "Tudo bem?"
[10:00:04] Cliente: "Quero fazer um pedido"
```

**Problema:** Se o sistema responder imediatamente a cada mensagem, teremos:
- 3 respostas fragmentadas e repetitivas
- Alto custo de chamadas à IA
- Experiência ruim para o cliente
- Contexto perdido entre mensagens

**Objetivo:** Agrupar mensagens do mesmo usuário em uma janela de tempo e processar todas de uma vez, gerando uma única resposta contextualizada.

---

## Decision

Implementar **Message Buffer com Redis** utilizando padrão de timer com reset.

### Arquitetura

```
Mensagem Recebida
    ↓
Adicionar ao Buffer (Redis)
    ↓
Resetar Timer (5 segundos)
    ↓
Nova mensagem? → Reset timer
    ↓
Timer expira → Flush buffer
    ↓
Concatenar mensagens
    ↓
Processar com IA
    ↓
Enviar UMA resposta
```

### Implementação Técnica

**Domain Service:**
```python
# domain/messaging/services/message_buffer_service.py

class MessageBufferService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.buffer_timeout = 5  # segundos
    
    async def add_to_buffer(
        self, 
        restaurant_id: str,
        customer_phone: str,
        message: str
    ):
        buffer_key = f"{restaurant_id}:buffer:{customer_phone}"
        
        # Adicionar mensagem
        await self.redis.lpush(buffer_key, message)
        
        # Resetar TTL
        await self.redis.expire(buffer_key, self.buffer_timeout)
        
        # Agendar flush (background task)
        await self.schedule_flush(buffer_key)
    
    async def flush_buffer(self, buffer_key: str):
        messages = await self.redis.lrange(buffer_key, 0, -1)
        
        if not messages:
            return
        
        # Concatenar
        full_message = " ".join(messages)
        
        # Deletar buffer
        await self.redis.delete(buffer_key)
        
        # Processar
        await self.process_message(full_message)
```

### Configuração

- **Timeout padrão:** 5 segundos
- **Key pattern:** `{restaurant_id}:buffer:{customer_phone}`
- **TTL:** Expira após 5s de inatividade
- **Flush:** Background task verifica expiração

---

## Consequences

### Positive

✅ **Melhor UX:** Cliente recebe 1 resposta contextualizada ao invés de 3 fragmentadas  
✅ **Economia de Custo:** Menos chamadas à IA  
✅ **Melhor Contexto:** IA vê mensagem completa  
✅ **Performance:** Redis é extremamente rápido  
✅ **Escalabilidade:** Redis suporta milhões de buffers simultâneos  
✅ **Isolamento:** Multi-tenancy garantido por key pattern  

### Negative

❌ **Latência Adicional:** Resposta demora até 5s (aceitável)  
❌ **Dependência Redis:** Sistema crítico depende de Redis  
❌ **Complexidade:** Gerenciar timers em background  
❌ **Edge Cases:** Mensagens muito longas ou timeout inadequado  

### Mitigations

- **Timeout Adaptativo:** Ajustar timeout baseado em tamanho da mensagem
- **Redis HA:** Usar Redis Sentinel ou Cluster em produção
- **Fallback:** Se Redis falhar, processar mensagem diretamente (sem buffer)
- **Monitoring:** Alertas se buffer não processar em X tempo

---

## Alternatives Considered

### 1. Buffer em PostgreSQL

**Pros:** Já temos PostgreSQL, persistência garantida  
**Cons:** Muito lento para operações temporárias, polling ineficiente  
**Rejected:** Performance inadequada

### 2. Buffer em Memória (Python dict)

**Pros:** Zero dependências, extremamente rápido  
**Cons:** Não funciona com múltiplas instâncias (horizontally scaled), perda de dados em restart  
**Rejected:** Não escala horizontalmente

### 3. RabbitMQ/Kafka com delay

**Pros:** Messaging robusto, escalável  
**Cons:** Over-engineering, complexidade operacional muito alta  
**Rejected:** Complexidade desnecessária para este caso

### 4. Sem Buffer (processar imediatamente)

**Pros:** Simples, zero latência  
**Cons:** Experiência ruim, alto custo de IA  
**Rejected:** Não resolve o problema principal

---

## Implementation Details

### Casos de Borda

**1. Mensagem muito longa:**
```python
if len(concatenated) > 1000:
    # Truncar ou dividir em chunks
    pass
```

**2. Flood de mensagens:**
```python
MAX_BUFFER_SIZE = 50  # Máximo 50 mensagens no buffer

if buffer_size > MAX_BUFFER_SIZE:
    # Flush imediatamente
    await flush_buffer(buffer_key)
```

**3. Redis indisponível:**
```python
try:
    await buffer_service.add_to_buffer(...)
except RedisError:
    # Fallback: processar diretamente
    await process_message_directly(message)
```

### Timeout Adaptativo (Futuro)

```python
def calculate_timeout(message: str) -> int:
    if message.endswith("?"):
        return 3  # Pergunta = resposta rápida
    elif len(message) > 100:
        return 7  # Mensagem longa = esperar mais
    else:
        return 5  # Padrão
```

### Monitoring

```python
# Métricas importantes
buffer_size = redis.llen(buffer_key)
buffer_age = redis.ttl(buffer_key)

# Alertas
if buffer_age > 10:
    alert("Buffer não processado em 10s")
```

---

## Testing Strategy

### Unit Tests

```python
async def test_add_to_buffer():
    service = MessageBufferService(redis_mock)
    
    await service.add_to_buffer("rest_1", "5511999999999", "Oi")
    
    buffer = await redis_mock.lrange("rest_1:buffer:5511999999999", 0, -1)
    assert buffer == ["Oi"]
```

### Integration Tests

```python
async def test_buffer_flush_after_timeout():
    # Adicionar mensagem
    await service.add_to_buffer("rest_1", "5511999999999", "Oi")
    
    # Esperar timeout
    await asyncio.sleep(6)
    
    # Verificar que buffer foi processado
    buffer = await redis.lrange("rest_1:buffer:5511999999999", 0, -1)
    assert buffer == []
```

### E2E Tests

```python
async def test_multiple_messages_buffered():
    # Simular cliente enviando 3 mensagens rápidas
    await webhook_handler({"body": "Oi", ...})
    await asyncio.sleep(0.5)
    
    await webhook_handler({"body": "Tudo bem?", ...})
    await asyncio.sleep(0.5)
    
    await webhook_handler({"body": "Quero pedir", ...})
    
    # Esperar flush
    await asyncio.sleep(6)
    
    # Verificar que apenas 1 resposta foi enviada
    assert join_client.send_message.call_count == 1
    
    # Verificar que resposta contém contexto completo
    call_args = join_client.send_message.call_args
    assert "Oi" in call_args.kwargs["text"]
```

---

## Performance Considerations

### Redis Configuration

```ini
# Otimizações para buffer
maxmemory-policy volatile-lru
maxmemory 2gb
timeout 300
tcp-keepalive 60
```

### Expected Load

- **1000 restaurantes**
- **100 conversas simultâneas por restaurante**
- **= 100,000 buffers ativos no pico**
- **Redis memory:** ~50MB (500 bytes por buffer × 100k)

### Scalability

Redis suporta **milhões de keys** facilmente. Com sharding, podemos escalar infinitamente:

```python
# Sharding por restaurant_id
shard = hash(restaurant_id) % NUM_REDIS_SHARDS
redis_client = redis_pool[shard]
```

---

## Migration Path

### Fase 1 (MVP): Buffer Simples
- Timeout fixo de 5s
- Sem adaptação
- Sem fallback

### Fase 2 (Produção): Buffer Robusto
- Timeout adaptativo
- Fallback se Redis falhar
- Monitoring e alertas

### Fase 3 (Escala): Buffer Distribuído
- Redis Cluster
- Sharding por tenant
- Backpressure handling

---

## Related Decisions

- ADR-001: DDD Architecture (MessageBufferService é Domain Service)
- ADR-003: Multi-level Memory (Buffer é short-term memory)

---

## References

- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [Debouncing vs Throttling](https://css-tricks.com/debouncing-throttling-explained-examples/)
- Join Developer API Documentation

---

**Last Updated:** 2026-03-27  
**Review Date:** 2026-09-27 (após produção)
