# TODO — Tacto System

**Última atualização:** 2026-03-30
**Critério:** Itens pendentes de implementação confirmados — código, infra e produto.

---

## 🔴 Alta Prioridade

### Testes Automatizados
- [x] Setup pytest + pytest-asyncio (70 testes unitários passando)
- [x] Testes para `ProcessIncomingMessageUseCase` (9 testes)
- [x] Testes para `MessageBufferService` (11 testes)
- [x] Testes para `Level1Agent` (14 testes)
- [x] Testes para `SyncTactoMenu` helpers e MenuItem (21 testes)
- [x] Estrutura de testes de integração com PostgreSQL (auto-skip se DB indisponível)
- [ ] Coverage mínima: 70% em lógica de negócio (pendente medição)

### Multi-tenant — Segurança
- [x] Validar HMAC da assinatura Join API no webhook (`webhook_join.py`) — `JOIN_WEBHOOK_SECRET`
- [x] CORS em produção: whitelist configurável via `CORS_ORIGINS` no `.env`
- [x] `secret_key` padrão "change-me-in-production" validado na startup — lança erro se não alterado em `DEBUG=false`

---

## 🟡 Média Prioridade

### Funcionalidades de Produto

- [ ] **Botão interativo CTA URL (WhatsApp)** — verificar se Join Developer API suporta `type: "cta_url"` em mensagens interativas. Se sim:
  - Adicionar `send_url_button(instance_key, phone, body, button_text, url)` ao `JoinClient`
  - Adicionar ao port `MessagingClient`
  - Atualizar `Level1Agent`: usar botão em vez de texto formatado quando `menu_url_sent`
  - Fallback para texto formatado se API não suportar

- [ ] **Level 2 Agent (transacional)** — agente que cria pedidos reais via Tacto API
  - Implementar `Order` aggregate no domain (`domain/order/`)
  - `OrderRepository` (interface + implementação Postgres)
  - `CreateOrderUseCase`
  - `Level2Agent` (LangGraph StateGraph com tool calling)
  - Detecção de nível de automação no `ProcessIncomingMessageUseCase`

- [ ] **Admin endpoints** — painel de controle interno
  - `GET /api/v1/admin/restaurants` — listar todos os tenants
  - `POST /api/v1/admin/restaurants/{id}/sync-menu` — forçar re-sync de cardápio
  - `POST /api/v1/admin/restaurants/{id}/clear-memory` — limpar memória de cliente
  - `GET /api/v1/admin/stats` — métricas agregadas por restaurante

- [ ] **Logging estruturado em produção** — configurar saída JSON do structlog para integração com Datadog/Grafana/Loki

### Infra e Configuração

- [ ] **`API_KEY` e `RATE_LIMIT_RPM` no `.env.example`** — documentar as novas variáveis adicionadas
- [ ] **CORS origins configurável** — adicionar `CORS_ORIGINS` ao `AppSettings` e `middleware.py`
- [ ] **`docker-compose.yml`** — adicionar healthcheck para o container da API
- [ ] **Alembic migrations** — verificar se há migrations pendentes para tabelas novas

---

## 🟢 Baixa Prioridade / Backlog Futuro

### Produto

- [ ] **Mensagens de áudio** — transcrever áudio via Whisper/Gemini antes de processar
- [ ] **Envio de imagem do cardápio** — gerar e enviar imagem do menu quando solicitado
- [ ] **Notificações proativas** — enviar promoções/lembretes via Join API (campanha)
- [ ] **Dashboard de analytics** — painel web para o dono do restaurante ver métricas

### Técnico

- [ ] **Timeout adaptativo** no `MessageBufferService` — ajustar janela de buffer por padrão de uso do cliente (ver `10 - Infrastructure Improvements.md`)
- [ ] **Row-Level Security (RLS)** no PostgreSQL — isolação multi-tenant no nível do banco (ver `10 - Infrastructure Improvements.md`)
- [ ] **Celery workers** — mover processamento pesado (sync de cardápio, embeddings) para filas assíncronas (ver `10 - Infrastructure Improvements.md`)

---

## ✅ Concluído (referência)

| Item | Concluído em |
|------|-------------|
| DDD Refactoring — 5 fases | 2026-03-27 |
| Level 1 Agent — humanização, RAG, memória 3 níveis | 2026-03-28 |
| WhatsApp text formatting (bold, italic, emojis) | 2026-03-28 |
| Config → `infrastructure/config/config.py` | 2026-03-29 |
| Middlewares → `interfaces/middlewares/` (CORS, Logging, RateLimit, Auth) | 2026-03-29 |
| Vault Obsidian — documentação completa do projeto | 2026-03-29 |
| Circuit breaker (JoinClient + TactoClient) | 2026-03-29 |
| Cache de embeddings incremental (sync_tacto_menu) | 2026-03-29 |
| Migration HNSW (005_hnsw_index.py) | 2026-03-29 |
| Reorganização vector_store → infrastructure/database | 2026-03-29 |
