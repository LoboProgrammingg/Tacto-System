# 📋 TactoFlow - Product Backlog & Roadmap

**Versão:** 0.0.1  
**Última Atualização:** 2026-03-27  
**Metodologia:** Sprints de 2 semanas  
**Status:** 🚀 Planejamento Inicial

---

## 📋 ÍNDICE

1. [Visão do Produto](#visão-do-produto)
2. [Roadmap Macro](#roadmap-macro)
3. [Sprint 1: Foundation](#sprint-1-foundation)
4. [Sprint 2: Tacto Integration](#sprint-2-tacto-integration)
5. [Sprint 3: Join Integration](#sprint-3-join-integration)
6. [Sprint 4: AI Core](#sprint-4-ai-core)
7. [Sprint 5: Use Cases & Memory](#sprint-5-use-cases--memory)
8. [Sprint 6: Polish & Deploy](#sprint-6-polish--deploy)
9. [Backlog Futuro](#backlog-futuro)
10. [Critérios de Aceitação](#critérios-de-aceitação)

---

## 🎯 VISÃO DO PRODUTO

### Objetivo

Criar um sistema backend robusto, escalável e pronto para produção que automatize o atendimento via WhatsApp para restaurantes, utilizando IA (Gemini) e integração com APIs externas (Tacto, Join).

### Proposta de Valor

1. **Para Restaurantes:**
   - Atendimento 24/7 automatizado
   - Redução de custo operacional
   - Aumento de conversão de vendas
   - Escalabilidade sem aumentar equipe

2. **Para Tacto:**
   - Produto diferenciado no mercado
   - Integração nativa com plataforma existente
   - Upsell para clientes atuais

### Definição de Pronto (DoD)

Uma feature está pronta quando:
- ✅ Código implementado seguindo DDD
- ✅ Testes unitários escritos (cobertura > 80%)
- ✅ Testes de integração passando
- ✅ Documentação atualizada
- ✅ Code review aprovado
- ✅ Deploy em staging funcional

---

## 🗓️ ROADMAP MACRO

### Fase 1: MVP (3 meses) - Q2 2026

**Objetivo:** Sistema funcional com nível BASIC de automação

- ✅ Infraestrutura base
- ✅ Integração Join + Tacto
- ✅ IA com estratégia BASIC
- ✅ Multi-tenancy funcional
- ✅ Buffer de mensagens
- ✅ Memória de curto prazo

**Entrega:** Sistema em produção atendendo primeiros 3 restaurantes piloto

---

### Fase 2: Intermediate (2 meses) - Q3 2026

**Objetivo:** Adicionar RAG de cardápio e melhorias de IA

- ⏳ Estratégia INTERMEDIATE
- ⏳ RAG completo de cardápio
- ⏳ Melhorias de NLP e intenção
- ⏳ Analytics e dashboards
- ⏳ Monitoramento avançado

**Entrega:** Sistema suportando 20+ restaurantes

---

### Fase 3: Advanced (3 meses) - Q4 2026

**Objetivo:** Sistema completo com criação de pedidos

- 🔮 Estratégia ADVANCED
- 🔮 Criação de pedidos via IA
- 🔮 Integração com pagamentos
- 🔮 Validação de endereços
- 🔮 Notificações proativas

**Entrega:** Produto completo pronto para escala

---

## 📦 SPRINT 1: FOUNDATION (Semanas 1-2)

**Objetivo:** Estabelecer base sólida do projeto

### User Stories

#### US-1.1: Configurar Infraestrutura Base
**Como** desenvolvedor  
**Quero** ter ambiente de desenvolvimento configurado  
**Para que** possa começar a implementar features

**Tarefas:**
- [ ] Configurar PostgreSQL + pgvector via Docker
- [ ] Configurar Redis via Docker
- [ ] Setup do projeto Python (venv, dependências)
- [ ] Configurar Alembic para migrations
- [ ] Criar migration inicial com schema core
- [ ] Configurar pre-commit hooks (black, isort, mypy)
- [ ] Setup de testes (pytest, pytest-asyncio)

**Estimativa:** 5 pontos  
**Prioridade:** CRÍTICA

---

#### US-1.2: Implementar Domain Layer - Restaurant Context
**Como** sistema  
**Quero** ter entidades de domínio bem definidas  
**Para que** regras de negócio sejam respeitadas

**Tarefas:**
- [ ] Implementar `Restaurant` entity (aggregate root)
- [ ] Implementar `Integration` entity
- [ ] Implementar `IntegrationType` value object
- [ ] Implementar `AutomationType` value object
- [ ] Implementar `OpeningHours` value object
- [ ] Implementar `DaySchedule` value object
- [ ] Criar `RestaurantRepository` interface
- [ ] Testes unitários das entities

**Critérios de Aceitação:**
- Todas invariantes validadas
- Value objects são imutáveis
- Repository é apenas interface (sem implementação)
- Cobertura de testes > 90%

**Estimativa:** 8 pontos  
**Prioridade:** CRÍTICA

---

#### US-1.3: Implementar Domain Layer - Messaging Context
**Como** sistema  
**Quero** modelar conversas e mensagens  
**Para que** possa gerenciar comunicação com clientes

**Tarefas:**
- [ ] Implementar `Conversation` entity (aggregate root)
- [ ] Implementar `Message` entity
- [ ] Implementar `MessageDirection` enum
- [ ] Implementar `MessageSource` enum
- [ ] Criar `MessagingRepository` interface
- [ ] Testes unitários

**Critérios de Aceitação:**
- Messages são sempre ordenadas cronologicamente
- Invariante de AI activation respeitada
- Aggregate boundary bem definido

**Estimativa:** 8 pontos  
**Prioridade:** CRÍTICA

---

#### US-1.4: Implementar Shared Kernel
**Como** desenvolvedor  
**Quero** ter componentes compartilhados reutilizáveis  
**Para que** não haja duplicação de código

**Tarefas:**
- [ ] Implementar `Result<T, E>` monad
- [ ] Implementar `PhoneNumber` value object
- [ ] Implementar `TenantId` value object
- [ ] Implementar exceções customizadas
- [ ] Criar helpers de validação
- [ ] Testes unitários

**Estimativa:** 3 pontos  
**Prioridade:** ALTA

---

### Métricas de Sucesso Sprint 1

- ✅ Ambiente local funcional
- ✅ Database criado com migrations
- ✅ Domain layer implementado (Restaurant + Messaging)
- ✅ Cobertura de testes > 80%
- ✅ CI/CD pipeline básico

---

## 📦 SPRINT 2: TACTO INTEGRATION (Semanas 3-4)

**Objetivo:** Integrar completamente com API externa da Tacto

### User Stories

#### US-2.1: Implementar OAuth2 Client
**Como** sistema  
**Quero** obter e cachear tokens OAuth2  
**Para que** possa autenticar na API Tacto

**Tarefas:**
- [ ] Criar `TactoOAuth2Handler` service
- [ ] Implementar token acquisition
- [ ] Implementar token caching (Redis)
- [ ] Implementar auto-refresh (5min antes de expirar)
- [ ] Implementar retry com backoff exponencial
- [ ] Testes de integração com mock

**Critérios de Aceitação:**
- Token cached corretamente no Redis
- Auto-refresh funciona
- Retry em caso de erro
- TTL respeitado

**Estimativa:** 5 pontos  
**Prioridade:** CRÍTICA

---

#### US-2.2: Implementar Tacto API Client
**Como** sistema  
**Quero** consumir endpoints da API Tacto  
**Para que** possa obter dados institucionais e cardápio

**Tarefas:**
- [ ] Criar `TactoClient` base class
- [ ] Implementar headers obrigatórios
- [ ] Implementar `InstitutionalDataService`
  - [ ] Endpoint `/institucional/wg`
  - [ ] Parse de resposta
  - [ ] Cache (1h TTL)
- [ ] Implementar `MenuService`
  - [ ] Endpoint `/menu/rag-full`
  - [ ] Parse de resposta
  - [ ] Cache (4h TTL)
- [ ] Implementar error handling
- [ ] Testes de integração

**Critérios de Aceitação:**
- Todos headers obrigatórios enviados
- Dados parseados corretamente
- Cache funcional
- Errors tratados adequadamente

**Estimativa:** 8 pontos  
**Prioridade:** CRÍTICA

---

#### US-2.3: Implementar Repository - PostgreSQL
**Como** sistema  
**Quero** persistir dados no PostgreSQL  
**Para que** tenha durabilidade e consistência

**Tarefas:**
- [ ] Criar SQLAlchemy models
  - [ ] `RestaurantModel`
  - [ ] `IntegrationModel`
  - [ ] `ConversationModel`
  - [ ] `MessageModel`
- [ ] Implementar `PostgresRestaurantRepository`
- [ ] Implementar `PostgresMessagingRepository`
- [ ] Implementar mappers (model ↔ entity)
- [ ] Testes de integração com DB real

**Critérios de Aceitação:**
- Domain entities <-> SQLAlchemy models
- Repository interfaces implementadas
- Transações funcionam corretamente
- Multi-tenancy respeitado em queries

**Estimativa:** 13 pontos  
**Prioridade:** CRÍTICA

---

#### US-2.4: Criar Seeds de Dados
**Como** desenvolvedor  
**Quero** popular banco com dados de teste  
**Para que** possa testar o sistema

**Tarefas:**
- [ ] Script de seed para restaurante teste
- [ ] Script para conversas e mensagens de exemplo
- [ ] Documentar como rodar seeds

**Estimativa:** 2 pontos  
**Prioridade:** MÉDIA

---

### Métricas de Sucesso Sprint 2

- ✅ OAuth2 token obtido e cached
- ✅ Dados institucionais obtidos da Tacto
- ✅ Cardápio obtido da Tacto
- ✅ Repositories funcionais
- ✅ Dados persistidos no PostgreSQL

---

## 📦 SPRINT 3: JOIN INTEGRATION (Semanas 5-6)

**Objetivo:** Integrar com Join Developer API para WhatsApp

### User Stories

#### US-3.1: Implementar Join Client
**Como** sistema  
**Quero** enviar e receber mensagens via Join  
**Para que** possa comunicar com clientes no WhatsApp

**Tarefas:**
- [ ] Criar `JoinClient` base class
- [ ] Implementar `send_message(phone, text)`
- [ ] Implementar `send_presence(phone, status)` (typing)
- [ ] Implementar parsing de webhooks
- [ ] Implementar validação de assinatura
- [ ] Testes com mock

**Estimativa:** 8 pontos  
**Prioridade:** CRÍTICA

---

#### US-3.2: Implementar Message Buffer Service
**Como** sistema  
**Quero** agrupar mensagens em buffer  
**Para que** não responda múltiplas vezes ao mesmo contexto

**Tarefas:**
- [ ] Criar `MessageBufferService` (domain service)
- [ ] Implementar adição ao buffer (Redis)
- [ ] Implementar timer com reset
- [ ] Implementar flush automático (após 5s)
- [ ] Implementar concatenação de mensagens
- [ ] Testes unitários e integração

**Critérios de Aceitação:**
- Buffer agrupa mensagens < 5s
- Timer reseta a cada nova mensagem
- Flush envia mensagem concatenada
- Buffer isolado por restaurant_id + phone

**Estimativa:** 8 pontos  
**Prioridade:** CRÍTICA

---

#### US-3.3: Implementar Webhook Handler
**Como** sistema  
**Quero** receber webhooks da Join  
**Para que** possa processar mensagens de clientes

**Tarefas:**
- [ ] Criar endpoint `POST /webhooks/join`
- [ ] Implementar validação de assinatura
- [ ] Implementar identificação de tenant (canal_master_id)
- [ ] Implementar validação (fromMe, source)
- [ ] Integrar com MessageBufferService
- [ ] Implementar resposta 202 Accepted
- [ ] Testes de integração

**Critérios de Aceitação:**
- Webhook valida assinatura
- Tenant identificado corretamente
- Mensagens fromMe=true ignoradas
- Source=phone desativa IA
- Resposta rápida (< 200ms)

**Estimativa:** 8 pontos  
**Prioridade:** CRÍTICA

---

#### US-3.4: Implementar Typing Simulation
**Como** sistema  
**Quero** simular digitação antes de responder  
**Para que** interação pareça humana

**Tarefas:**
- [ ] Implementar cálculo de delay (0.05s por char, max 4s)
- [ ] Integrar com send_message
- [ ] Testes

**Estimativa:** 2 pontos  
**Prioridade:** BAIXA

---

### Métricas de Sucesso Sprint 3

- ✅ Webhook recebe mensagens
- ✅ Buffer agrupa mensagens corretamente
- ✅ Mensagens enviadas via Join
- ✅ Typing simulation funcional

---

## 📦 SPRINT 4: AI CORE (Semanas 7-8)

**Objetivo:** Implementar núcleo de IA com Gemini

### User Stories

#### US-4.1: Implementar Gemini Client
**Como** sistema  
**Quero** gerar respostas usando Gemini  
**Para que** possa responder clientes automaticamente

**Tarefas:**
- [ ] Criar `GeminiClient` wrapper
- [ ] Implementar `generate(prompt, context, message)`
- [ ] Implementar error handling
- [ ] Implementar timeout (30s)
- [ ] Implementar retry policy
- [ ] Testes com mock

**Estimativa:** 5 pontos  
**Prioridade:** CRÍTICA

---

#### US-4.2: Implementar Response Orchestrator
**Como** sistema  
**Quero** orquestrar geração de respostas  
**Para que** fluxo completo seja coordenado

**Tarefas:**
- [ ] Criar `ResponseOrchestrator` (domain service)
- [ ] Implementar verificação de horário
- [ ] Implementar busca de contexto
- [ ] Implementar seleção de estratégia
- [ ] Implementar chamada à IA
- [ ] Testes unitários

**Critérios de Aceitação:**
- Se fechado: retorna apenas horário do dia
- Se aberto: chama estratégia correta
- Contexto montado adequadamente

**Estimativa:** 8 pontos  
**Prioridade:** CRÍTICA

---

#### US-4.3: Implementar BasicStrategy
**Como** sistema  
**Quero** estratégia BASIC de automação  
**Para que** possa responder com dados institucionais

**Tarefas:**
- [ ] Criar `BasicStrategy` class
- [ ] Implementar montagem de prompt
- [ ] Implementar restrições do nível BASIC
- [ ] Implementar validação de resposta
- [ ] Implementar filtro de conteúdo inadequado
- [ ] Testes unitários

**Critérios de Aceitação:**
- Prompt inclui dados institucionais
- Prompt inclui restrições (não falar de produtos)
- Resposta validada antes de enviar
- Palavrões bloqueados
- Menção a concorrentes bloqueada

**Estimativa:** 13 pontos  
**Prioridade:** CRÍTICA

---

#### US-4.4: Implementar Intent Detection
**Como** sistema  
**Quero** detectar intenção do usuário  
**Para que** possa ajustar resposta adequadamente

**Tarefas:**
- [ ] Criar `IntentDetectionService`
- [ ] Implementar detecção de intents básicos
  - GREETING
  - ASK_MENU
  - ASK_HOURS
  - ASK_ADDRESS
  - ASK_PAYMENT
- [ ] Usar patterns ou IA leve
- [ ] Testes

**Estimativa:** 5 pontos  
**Prioridade:** MÉDIA

---

### Métricas de Sucesso Sprint 4

- ✅ IA responde mensagens
- ✅ Estratégia BASIC funcional
- ✅ Horário de funcionamento respeitado
- ✅ Filtros de conteúdo ativos

---

## 📦 SPRINT 5: USE CASES & MEMORY (Semanas 9-10)

**Objetivo:** Completar use cases e sistema de memória

### User Stories

#### US-5.1: Implementar ProcessIncomingMessage Use Case
**Como** sistema  
**Quero** processar mensagem de ponta a ponta  
**Para que** fluxo completo funcione

**Tarefas:**
- [ ] Criar `ProcessIncomingMessage` use case
- [ ] Implementar validações
- [ ] Integrar com buffer
- [ ] Integrar com orchestrator
- [ ] Salvar mensagem no DB
- [ ] Salvar resposta no DB
- [ ] Enviar resposta via Join
- [ ] Testes end-to-end

**Estimativa:** 13 pontos  
**Prioridade:** CRÍTICA

---

#### US-5.2: Implementar CreateRestaurant Use Case
**Como** admin  
**Quero** criar restaurante via API  
**Para que** possa onboard novos clientes

**Tarefas:**
- [ ] Criar `CreateRestaurant` use case
- [ ] Implementar validações
- [ ] Persistir no DB
- [ ] Criar endpoint POST /restaurants
- [ ] Testes

**Estimativa:** 5 pontos  
**Prioridade:** ALTA

---

#### US-5.3: Implementar Memory Service
**Como** sistema  
**Quero** armazenar e recuperar memória de conversas  
**Para que** IA tenha contexto

**Tarefas:**
- [ ] Criar `MemoryService` (domain service)
- [ ] Implementar short-term memory (Redis)
  - Store últimas 10 mensagens
  - TTL 1h
- [ ] Implementar retrieve context
- [ ] Testes

**Estimativa:** 8 pontos  
**Prioridade:** ALTA

---

#### US-5.4: Implementar pgvector para Long-term Memory
**Como** sistema  
**Quero** busca semântica em histórico  
**Para que** IA tenha contexto profundo (futuro)

**Tarefas:**
- [ ] Criar `EmbeddingService`
- [ ] Gerar embeddings com Gemini
- [ ] Armazenar em pgvector
- [ ] Implementar similarity search
- [ ] Testes

**Estimativa:** 8 pontos  
**Prioridade:** MÉDIA (pode ir para backlog futuro)

---

### Métricas de Sucesso Sprint 5

- ✅ Fluxo end-to-end funcional
- ✅ Restaurantes podem ser criados via API
- ✅ Memória de curto prazo funcional
- ✅ (Opcional) pgvector funcional

---

## 📦 SPRINT 6: POLISH & DEPLOY (Semanas 11-12)

**Objetivo:** Preparar para produção

### User Stories

#### US-6.1: Implementar Logging Estruturado
**Como** desenvolvedor  
**Quero** logs estruturados  
**Para que** possa debugar facilmente

**Tarefas:**
- [ ] Configurar structlog
- [ ] Adicionar logs em pontos críticos
- [ ] Incluir restaurant_id em todos logs
- [ ] Configurar log rotation

**Estimativa:** 3 pontos

---

#### US-6.2: Implementar Health Checks
**Como** ops  
**Quero** monitorar saúde do sistema  
**Para que** possa detectar problemas

**Tarefas:**
- [ ] Criar GET /health (básico)
- [ ] Criar GET /health/detailed (com dependências)
- [ ] Verificar PostgreSQL
- [ ] Verificar Redis
- [ ] Verificar APIs externas

**Estimativa:** 3 pontos

---

#### US-6.3: Implementar Testes E2E
**Como** desenvolvedor  
**Quero** testes end-to-end  
**Para que** garanta que tudo funciona junto

**Tarefas:**
- [ ] Setup de teste E2E
- [ ] Teste: Receber mensagem → Responder
- [ ] Teste: Criar restaurante → Processar mensagem
- [ ] Teste: Buffer de mensagens
- [ ] Teste: Horário fechado

**Estimativa:** 8 pontos

---

#### US-6.4: Docker Production Setup
**Como** ops  
**Quero** deploy com Docker  
**Para que** ambiente seja reproduzível

**Tarefas:**
- [ ] Otimizar Dockerfile para produção
- [ ] Multi-stage build
- [ ] Docker Compose para produção
- [ ] Configurar volumes
- [ ] Configurar networks
- [ ] Documentar deploy

**Estimativa:** 5 pontos

---

#### US-6.5: Documentação Final
**Como** desenvolvedor  
**Quero** documentação completa  
**Para que** outros possam contribuir

**Tarefas:**
- [ ] README.md completo
- [ ] Guia de setup local
- [ ] Guia de deploy
- [ ] API documentation (Swagger)
- [ ] Troubleshooting guide

**Estimativa:** 5 pontos

---

### Métricas de Sucesso Sprint 6

- ✅ Logs estruturados funcionais
- ✅ Health checks implementados
- ✅ Testes E2E passando
- ✅ Docker production ready
- ✅ Documentação completa

---

## 🔮 BACKLOG FUTURO (Pós-MVP)

### Fase 2: Intermediate Features

**P1 - Alta Prioridade**
- [ ] Implementar IntermediateStrategy
- [ ] RAG completo de cardápio
- [ ] Melhorar detecção de intenção com IA
- [ ] Dashboard de analytics
- [ ] Métricas Prometheus

**P2 - Média Prioridade**
- [ ] Webhooks outgoing (notificar eventos)
- [ ] API de configuração avançada
- [ ] A/B testing de prompts
- [ ] Fine-tuning do modelo IA

**P3 - Baixa Prioridade**
- [ ] GraphQL API
- [ ] Multi-idioma
- [ ] Integração com CRMs

---

### Fase 3: Advanced Features

**P1 - Alta Prioridade**
- [ ] Implementar AdvancedStrategy
- [ ] Criação de pedidos via IA
- [ ] Validação de endereço
- [ ] Cálculo de frete
- [ ] Integração com pagamentos

**P2 - Média Prioridade**
- [ ] Notificações proativas
- [ ] Campanhas de marketing
- [ ] Programa de fidelidade
- [ ] Cupons e descontos

---

## ✅ CRITÉRIOS DE ACEITAÇÃO GLOBAIS

### Para Toda Feature

**Código:**
- [ ] Segue princípios DDD
- [ ] Segue SOLID
- [ ] Type hints completos
- [ ] Docstrings em funções públicas
- [ ] Sem código comentado
- [ ] Black + isort aplicados

**Testes:**
- [ ] Testes unitários (>80% cobertura)
- [ ] Testes de integração (quando aplicável)
- [ ] Testes passando no CI

**Documentação:**
- [ ] README atualizado (se necessário)
- [ ] docs/ atualizado (se necessário)
- [ ] Comentários em lógica complexa

**Review:**
- [ ] Code review aprovado
- [ ] Sem dívida técnica crítica

---

## 📊 VELOCITY & ESTIMATIVAS

### Estimativas

- **1 ponto** = ~2h de trabalho
- **2 pontos** = ~4h
- **3 pontos** = ~6h (meio dia)
- **5 pontos** = ~1 dia
- **8 pontos** = ~1.5 dias
- **13 pontos** = ~2-3 dias

### Velocity Esperada

- **Sprint de 2 semanas** = ~40 pontos (1 desenvolvedor full-time)
- Com 2 desenvolvedores = ~60-70 pontos

---

## 🎯 DEFINITION OF READY (DoR)

Uma história está pronta para desenvolvimento quando:

- [ ] User story clara (Como/Quero/Para que)
- [ ] Critérios de aceitação definidos
- [ ] Estimativa de pontos
- [ ] Dependências identificadas
- [ ] Dúvidas técnicas esclarecidas

---

## 📝 CHANGELOG

### [0.0.1] - 2026-03-27

#### Definido
- Roadmap macro (Fases 1-3)
- Backlog detalhado Sprints 1-6 (MVP)
- Estimativas e prioridades
- Critérios de aceitação

#### Próximos Passos
- Iniciar Sprint 1
- Refinar estimativas com time
- Ajustar velocidade após sprint 1

---

**Mantido por:** Product Owner & Engineering Team  
**Atualização:** A cada sprint  
**Próxima Revisão:** Final de cada sprint
