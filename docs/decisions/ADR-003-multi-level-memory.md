# ADR-003: Multi-level Memory Architecture

**Status:** Accepted  
**Date:** 2026-03-27  
**Deciders:** Engineering Team, AI/ML Team  
**Context:** Sistema de memória para contexto de conversas

---

## Context

Para a IA gerar respostas contextualizadas, precisa ter acesso ao histórico da conversa. Porém:

**Desafios:**
1. **Volume:** Milhares de conversas simultâneas gerando milhões de mensagens
2. **Latência:** IA precisa de contexto rápido (< 100ms)
3. **Custo:** Não podemos enviar todo histórico para IA (custo de tokens)
4. **Relevância:** Mensagens antigas podem não ser relevantes
5. **Busca Semântica:** Precisa encontrar informações relevantes mesmo sem match exato

**Requisitos:**
- Contexto imediato (últimas N mensagens) em < 50ms
- Busca semântica em histórico completo
- Persistência de longo prazo para analytics
- Isolamento por tenant (multi-tenancy)

---

## Decision

Implementar **arquitetura de memória em 3 níveis** (três camadas de cache):

```
┌─────────────────────────────────────┐
│  Short-term Memory (Redis)          │  ← Últimas 10 msgs, TTL 1h
│  - Acesso: < 5ms                    │
│  - Tamanho: ~50 KB por conversa     │
└─────────────────────────────────────┘
           ↓ (fallback)
┌─────────────────────────────────────┐
│  Mid-term Memory (PostgreSQL)       │  ← Histórico 30 dias
│  - Acesso: < 50ms                   │
│  - Tamanho: Ilimitado               │
└─────────────────────────────────────┘
           ↓ (analytics & RAG)
┌─────────────────────────────────────┐
│  Long-term Memory (pgvector)        │  ← Busca semântica
│  - Acesso: < 200ms                  │
│  - Embeddings: 768 dimensões        │
└─────────────────────────────────────┘
```

### Níveis Detalhados

#### 1️⃣ Short-term Memory (Redis)

**Propósito:** Contexto imediato da conversa  
**Armazenamento:** Últimas 10 mensagens  
**TTL:** 1 hora de inatividade  
**Key Pattern:** `{restaurant_id}:memory:short:{conversation_id}`

**Estrutura:**
```json
{
  "messages": [
    {
      "id": "msg_uuid_1",
      "body": "Olá",
      "direction": "incoming",
      "timestamp": "2026-03-27T10:00:00Z"
    },
    {
      "id": "msg_uuid_2", 
      "body": "Olá! Como posso ajudar?",
      "direction": "outgoing",
      "timestamp": "2026-03-27T10:00:05Z"
    }
  ],
  "metadata": {
    "customer_phone": "5511999999999",
    "last_intent": "greeting"
  }
}
```

**Uso:**
```python
async def get_conversation_context(conversation_id: str) -> List[Message]:
    # Tentar Redis primeiro
    cached = await redis.get(f"{restaurant_id}:memory:short:{conversation_id}")
    
    if cached:
        return parse_messages(cached)
    
    # Fallback: PostgreSQL
    messages = await db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.timestamp.desc()).limit(10).all()
    
    # Cachear para próxima vez
    await redis.setex(
        f"{restaurant_id}:memory:short:{conversation_id}",
        3600,
        serialize_messages(messages)
    )
    
    return messages
```

---

#### 2️⃣ Mid-term Memory (PostgreSQL)

**Propósito:** Histórico completo para analytics e auditoria  
**Armazenamento:** Todas mensagens  
**Retenção:** 30 dias (configurável por restaurante)  
**Tabela:** `messages`

**Uso:**
```python
async def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    before: Optional[datetime] = None
) -> List[Message]:
    query = db.query(Message).filter(
        Message.conversation_id == conversation_id
    )
    
    if before:
        query = query.filter(Message.timestamp < before)
    
    return await query.order_by(
        Message.timestamp.desc()
    ).limit(limit).all()
```

**Archive Strategy (Futuro):**
```python
# Mover mensagens > 30 dias para cold storage (S3)
async def archive_old_messages():
    cutoff = datetime.now() - timedelta(days=30)
    
    old_messages = db.query(Message).filter(
        Message.created_at < cutoff
    ).all()
    
    # Exportar para S3
    await s3.put_object(
        Bucket="tacto-archives",
        Key=f"messages/{date}/batch.parquet",
        Body=serialize_to_parquet(old_messages)
    )
    
    # Deletar do PostgreSQL
    await db.delete(old_messages)
```

---

#### 3️⃣ Long-term Memory (pgvector)

**Propósito:** Busca semântica em histórico completo  
**Armazenamento:** Embeddings de mensagens importantes  
**Dimensões:** 768 (Gemini embedding-001)  
**Tabela:** `message_embeddings`

**Quando Gerar Embedding:**
- Mensagens do cliente (não respostas da IA)
- Mensagens importantes (pedidos, reclamações, elogios)
- Informações valiosas do cliente

**Implementação:**
```python
async def store_message_embedding(message: Message):
    # Gerar embedding
    embedding = await gemini_client.generate_embedding(message.body)
    
    # Armazenar em pgvector
    await db.execute(
        """
        INSERT INTO message_embeddings 
        (message_id, restaurant_id, embedding, content, metadata)
        VALUES ($1, $2, $3, $4, $5)
        """,
        message.id,
        message.restaurant_id,
        embedding,
        message.body,
        json.dumps({
            "timestamp": message.timestamp.isoformat(),
            "customer_phone": message.customer_phone
        })
    )
```

**Busca Semântica:**
```python
async def semantic_search(
    restaurant_id: str,
    query: str,
    limit: int = 5
) -> List[Message]:
    # Gerar embedding da query
    query_embedding = await gemini_client.generate_embedding(query)
    
    # Buscar similares usando pgvector
    results = await db.execute(
        """
        SELECT 
            me.content,
            me.metadata,
            me.embedding <=> $1::vector AS distance
        FROM message_embeddings me
        WHERE me.restaurant_id = $2
        ORDER BY me.embedding <=> $1::vector
        LIMIT $3
        """,
        query_embedding,
        restaurant_id,
        limit
    )
    
    return results.fetchall()
```

**Uso para RAG (Futuro - INTERMEDIATE):**
```python
async def generate_response_with_rag(user_message: str):
    # Buscar contexto relevante
    relevant_context = await semantic_search(
        restaurant_id,
        user_message,
        limit=3
    )
    
    # Montar prompt com contexto
    prompt = f"""
    Contexto relevante de conversas anteriores:
    {format_context(relevant_context)}
    
    Mensagem do usuário:
    {user_message}
    
    Responda considerando o contexto acima.
    """
    
    return await gemini_client.generate(prompt)
```

---

## Consequences

### Positive

✅ **Performance:** Redis < 5ms, PostgreSQL < 50ms, pgvector < 200ms  
✅ **Escalabilidade:** Cada nível otimizado para seu caso de uso  
✅ **Custo-efetivo:** Cache reduz queries ao DB em ~95%  
✅ **Flexibilidade:** Fácil adicionar novos níveis ou ajustar TTLs  
✅ **RAG-ready:** pgvector prepara para busca semântica avançada  
✅ **Analytics:** PostgreSQL tem dados completos para BI  

### Negative

❌ **Complexidade:** 3 sistemas para gerenciar  
❌ **Consistência:** Possibilidade de dados desatualizados no cache  
❌ **Custo Infraestrutura:** Redis + PostgreSQL + pgvector  
❌ **Debugging:** Mais difícil rastrear onde dados estão  

### Mitigations

- **Cache Invalidation:** Invalidar Redis ao adicionar nova mensagem
- **Monitoring:** Dashboards mostrando hit rate de cada nível
- **Fallback:** Se Redis falhar, usar PostgreSQL diretamente
- **Documentation:** Documentar claramente quando usar cada nível

---

## Alternatives Considered

### 1. Apenas PostgreSQL

**Pros:** Simples, único sistema, sempre consistente  
**Cons:** Latência alta (~50-100ms), não escala bem  
**Rejected:** Performance inadequada para tempo real

### 2. Apenas Redis

**Pros:** Extremamente rápido, simples  
**Cons:** Persistência frágil, sem analytics, limitado em volume  
**Rejected:** Não resolve todos os casos de uso

### 3. Elasticsearch para busca

**Pros:** Busca full-text excelente  
**Cons:** Não tem embeddings nativos, complexidade operacional  
**Rejected:** pgvector é suficiente e já temos PostgreSQL

### 4. Vector DB dedicado (Pinecone, Weaviate)

**Pros:** Otimizado para embeddings, features avançadas  
**Cons:** Custo alto, mais um sistema para gerenciar  
**Rejected:** pgvector suficiente para MVP

---

## Implementation Roadmap

### Fase 1 (Sprint 5): Short + Mid term

- [x] Implementar cache Redis (short-term)
- [x] Usar PostgreSQL existente (mid-term)
- [x] MemoryService com fallback
- [ ] Monitoring de hit rate

### Fase 2 (Pós-MVP): Long-term

- [ ] Setup pgvector
- [ ] Gerar embeddings de mensagens
- [ ] Implementar semantic search
- [ ] Usar em RAG (INTERMEDIATE level)

### Fase 3 (Escala): Otimização

- [ ] Redis Cluster para HA
- [ ] PostgreSQL read replicas
- [ ] Archive para S3 (> 30 dias)
- [ ] Fine-tuning de embeddings

---

## Performance Benchmarks

### Expected Performance

| Nível | Latência P50 | Latência P99 | Cache Hit Rate |
|-------|--------------|--------------|----------------|
| Redis | < 5ms | < 10ms | 95% |
| PostgreSQL | < 50ms | < 100ms | N/A |
| pgvector | < 200ms | < 500ms | N/A |

### Load Testing

```python
# Simular 1000 conversas simultâneas
@pytest.mark.benchmark
async def test_memory_performance():
    tasks = []
    
    for i in range(1000):
        tasks.append(get_conversation_context(f"conv_{i}"))
    
    start = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    assert elapsed < 5.0  # < 5s para 1000 requests
```

---

## Monitoring & Alerts

### Métricas Importantes

```python
# Redis
redis_hit_rate = cache_hits / total_requests
redis_memory_usage = redis.info()["used_memory"]

# PostgreSQL
avg_query_time = pg_stat_statements.mean_exec_time
slow_queries = queries WHERE exec_time > 100ms

# pgvector
vector_search_latency = histogram(search_time)
embedding_generation_rate = embeddings_per_minute
```

### Alertas

```yaml
alerts:
  - name: redis_hit_rate_low
    condition: redis_hit_rate < 0.85
    action: investigate_cache_invalidation
  
  - name: postgres_slow_queries
    condition: avg_query_time > 100ms
    action: check_indexes
  
  - name: redis_memory_high
    condition: redis_memory_usage > 1.5GB
    action: increase_redis_memory_or_reduce_ttl
```

---

## Related Decisions

- ADR-001: DDD Architecture (MemoryService é Domain Service)
- ADR-002: Message Buffer Strategy (Buffer usa Redis)

---

## References

- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Gemini Embeddings](https://ai.google.dev/docs/embeddings_guide)
- [RAG Architecture Patterns](https://www.pinecone.io/learn/retrieval-augmented-generation/)

---

**Last Updated:** 2026-03-27  
**Review Date:** 2026-12-27 (após implementar pgvector)
