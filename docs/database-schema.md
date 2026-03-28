# 🗄️ TactoFlow - Database Schema

**Versão:** 0.0.1  
**Última Atualização:** 2026-03-27  
**SGBD:** PostgreSQL 16+ com extensão pgvector  
**ORM:** SQLAlchemy 2.0 (async)  
**Migrations:** Alembic

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Convenções](#convenções)
3. [Tabelas Core](#tabelas-core)
4. [Tabelas de Domínio](#tabelas-de-domínio)
5. [Tabelas de Vector Store](#tabelas-de-vector-store)
6. [Índices](#índices)
7. [Constraints](#constraints)
8. [Triggers](#triggers)
9. [Migrations](#migrations)

---

## 🎯 VISÃO GERAL

### Princípios de Design

1. **Multi-tenancy:** Toda tabela com dados de negócio tem `restaurant_id`
2. **Soft Delete:** Usar `deleted_at` ao invés de DELETE físico
3. **Audit Trail:** Todas tabelas têm `created_at`, `updated_at`
4. **UUIDs:** Chaves primárias são UUIDs (exceto tabelas de configuração)
5. **Normalização:** 3NF onde faz sentido, desnormalizar para performance quando necessário
6. **Indexes:** Indexar foreign keys e campos de busca
7. **Constraints:** Validar no banco E na aplicação (defesa em profundidade)

### Extensões PostgreSQL

```sql
-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Busca fuzzy
```

---

## 📏 CONVENÇÕES

### Naming Conventions

- **Tabelas:** `snake_case`, plural (ex: `restaurants`, `messages`)
- **Colunas:** `snake_case`
- **Foreign Keys:** `{tabela_singular}_id` (ex: `restaurant_id`)
- **Indexes:** `idx_{tabela}_{coluna(s)}`
- **Unique Constraints:** `uq_{tabela}_{coluna(s)}`
- **Check Constraints:** `ck_{tabela}_{regra}`

### Tipos de Dados Padrão

```sql
-- IDs
id UUID PRIMARY KEY DEFAULT uuid_generate_v4()

-- Timestamps
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
deleted_at TIMESTAMPTZ

-- Strings
name VARCHAR(255)
description TEXT
url VARCHAR(2048)

-- JSON
metadata JSONB

-- Enums
status INTEGER NOT NULL
```

---

## 🏗️ TABELAS CORE

### 1. `restaurants`

**Descrição:** Tabela principal de restaurantes (tenant)

```sql
CREATE TABLE restaurants (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Dados básicos
    name VARCHAR(255) NOT NULL,
    prompt_default TEXT NOT NULL,
    menu_url VARCHAR(2048) NOT NULL,
    
    -- Horários (JSON estruturado)
    opening_hours JSONB NOT NULL,
    
    -- Integrações
    integration_type INTEGER NOT NULL,  -- 1=META, 2=JOIN
    automation_type INTEGER NOT NULL,   -- 1=BASIC, 2=INTERMEDIATE, 3=ADVANCED
    
    -- Dados Tacto
    chave_grupo_empresarial UUID NOT NULL,
    canal_master_id VARCHAR(255) NOT NULL,
    empresa_base_id VARCHAR(100) NOT NULL,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Auditoria
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT uq_restaurants_name UNIQUE (name) WHERE deleted_at IS NULL,
    CONSTRAINT uq_restaurants_canal_master_id UNIQUE (canal_master_id) WHERE deleted_at IS NULL,
    CONSTRAINT ck_restaurants_integration_type CHECK (integration_type IN (1, 2)),
    CONSTRAINT ck_restaurants_automation_type CHECK (automation_type IN (1, 2, 3)),
    CONSTRAINT ck_restaurants_name_length CHECK (length(name) >= 3)
);

-- Índices
CREATE INDEX idx_restaurants_canal_master_id ON restaurants(canal_master_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_restaurants_is_active ON restaurants(is_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_restaurants_chave_grupo ON restaurants(chave_grupo_empresarial);

-- Comentários
COMMENT ON TABLE restaurants IS 'Restaurantes (tenants do sistema)';
COMMENT ON COLUMN restaurants.opening_hours IS 'Horários de funcionamento em formato JSON';
COMMENT ON COLUMN restaurants.canal_master_id IS 'ID do canal na integração (Join/WhatsApp)';
```

**Exemplo de `opening_hours` JSON:**
```json
{
  "monday": {"opens_at": "18:00", "closes_at": "23:00"},
  "tuesday": {"opens_at": "18:00", "closes_at": "23:00"},
  "wednesday": {"is_closed": true},
  "thursday": {"opens_at": "18:00", "closes_at": "23:00"},
  "friday": {"opens_at": "18:00", "closes_at": "00:00"},
  "saturday": {"opens_at": "18:00", "closes_at": "00:00"},
  "sunday": {"opens_at": "18:00", "closes_at": "23:00"}
}
```

---

### 2. `integrations`

**Descrição:** Configurações de integração de cada restaurante

```sql
CREATE TABLE integrations (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    
    -- Tipo de integração
    integration_type INTEGER NOT NULL,  -- 1=META, 2=JOIN
    
    -- Credenciais (criptografadas)
    credentials JSONB NOT NULL,
    
    -- Configurações
    webhook_url VARCHAR(2048),
    webhook_secret VARCHAR(255),
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    
    -- Auditoria
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_integrations_restaurant_type UNIQUE (restaurant_id, integration_type)
);

-- Índices
CREATE INDEX idx_integrations_restaurant_id ON integrations(restaurant_id);
CREATE INDEX idx_integrations_is_active ON integrations(is_active);

COMMENT ON TABLE integrations IS 'Configurações de integração (Join, WhatsApp Business, etc)';
COMMENT ON COLUMN integrations.credentials IS 'Credenciais criptografadas em JSON';
```

**Exemplo de `credentials` JSON (Join):**
```json
{
  "instance_key": "encrypted_instance_key",
  "token_cliente": "encrypted_token"
}
```

---

## 💬 TABELAS DE DOMÍNIO

### 3. `conversations`

**Descrição:** Conversas com clientes

```sql
CREATE TABLE conversations (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    
    -- Cliente
    customer_phone VARCHAR(20) NOT NULL,  -- Formato: 5511999999999
    customer_name VARCHAR(255),
    
    -- Controle de IA
    is_ai_active BOOLEAN NOT NULL DEFAULT TRUE,
    ai_disabled_until TIMESTAMPTZ,
    ai_disabled_reason VARCHAR(100),  -- 'human_intervention', 'manual', etc
    
    -- Metadata
    metadata JSONB,
    
    -- Auditoria
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT uq_conversations_restaurant_phone UNIQUE (restaurant_id, customer_phone),
    CONSTRAINT ck_conversations_phone_format CHECK (customer_phone ~ '^\d{10,15}$')
);

-- Índices
CREATE INDEX idx_conversations_restaurant_id ON conversations(restaurant_id);
CREATE INDEX idx_conversations_customer_phone ON conversations(customer_phone);
CREATE INDEX idx_conversations_is_ai_active ON conversations(is_ai_active);
CREATE INDEX idx_conversations_last_message_at ON conversations(last_message_at DESC);

-- Índice composto para queries comuns
CREATE INDEX idx_conversations_restaurant_active ON conversations(restaurant_id, is_ai_active, last_message_at DESC);

COMMENT ON TABLE conversations IS 'Conversas/threads com clientes';
COMMENT ON COLUMN conversations.ai_disabled_until IS 'IA fica pausada até este timestamp';
```

---

### 4. `messages`

**Descrição:** Mensagens individuais

```sql
CREATE TABLE messages (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Conteúdo
    body TEXT NOT NULL,
    
    -- Direção e origem
    direction VARCHAR(20) NOT NULL,  -- 'incoming', 'outgoing'
    source VARCHAR(20) NOT NULL,     -- 'app', 'phone', 'ai'
    from_me BOOLEAN NOT NULL,
    
    -- Referências externas
    external_id VARCHAR(255),  -- ID da Join/WhatsApp
    
    -- Mídia
    media_url VARCHAR(2048),
    media_type VARCHAR(50),
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    timestamp TIMESTAMPTZ NOT NULL,  -- Timestamp da mensagem original
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT ck_messages_direction CHECK (direction IN ('incoming', 'outgoing')),
    CONSTRAINT ck_messages_source CHECK (source IN ('app', 'phone', 'ai')),
    CONSTRAINT uq_messages_external_id UNIQUE (external_id) WHERE external_id IS NOT NULL
);

-- Índices
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX idx_messages_external_id ON messages(external_id) WHERE external_id IS NOT NULL;

-- Índice para busca full-text (futuro)
CREATE INDEX idx_messages_body_trgm ON messages USING gin (body gin_trgm_ops);

-- Particionamento por data (considerar para futuro quando volume crescer)
-- CREATE TABLE messages_2026_03 PARTITION OF messages FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

COMMENT ON TABLE messages IS 'Mensagens individuais das conversas';
COMMENT ON COLUMN messages.timestamp IS 'Timestamp original da mensagem (não criação no DB)';
COMMENT ON COLUMN messages.from_me IS 'Mensagem enviada por nós (não pelo cliente)';
```

---

### 5. `message_buffer`

**Descrição:** Buffer temporário de mensagens (alternativa ao Redis para persistência)

**Nota:** Esta tabela é opcional. Prefira Redis para buffer em produção.

```sql
CREATE TABLE message_buffer (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Mensagens agrupadas
    messages JSONB NOT NULL,  -- Array de mensagens
    
    -- Controle de processamento
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'processing', 'processed', 'failed'
    process_after TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    
    -- Auditoria
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT ck_message_buffer_status CHECK (status IN ('pending', 'processing', 'processed', 'failed'))
);

-- Índices
CREATE INDEX idx_message_buffer_process_after ON message_buffer(process_after) WHERE status = 'pending';
CREATE INDEX idx_message_buffer_status ON message_buffer(status);
CREATE INDEX idx_message_buffer_conversation_id ON message_buffer(conversation_id);

-- Auto-delete após 24h (via cron job ou trigger)
CREATE INDEX idx_message_buffer_cleanup ON message_buffer(created_at) WHERE status IN ('processed', 'failed');

COMMENT ON TABLE message_buffer IS 'Buffer temporário para agrupamento de mensagens';
```

---

### 6. `ai_interactions`

**Descrição:** Log de interações com IA (para analytics e debugging)

```sql
CREATE TABLE ai_interactions (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    
    -- Input/Output
    user_input TEXT NOT NULL,
    ai_output TEXT NOT NULL,
    
    -- Contexto usado
    system_prompt TEXT,
    conversation_context JSONB,
    
    -- Metadados da IA
    model_used VARCHAR(100),
    tokens_used INTEGER,
    response_time_ms INTEGER,
    
    -- Detecção de intenção
    detected_intent VARCHAR(100),
    intent_confidence DECIMAL(3, 2),
    
    -- Estratégia usada
    strategy_used VARCHAR(50),  -- 'basic', 'intermediate', 'advanced'
    
    -- Status
    status VARCHAR(20) NOT NULL,  -- 'success', 'error', 'filtered'
    error_message TEXT,
    
    -- Auditoria
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT ck_ai_interactions_status CHECK (status IN ('success', 'error', 'filtered'))
);

-- Índices
CREATE INDEX idx_ai_interactions_restaurant_id ON ai_interactions(restaurant_id);
CREATE INDEX idx_ai_interactions_conversation_id ON ai_interactions(conversation_id);
CREATE INDEX idx_ai_interactions_created_at ON ai_interactions(created_at DESC);
CREATE INDEX idx_ai_interactions_status ON ai_interactions(status);

-- Particionamento por mês (recomendado para volume alto)
-- ALTER TABLE ai_interactions PARTITION BY RANGE (created_at);

COMMENT ON TABLE ai_interactions IS 'Log de todas interações com IA para analytics e debugging';
```

---

### 7. `orders` (FUTURO)

**Descrição:** Pedidos criados pelo sistema

```sql
CREATE TABLE orders (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE SET NULL,
    
    -- Número do pedido (sequencial por restaurante)
    order_number INTEGER NOT NULL,
    
    -- Cliente
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255),
    
    -- Endereço de entrega
    delivery_address JSONB NOT NULL,
    
    -- Itens (desnormalizado para performance)
    items JSONB NOT NULL,
    
    -- Valores
    subtotal DECIMAL(10, 2) NOT NULL,
    delivery_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
    discount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    
    -- Pagamento
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Integração Tacto
    tacto_order_id VARCHAR(255),
    synced_at TIMESTAMPTZ,
    
    -- Timestamps
    estimated_delivery_time TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    
    -- Auditoria
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_orders_restaurant_number UNIQUE (restaurant_id, order_number),
    CONSTRAINT ck_orders_status CHECK (status IN ('pending', 'confirmed', 'preparing', 'out_for_delivery', 'delivered', 'cancelled')),
    CONSTRAINT ck_orders_payment_status CHECK (payment_status IN ('pending', 'paid', 'failed'))
);

-- Índices
CREATE INDEX idx_orders_restaurant_id ON orders(restaurant_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_orders_customer_phone ON orders(customer_phone);

COMMENT ON TABLE orders IS 'Pedidos criados pelo sistema (FUTURO - nível ADVANCED)';
```

---

## 🧠 TABELAS DE VECTOR STORE

### 8. `message_embeddings`

**Descrição:** Embeddings de mensagens para RAG (pgvector)

```sql
CREATE TABLE message_embeddings (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- Embedding
    embedding VECTOR(768),  -- Gemini embedding-001 tem 768 dimensões
    
    -- Metadata para filtragem
    content TEXT NOT NULL,  -- Cópia do texto para referência
    metadata JSONB,
    
    -- Auditoria
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_message_embeddings_message UNIQUE (message_id)
);

-- Índices vetoriais
CREATE INDEX idx_message_embeddings_vector ON message_embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Índice para multi-tenancy
CREATE INDEX idx_message_embeddings_restaurant_id ON message_embeddings(restaurant_id);

-- Índice GIN para metadata
CREATE INDEX idx_message_embeddings_metadata ON message_embeddings USING gin (metadata);

COMMENT ON TABLE message_embeddings IS 'Embeddings de mensagens para busca semântica (RAG)';
```

**Queries de exemplo:**
```sql
-- Buscar mensagens similares
SELECT 
    me.content,
    me.embedding <=> '[0.1, 0.2, ...]'::vector AS distance
FROM message_embeddings me
WHERE me.restaurant_id = 'restaurant_uuid'
ORDER BY me.embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

---

### 9. `menu_embeddings`

**Descrição:** Embeddings do cardápio para RAG

```sql
CREATE TABLE menu_embeddings (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    
    -- Produto/item
    product_name VARCHAR(255) NOT NULL,
    product_description TEXT,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    
    -- Embedding
    embedding VECTOR(768),
    
    -- Metadata
    metadata JSONB,
    
    -- Sincronização
    synced_from_tacto_at TIMESTAMPTZ,
    
    -- Auditoria
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Índices
CREATE INDEX idx_menu_embeddings_vector ON menu_embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

CREATE INDEX idx_menu_embeddings_restaurant_id ON menu_embeddings(restaurant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_menu_embeddings_category ON menu_embeddings(category);

COMMENT ON TABLE menu_embeddings IS 'Embeddings de itens do cardápio para RAG (INTERMEDIATE/ADVANCED)';
```

---

## 🔍 ÍNDICES ADICIONAIS

### Índices Compostos para Performance

```sql
-- Conversas ativas por restaurante
CREATE INDEX idx_conversations_active_lookup 
    ON conversations(restaurant_id, is_ai_active, last_message_at DESC)
    WHERE deleted_at IS NULL;

-- Mensagens recentes por conversa
CREATE INDEX idx_messages_conversation_timeline 
    ON messages(conversation_id, timestamp DESC);

-- Busca de restaurante por canal
CREATE INDEX idx_restaurants_canal_lookup 
    ON restaurants(canal_master_id, is_active)
    WHERE deleted_at IS NULL;
```

### Índices para Analytics

```sql
-- Estatísticas por período
CREATE INDEX idx_messages_analytics 
    ON messages(conversation_id, created_at, direction);

-- Estatísticas de IA
CREATE INDEX idx_ai_interactions_analytics 
    ON ai_interactions(restaurant_id, created_at, status, strategy_used);
```

---

## ⚙️ CONSTRAINTS

### Check Constraints Importantes

```sql
-- Garantir que totais de pedidos são positivos
ALTER TABLE orders 
    ADD CONSTRAINT ck_orders_totals_positive 
    CHECK (subtotal >= 0 AND total >= 0);

-- Garantir que discount não excede subtotal
ALTER TABLE orders 
    ADD CONSTRAINT ck_orders_discount_valid 
    CHECK (discount <= subtotal);

-- Validar formato de telefone
ALTER TABLE conversations 
    ADD CONSTRAINT ck_conversations_phone_format 
    CHECK (customer_phone ~ '^\d{10,15}$');

-- Validar URLs
ALTER TABLE restaurants 
    ADD CONSTRAINT ck_restaurants_menu_url 
    CHECK (menu_url ~ '^https?://');
```

---

## 🔄 TRIGGERS

### 1. Auto-update `updated_at`

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar em todas tabelas relevantes
CREATE TRIGGER trigger_restaurants_updated_at
    BEFORE UPDATE ON restaurants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Repetir para outras tabelas...
```

---

### 2. Auto-update `last_message_at` em conversations

```sql
CREATE OR REPLACE FUNCTION update_conversation_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations 
    SET last_message_at = NEW.timestamp,
        updated_at = NOW()
    WHERE id = NEW.conversation_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_messages_update_conversation
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_last_message();
```

---

### 3. Auto-increment `order_number` por restaurante

```sql
CREATE OR REPLACE FUNCTION set_order_number()
RETURNS TRIGGER AS $$
BEGIN
    SELECT COALESCE(MAX(order_number), 0) + 1
    INTO NEW.order_number
    FROM orders
    WHERE restaurant_id = NEW.restaurant_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_orders_set_number
    BEFORE INSERT ON orders
    FOR EACH ROW
    WHEN (NEW.order_number IS NULL)
    EXECUTE FUNCTION set_order_number();
```

---

## 📦 MIGRATIONS

### Estrutura de Migrations (Alembic)

```
infrastructure/persistence/migrations/
├── alembic.ini
├── env.py
└── versions/
    ├── 001_initial_schema.py
    ├── 002_add_integrations.py
    ├── 003_add_message_buffer.py
    ├── 004_add_ai_interactions.py
    └── 005_add_vector_store.py
```

### Migration Inicial

```python
# versions/001_initial_schema.py

"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMPTZ

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Habilitar extensões
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgvector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    
    # Criar tabela restaurants
    op.create_table(
        'restaurants',
        sa.Column('id', UUID, primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('prompt_default', sa.Text, nullable=False),
        sa.Column('menu_url', sa.String(2048), nullable=False),
        sa.Column('opening_hours', JSONB, nullable=False),
        sa.Column('integration_type', sa.Integer, nullable=False),
        sa.Column('automation_type', sa.Integer, nullable=False),
        sa.Column('chave_grupo_empresarial', UUID, nullable=False),
        sa.Column('canal_master_id', sa.String(255), nullable=False),
        sa.Column('empresa_base_id', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', TIMESTAMPTZ, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', TIMESTAMPTZ, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('deleted_at', TIMESTAMPTZ),
    )
    
    # Criar índices
    op.create_index('idx_restaurants_canal_master_id', 'restaurants', ['canal_master_id'])
    op.create_index('idx_restaurants_is_active', 'restaurants', ['is_active'])
    
    # ... continuar com outras tabelas


def downgrade():
    op.drop_table('restaurants')
    # ... reverter outras alterações
```

---

## 🔒 SEGURANÇA

### Row-Level Security (RLS) - Futuro

```sql
-- Habilitar RLS
ALTER TABLE restaurants ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Policy: usuário só vê dados do próprio tenant
CREATE POLICY tenant_isolation ON restaurants
    FOR ALL
    USING (id = current_setting('app.current_restaurant_id')::uuid);
```

### Criptografia de Dados Sensíveis

```sql
-- Instalar pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Função para criptografar credentials
CREATE OR REPLACE FUNCTION encrypt_credentials(data JSONB)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(
        pgp_sym_encrypt(
            data::text,
            current_setting('app.encryption_key')
        ),
        'base64'
    );
END;
$$ LANGUAGE plpgsql;
```

---

## 📊 VIEWS ÚTEIS

### View: Estatísticas por Restaurante

```sql
CREATE OR REPLACE VIEW restaurant_stats AS
SELECT 
    r.id AS restaurant_id,
    r.name,
    COUNT(DISTINCT c.id) AS total_conversations,
    COUNT(m.id) AS total_messages,
    COUNT(m.id) FILTER (WHERE m.direction = 'incoming') AS incoming_messages,
    COUNT(m.id) FILTER (WHERE m.direction = 'outgoing') AS outgoing_messages,
    COUNT(c.id) FILTER (WHERE c.is_ai_active = false) AS ai_disabled_conversations,
    MAX(m.created_at) AS last_message_at
FROM restaurants r
LEFT JOIN conversations c ON c.restaurant_id = r.id
LEFT JOIN messages m ON m.conversation_id = c.id
WHERE r.deleted_at IS NULL
GROUP BY r.id, r.name;
```

### View: Conversas Ativas com Última Mensagem

```sql
CREATE OR REPLACE VIEW active_conversations AS
SELECT 
    c.id,
    c.restaurant_id,
    c.customer_phone,
    c.is_ai_active,
    c.last_message_at,
    m.body AS last_message_body,
    m.direction AS last_message_direction
FROM conversations c
LEFT JOIN LATERAL (
    SELECT body, direction
    FROM messages
    WHERE conversation_id = c.id
    ORDER BY timestamp DESC
    LIMIT 1
) m ON true
WHERE c.last_message_at > NOW() - INTERVAL '24 hours';
```

---

## 🧪 DADOS DE TESTE (Seeds)

```sql
-- Inserir restaurante de teste
INSERT INTO restaurants (
    name, 
    prompt_default, 
    menu_url,
    opening_hours,
    integration_type,
    automation_type,
    chave_grupo_empresarial,
    canal_master_id,
    empresa_base_id
) VALUES (
    'Pizzaria do João - Teste',
    'Você é um assistente cordial da Pizzaria do João...',
    'https://cardapio.pizzariadojoao.com.br',
    '{
        "monday": {"opens_at": "18:00", "closes_at": "23:00"},
        "tuesday": {"opens_at": "18:00", "closes_at": "23:00"},
        "wednesday": {"is_closed": true},
        "thursday": {"opens_at": "18:00", "closes_at": "23:00"},
        "friday": {"opens_at": "18:00", "closes_at": "00:00"},
        "saturday": {"opens_at": "18:00", "closes_at": "00:00"},
        "sunday": {"opens_at": "18:00", "closes_at": "23:00"}
    }'::jsonb,
    2,  -- JOIN
    1,  -- BASIC
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid,
    'canal-teste-123',
    '1'
);
```

---

## 📝 CHANGELOG

### [0.0.1] - 2026-03-27

#### Definido
- Schema completo de todas tabelas core
- Índices para performance
- Constraints de validação
- Triggers de auditoria
- Estrutura de migrations

#### Planejado (Futuro)
- Particionamento de tabelas grandes
- Row-Level Security
- Materialzed views para analytics
- Archive tables para dados antigos

---

**Mantido por:** Engineering Team  
**Última Revisão:** 2026-03-27  
**Próxima Revisão:** Após primeira migration
