# Plano de Revisão de Excelência — Tacto-System

**Data:** 2026-03-28
**Fase:** Pós-Refactoring DDD (Fases 1–5 concluídas)
**Objetivo:** Auditoria final de qualidade sênior, limpeza, validação multi-tenant e melhoria da IA

---

## Contexto

Após completar as 5 fases do refactoring DDD, este plano cobre:

1. **Limpeza de código morto** — deletar stubs e arquivos órfãos identificados em auditoria
2. **Validação da arquitetura multi-tenant** — confirmada correta; documentada aqui
3. **Melhoria da IA (Level1Prompts)** — humanização máxima para atendente de restaurante
4. **Nova documentação** — `project-context.md` atualizado com realidade atual do sistema

---

## 1. Auditoria de Arquivos Mortos

### Deletar (confirmado por auditoria — zero consumidores)

| Arquivo | Motivo |
|---------|--------|
| `tacto/application/use_cases/create_order.py` | Stub com import quebrado (`from domain.shared.result` sem `tacto.`), não exportado no `__init__.py`, zero referências |
| `tacto/interfaces/http/routes/webhook.py` | Versão antiga do webhook; substituída inteiramente por `webhook_join.py`; não registrada em nenhum router |
| `tacto/interfaces/workers/message_worker.py` | Stub com TODO; processamento acontece via `BackgroundTasks` do FastAPI no webhook; nunca importado |
| `tacto/interfaces/workers/__init__.py` | Pasta fica vazia após deleção do worker |

### Manter (confirmado como usado)

| Arquivo | Motivo |
|---------|--------|
| `tacto/infrastructure/messaging/instance_phone_cache.py` | Importado e usado em `webhook_join.py` para detectar operador humano via número de telefone da instância |

---

## 2. Arquitetura Multi-Tenant — Validação

A auditoria confirmou que a isolação multi-tenant está **correta e robusta** em todas as camadas.

### Fluxo completo de identificação de tenant

```
JOIN Webhook POST
  body.instance = "51952e2c-..."  ← canal_master_id do restaurante
  ↓
webhook_join.py: extrai instance_key
  ↓
MessageBufferService: buffer por (instance_key, phone) — 5s
  ↓
ProcessIncomingMessageUseCase.execute(dto)
  ↓
restaurant_repo.find_by_canal_master_id(instance_key)
  → Restaurant entity carregada do PostgreSQL
  ↓
Tudo scoped por restaurant_id:
  - conversation_repo.find_by_restaurant_and_phone(restaurant.id, phone)
  - vector_store.search_menu(restaurant.id, embedding)
  - memory: chave Redis = "memory:{restaurant_id}:{phone}:{type}"
  - TactoClient: headers EmpresaId + Tacto-Grupo-Empresarial por chamada
  - JoinClient: header instancia = instance_key por chamada
```

### Isolação por camada — status

| Camada | Chave de Isolação | Status |
|--------|-------------------|--------|
| Conversas (PostgreSQL) | `restaurant_id + customer_phone` | ✅ Correto |
| Mensagens (PostgreSQL) | via `conversation_id → restaurant_id` | ✅ Correto |
| Memória curto/médio prazo (Redis) | `memory:{restaurant_id}:{phone}:{type}` | ✅ Correto |
| Memória longo prazo (PostgreSQL) | `restaurant_id + customer_phone` | ✅ Correto |
| Embeddings de cardápio (pgvector) | `restaurant_id` na busca semântica | ✅ Correto |
| Message buffer (Redis) | `{instance_key}:{phone}` — instance_key é único por restaurante | ✅ Correto |
| TactoClient | Headers `EmpresaId` + `Tacto-Grupo-Empresarial` por chamada | ✅ Correto |
| JoinClient | Header `instancia` = `instance_key` por chamada | ✅ Correto |

### Modelo de credenciais

- **Tacto API**: token OAuth2 global (1 client_id/secret para todos os restaurantes); isolação por headers HTTP por chamada
- **Join API**: token_cliente global; isolação por `instance_key` (canal_master_id) por chamada
- **Gemini**: chave de API global compartilhada; sem isolação necessária (LLM stateless)
- **Redis**: instância compartilhada; isolação por prefixo de chave com `restaurant_id`
- **PostgreSQL**: banco compartilhado; isolação por `restaurant_id` em todas as queries

Para adicionar um novo restaurante:
1. Cadastrar via `POST /api/v1/restaurants` com `canal_master_id` (chave da instância Join), `empresa_base_id` e `chave_grupo_empresarial` (credenciais Tacto por restaurante)
2. Configurar webhook Join via `POST /api/v1/instances/{instance_key}/webhook`
3. Sincronizar cardápio via use case `SyncTactoMenu`

---

## 3. Melhorias da IA (Level1Agent / Level1Prompts)

### Problemas identificados em `tacto/domain/ai_assistance/prompts/level1_prompts.py`

| # | Problema | Impacto |
|---|---------|---------|
| 1 | Fallbacks internos robóticos: `"Nenhum item específico encontrado. Redirecione o cliente para o link do cardápio."` | Aparece no sistema prompt; LLM tende a repetir mecanicamente |
| 2 | `"Sem histórico de longo prazo ainda."` nas seções de memória vazia | Faz a IA parecer que está lendo um formulário |
| 3 | `"Nenhuma instrução específica."` quando `custom_prompt` está vazio | Tom de debug, não de atendente |
| 4 | Regra de ingredientes excessivamente rígida: "TODOS... EXATAMENTE... sem cortar" | Pode gerar dumps de texto sem fluidez conversacional |
| 5 | Nenhum guia para a primeira mensagem da conversa | LLM pode abrir de forma genérica ou robótica |
| 6 | Seção de memória sem exemplos de tom: "mencione naturalmente" é vago | LLM não sabe como soar natural ao referenciar histórico |
| 7 | `MENU_TRIGGER_KEYWORDS` inclui itens genéricos ("pizza", "hamburguer") que deveriam acionar RAG, não o link | Envia link do cardápio quando cliente pede sugestão de sabor |
| 8 | Variações únicas em `get_closed_response()` e `get_human_handoff_response()` | Clientes recorrentes recebem exatamente a mesma mensagem |

### Mudanças planejadas

**A. SYSTEM_PROMPT:**
- Substituir fallbacks por frases omitidas ou em linguagem natural
- Adicionar seção de exemplos: como abrir a conversa, como referenciar histórico
- Suavizar regra de ingredientes: fluidez > completude mecânica
- Guia para primeira mensagem vs. conversa em andamento

**B. `get_closed_response()`:**
- Lista de variações com `random.choice()`
- Incluir próximo horário de abertura quando disponível

**C. `get_human_handoff_response()`:**
- Variações com tom empático real
- Ex: "Tá bom, deixa eu chamar alguém aqui pra te ajudar"

**D. `MENU_TRIGGER_KEYWORDS`:**
- Remover itens genéricos de comida (pizza, hamburguer, etc.) — esses devem acionar RAG
- Manter apenas triggers de preço/link explícito: "preço", "quanto custa", "cardápio", "link", "pedido"

---

## 4. Documentação

### Substituir `docs/project-context.md`

O arquivo atual referencia estrutura obsoleta:
- `domain/ai/` (deletado na FASE 4)
- `domain/assistant/` (deletado na FASE 4)
- `AssistantService`, `BasicStrategy`, `ResponseOrchestrator` (não existem)
- Status "em desenvolvimento inicial" (sistema está funcional)

O novo arquivo deve refletir:
- Arquitetura atual pós-refactoring (todas as 5 fases concluídas)
- Bounded contexts reais: `ai_assistance`, `messaging`, `restaurant`, `customer_memory`, `shared`
- Fluxo completo de mensagem → IA → resposta
- Features implementadas vs. backlog
- Como rodar localmente
- Como adicionar novo restaurante

---

---

## 5. Reorganização de Config e Middlewares

### Motivação

Atualmente `tacto/config/settings.py` está na raiz do pacote como pasta avulsa, e o middleware CORS está embutido diretamente em `tacto/main.py`. A Clean Architecture exige que:
- Leitura de ambiente (settings) viva na **camada de infraestrutura** — é um detalhe técnico, não regra de negócio
- Middlewares vivam na **camada de interface** — são adaptadores HTTP, não lógica de aplicação

### Estrutura alvo

```
tacto/
├── infrastructure/
│   ├── config/                  ← NOVO — pasta dedicada a configurações técnicas
│   │   └── config.py            ← move/reexporta Settings, get_settings()
│   │                               (pode importar de tacto.config.settings
│   │                                mantendo backwards compat ou migrar direto)
│   └── ... (agents, ai, database, etc.)
│
└── interfaces/
    ├── middlewares/             ← NOVO — pasta dedicada a middlewares HTTP
    │   └── middleware.py        ← extrai CORSMiddleware + qualquer futuro
    │                               middleware (logging, rate limit, auth)
    └── http/
        └── ...
```

### O que mover

| De | Para | O que é |
|----|------|---------|
| `tacto/config/settings.py` | `tacto/infrastructure/config/config.py` | Pydantic Settings, `get_settings()`, todas as classes de configuração (AppSettings, DatabaseSettings, RedisSettings, etc.) |
| `main.py` linhas 110–117 (`app.add_middleware(CORSMiddleware, ...)`) | `tacto/interfaces/middlewares/middleware.py` | Função `setup_middlewares(app)` que recebe o `FastAPI` e registra todos os middlewares |

### Impacto em imports

Qualquer arquivo que faz `from tacto.config.settings import get_settings` continua funcionando se:
- `tacto/config/settings.py` virar um shim que reexporta de `tacto.infrastructure.config.config`
- **OU** migrar todos os imports de uma vez (mais limpo)

Busca rápida para mapear impacto antes de executar:
```bash
grep -r "from tacto.config" tacto/ --include="*.py" | wc -l
```

### Exemplo do middleware.py

```python
# tacto/interfaces/middlewares/middleware.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tacto.infrastructure.config.config import get_settings

def setup_middlewares(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Futuro: LoggingMiddleware, RateLimitMiddleware, AuthMiddleware
```

### Exemplo do config.py

```python
# tacto/infrastructure/config/config.py
# Move o conteúdo de tacto/config/settings.py para cá
# Mantém get_settings() com lru_cache
from functools import lru_cache
from pydantic_settings import BaseSettings
# ... (todo o conteúdo atual de settings.py)

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Checklist de execução

- [x] Criar `tacto/infrastructure/config/__init__.py`
- [x] Criar `tacto/infrastructure/config/config.py` (mover conteúdo de `settings.py`)
- [x] Criar `tacto/interfaces/middlewares/__init__.py`
- [x] Criar `tacto/interfaces/middlewares/middleware.py` (extrair de `main.py`)
- [x] Atualizar `main.py`: `from tacto.interfaces.middlewares.middleware import setup_middlewares`
- [x] Converter `tacto/config/settings.py` e `tacto/config/__init__.py` em shims de compatibilidade (zero mudanças nos 14 arquivos existentes)
- [x] Validado: `get_settings()` e `setup_middlewares()` importam e executam corretamente

---

---

## 6. Mensagens WhatsApp Atraentes

### Estado atual (implementado)

Formatação de texto nativa WhatsApp via templates em `Level1Prompts`:
- `format_menu_url_block(url, restaurant_name, message)` — gera bloco formatado com `*negrito*`, `_itálico_` e emojis
- Templates gerais (4 variações) + templates específicos para delivery (3 variações)
- `is_delivery_request(message)` — detecta intenção de entrega para escolher template certo
- `Level1Agent` usa o bloco formatado em vez de `📋 Cardápio: <url_seca>`

**Antes:**
```
Pode sim! É só acessar o link.

📋 Cardápio: https://webgula.com.br/mt-rosario-pizzariadapraca/delivery
```

**Depois (exemplo com template delivery):**
```
A gente faz entrega sim! 🛵

Faça o pedido pelo link:
https://webgula.com.br/mt-rosario-pizzariadapraca/delivery
```

**Depois (exemplo com template geral):**
```
Aqui o cardápio completo 👇

*https://webgula.com.br/mt-rosario-pizzariadapraca/delivery*

_É por lá que fica o preço e você faz o pedido._
```

---

### Backlog: Mensagens Interativas (Botões e Listas)

**Pré-requisito:** verificar se o Join Developer API suporta mensagens interativas.
Verificar em: https://documenter.getpostman.com/view/20242264/2sAXjDdEpW

**WhatsApp suporta nativamente via Business API:**

#### Reply Buttons (até 3 botões)
```json
{
  "type": "interactive",
  "interactive": {
    "type": "button",
    "body": { "text": "Como prefere continuar?" },
    "action": {
      "buttons": [
        { "type": "reply", "reply": { "id": "ver_cardapio", "title": "📋 Ver Cardápio" } },
        { "type": "reply", "reply": { "id": "falar_atendente", "title": "👤 Falar com Atendente" } },
        { "type": "reply", "reply": { "id": "horario",       "title": "🕐 Horário" } }
      ]
    }
  }
}
```

#### CTA URL Button (botão com link — o mais elegante para cardápio)
```json
{
  "type": "interactive",
  "interactive": {
    "type": "cta_url",
    "body": { "text": "Veja o cardápio completo com preços e faça seu pedido!" },
    "action": {
      "name": "cta_url",
      "parameters": {
        "display_text": "📋 Ver Cardápio",
        "url": "https://webgula.com.br/mt-rosario-pizzariadapraca/delivery"
      }
    }
  }
}
```

**Este é o ideal para menus** — o cliente vê "📋 Ver Cardápio" como botão azul clicável, não a URL crua.

#### O que precisa ser implementado

- [ ] Verificar se Join Developer API tem endpoint de mensagem interativa
- [ ] Adicionar `send_interactive_message(instance_key, phone, payload)` ao `JoinClient`
- [ ] Adicionar `send_url_button(instance_key, phone, body, button_text, url)` ao `JoinClient`
- [ ] Adicionar `send_url_button()` ao `MessagingClient` port
- [ ] Atualizar `Level1Agent`: quando `menu_url_sent`, usar `send_url_button()` em vez de texto
- [ ] Fallback para texto formatado se API não suportar interativo

---

## Ordem de Execução

1. ✅ Deletar arquivos mortos
2. ✅ Melhorar `level1_prompts.py`
3. ✅ Atualizar `docs/project-context.md`
4. ✅ Templates formatados WhatsApp para menu URL (texto nativo)
5. ✅ Reorganizar config → `infrastructure/config/config.py`
6. ✅ Extrair middlewares → `interfaces/middlewares/middleware.py`
7. ⬜ Botão interativo CTA URL (verificar suporte Join API primeiro)
