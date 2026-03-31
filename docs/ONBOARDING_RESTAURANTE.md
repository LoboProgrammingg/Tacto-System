# Onboarding de Restaurante — Guia Completo

> Baseado na implementação real do TactoFlow.
> Cobre: criação do restaurante, sincronização do menu com a Tacto API e configuração do webhook na Join.

---

## Pré-requisitos

Antes de começar, tenha em mãos as seguintes informações fornecidas pela Tacto:

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `name` | Nome do restaurante | `CHEFF CACHACARIA` |
| `chave_grupo_empresarial` | UUID da empresa na Tacto | `44464DBF-6A46-481D-A9BC-79DBBDACB3D4` |
| `empresa_base_id` | ID base da empresa na Tacto | `1` |
| `canal_master_id` | Chave da instância Join (nome da instância) | `wp-empresa-453` |
| `menu_url` | URL do Webgula para delivery | `https://v2.webgula.com.br/matupa-cheff/delivery` |
| `telefone` | Número conectado na instância Join | `5566999670755` |

---

## Etapa 1 — Criar o Restaurante

Faça um `POST` para `/api/v1/restaurants/`:

```bash
curl -X POST http://65.21.240.57:8000/api/v1/restaurants/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NOME DO RESTAURANTE",
    "menu_url": "https://v2.webgula.com.br/slug-do-restaurante/delivery",
    "chave_grupo_empresarial": "UUID-DA-EMPRESA",
    "canal_master_id": "wp-empresa-XXX",
    "empresa_base_id": "1",
    "integration_type": 2,
    "automation_type": 1
  }'
```

### Parâmetros importantes

| Campo | Tipo | Valores | Descrição |
|-------|------|---------|-----------|
| `integration_type` | int | `2` = Join | Sempre `2` para integração Join Developer |
| `automation_type` | int | `1` = Basic, `2` = Intermediate, `3` = Advanced | Nível do agente de IA |
| `opening_hours` | objeto | opcional | Se omitido, preenchido automaticamente pelo tacto-sync |

### Níveis de automação (`automation_type`)

| Valor | Nome | Comportamento |
|-------|------|---------------|
| `1` | Basic | Informações institucionais apenas |
| `2` | Intermediate | Menu completo via RAG + recomendações |
| `3` | Advanced | Criação de pedidos completa |

### Resposta esperada

```json
{
  "id": "133d415d-5b9a-4bae-b618-0abda7a109d3",
  "name": "NOME DO RESTAURANTE",
  "canal_master_id": "wp-empresa-XXX",
  "is_active": true,
  ...
}
```

**Guarde o `id` retornado** — será usado nas próximas etapas.

---

## Etapa 2 — Sincronizar o Menu (Tacto Sync)

O tacto-sync busca o cardápio completo na API externa da Tacto, gera embeddings com Gemini e salva no pgvector. Também atualiza automaticamente os horários de funcionamento.

```bash
curl -X POST http://65.21.240.57:8000/api/v1/restaurants/{RESTAURANT_ID}/tacto-sync
```

Substitua `{RESTAURANT_ID}` pelo `id` retornado na Etapa 1.

### O que esse endpoint faz

1. Autentica na API externa da Tacto usando `chave_grupo_empresarial` + `empresa_base_id`
2. Busca todos os itens do cardápio
3. Gera embeddings via Gemini para cada item (nome + descrição, nunca preços)
4. Salva no pgvector para busca semântica
5. Atualiza os horários de funcionamento do restaurante automaticamente

### Resposta esperada

```json
{
  "restaurant_id": "133d415d-5b9a-4bae-b618-0abda7a109d3",
  "restaurant_name": "NOME DO RESTAURANTE",
  "items_synced": 162,
  "categories": ["Pizzas", "Bebidas", "Porções", ...],
  "address": "Av. Exemplo, 1001 - Cidade/UF",
  "hours_text": "- Segunda: 18:00 às 22:30\n- ..."
}
```

> **Quando repetir o sync?** Sempre que o cardápio mudar na plataforma Tacto. O sistema faz sync incremental — só re-gera embeddings de itens novos ou alterados.

---

## Etapa 3 — Configurar o Webhook na Join

### 3a. Configurar a URL de webhook na Join API

Este endpoint configura para qual URL a instância Join vai enviar os eventos de mensagem.

```bash
curl -X POST "https://api-prd.joindeveloper.com.br/webhook/configurarinstancia" \
  -H "tokenCliente: SEU_TOKEN_CLIENTE" \
  -H "instancia: wp-empresa-XXX" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://65.21.240.57:8000/api/v1/webhook/join"}'
```

**Parâmetros obrigatórios:**

| Onde | Campo | Valor |
|------|-------|-------|
| Header | `tokenCliente` | Token do cliente Join (em `JOIN_TOKEN_CLIENTE` no `.env`) |
| Header | `instancia` | Nome da instância Join (ex: `wp-empresa-453`) |
| Body | `url` | URL do webhook do TactoFlow |

**Resposta esperada:**

```json
{
  "evento": "Definir Webhook",
  "status": "Sucesso",
  "instancia": "wp-empresa-453",
  "Webhook": "http://65.21.240.57:8000/api/v1/webhook/join"
}
```

> ⚠️ **Atenção ao endpoint correto:** o endpoint é `/webhook/configurarinstancia` (não `/webhook/configurar`). O campo `instancia` vai no **header**, não no body.

### 3b. Conectar a instância Join ao restaurante no TactoFlow

Este passo vincula a instância Join ao restaurante no banco de dados, habilitando o roteamento multi-tenant de mensagens.

```bash
curl -X POST http://65.21.240.57:8000/api/v1/instances/connect \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "UUID-DO-RESTAURANTE",
    "instancia": "wp-empresa-XXX"
  }'
```

**Resposta esperada:**

```json
{
  "success": true,
  "message": "Instance 'wp-empresa-XXX' connected to restaurant 'NOME DO RESTAURANTE'",
  "restaurant_id": "UUID-DO-RESTAURANTE",
  "restaurant_name": "NOME DO RESTAURANTE",
  "instance_key": "wp-empresa-XXX"
}
```

---

## Como funciona o roteamento multi-tenant

Cada restaurante tem um `canal_master_id` único que corresponde ao `nome` da instância na Join (`wp-empresa-XXX`).

Quando a Join envia um webhook:

```
Join → POST /api/v1/webhook/join → {"instance": "wp-empresa-453", ...}
                                          ↓
                            find_by_canal_master_id("wp-empresa-453")
                                          ↓
                               Restaurante: CHEFF CACHACARIA
                                          ↓
                        Pipeline de IA com cardápio isolado
```

Cada restaurante tem suas próprias `conversations`, `messages` e `menu_embeddings` — zero vazamento entre tenants.

---

## Checklist completo

```
[ ] 1. Coletar dados do restaurante (nome, chave_grupo_empresarial, empresa_base_id, canal_master_id, menu_url)
[ ] 2. POST /api/v1/restaurants/ → guardar o restaurant_id retornado
[ ] 3. POST /api/v1/restaurants/{id}/tacto-sync → confirmar items_synced > 0
[ ] 4. Configurar webhook na Join API (endpoint: /webhook/configurarinstancia)
[ ] 5. POST /api/v1/instances/connect → vincular instância ao restaurante
[ ] 6. Enviar mensagem de teste e verificar logs: docker logs tactoflow_api_prod --tail=50
```

---

## Verificando nos logs

Após configurar, envie uma mensagem de teste para o WhatsApp do restaurante. Nos logs você deve ver:

```
webhook_raw_fields   instance=wp-empresa-XXX  from_me=False ...
webhook_accepted     phone=55...  message_preview=Ola...
buffer_processing    combined_preview=Ola  message_count=1
```

Se aparecer `Restaurant not found for instance_key`, o `canal_master_id` no banco não bate com o `nome` da instância na Join. Verifique com:

```sql
SELECT name, canal_master_id FROM restaurants WHERE name ILIKE '%nome%';
```

---

## Variáveis de ambiente relevantes

```env
# Tacto API
TACTO_AUTH_URL=https://accounts.tactonuvem.com.br/connect/token
TACTO_API_BASE_URL=https://api-externa.tactonuvem.com.br

# Join Developer
JOIN_API_BASE_URL=https://api-prd.joindeveloper.com.br
JOIN_TOKEN_CLIENTE=seu-token-aqui

# Servidor
# Webhook URL pública: http://IP:8000/api/v1/webhook/join
```

---

## Endpoints de referência

| Ação | Método | Endpoint |
|------|--------|----------|
| Criar restaurante | `POST` | `/api/v1/restaurants/` |
| Listar restaurantes | `GET` | `/api/v1/restaurants/` |
| Buscar restaurante | `GET` | `/api/v1/restaurants/{id}` |
| Sincronizar menu | `POST` | `/api/v1/restaurants/{id}/tacto-sync` |
| Ver dados Tacto | `GET` | `/api/v1/restaurants/{id}/tacto-data` |
| Listar instâncias Join | `GET` | `/api/v1/instances/` |
| Status da instância | `GET` | `/api/v1/instances/{key}/status` |
| Conectar instância | `POST` | `/api/v1/instances/connect` |
| Configurar webhook | `POST` | `/api/v1/instances/webhook` |
| Health check | `GET` | `/health` |
