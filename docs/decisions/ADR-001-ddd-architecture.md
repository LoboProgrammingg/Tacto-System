# ADR-001: Domain-Driven Design Architecture

**Status:** Accepted  
**Date:** 2026-03-27  
**Deciders:** Engineering Team, Tech Lead  
**Context:** Arquitetura base do sistema TactoFlow

---

## Context

O TactoFlow é um sistema backend complexo que precisa:
- Gerenciar múltiplos restaurantes (multi-tenant)
- Integrar com múltiplas APIs externas (Tacto, Join, Gemini)
- Processar mensagens em tempo real
- Escalar para centenas de restaurantes
- Manter regras de negócio complexas e bem definidas
- Permitir evolução sem quebrar o sistema

**Problema:** Como estruturar o código de forma que seja:
1. Testável
2. Manutenível
3. Escalável
4. Alinhado com o negócio
5. Resistente a mudanças de infraestrutura

---

## Decision

Adotamos **Domain-Driven Design (DDD)** seguindo rigorosamente os princípios de Eric Evans, combinado com **Clean Architecture** de Robert C. Martin.

### Estrutura de Camadas

```
tacto/
├── domain/          # Core business logic (ZERO dependências externas)
├── application/     # Use cases e orquestração
├── infrastructure/  # Detalhes técnicos (DB, APIs, etc.)
└── interfaces/      # HTTP, CLI, Workers
```

### Bounded Contexts

Dividimos o sistema em 5 contextos delimitados:
1. **Restaurant Context** - Gestão de restaurantes
2. **Messaging Context** - Conversas e mensagens
3. **Assistant Context** - IA e estratégias de resposta
4. **Memory Context** - Memória multi-nível
5. **Order Context** - Pedidos (futuro)

### Tactical Patterns

- **Entities:** Objetos com identidade própria (Restaurant, Conversation, Message)
- **Value Objects:** Imutáveis sem identidade (IntegrationType, OpeningHours)
- **Aggregates:** Clusters transacionais (Restaurant é root de Integration)
- **Repository Pattern:** Interface no domínio, implementação na infraestrutura
- **Domain Services:** Lógica que não pertence a entidades
- **Strategy Pattern:** Diferentes níveis de automação

---

## Consequences

### Positive

✅ **Separação de Concerns:** Domínio não depende de frameworks  
✅ **Testabilidade:** Domain layer 100% testável sem mocks pesados  
✅ **Manutenibilidade:** Regras de negócio centralizadas  
✅ **Linguagem Ubíqua:** Código reflete termos do negócio  
✅ **Flexibilidade:** Trocar DB/frameworks sem afetar domínio  
✅ **Onboarding:** Novos devs entendem negócio pelo código  

### Negative

❌ **Curva de Aprendizado:** DDD requer estudo e disciplina  
❌ **Overhead Inicial:** Mais código boilerplate no início  
❌ **Complexidade Acidental:** Se mal aplicado, pode complicar coisas simples  
❌ **Requer Disciplina:** Fácil violar camadas se não houver code review  

### Mitigations

- **Treinamento:** Todos devs devem ler "Domain-Driven Design" (cap. 1-7)
- **Code Reviews:** Garantir que camadas não sejam violadas
- **Linters:** Configurar import-linter para detectar violações
- **Testes:** Verificar que domain layer não importa infrastructure

---

## Alternatives Considered

### 1. MVC Tradicional

**Pros:** Simples, rápido para começar  
**Cons:** Não escala bem, lógica de negócio vaza para controllers  
**Rejected:** Sistema muito complexo para MVC

### 2. Service Layer sem DDD

**Pros:** Mais simples que DDD, ainda organizado  
**Cons:** Sem linguagem ubíqua, sem agregados, sem invariantes claras  
**Rejected:** Regras de negócio complexas demais

### 3. CQRS + Event Sourcing

**Pros:** Altamente escalável, auditoria completa  
**Cons:** Complexidade extrema, over-engineering para MVP  
**Rejected:** Complexidade desnecessária nesta fase

---

## Implementation Notes

### Regras de Ouro

1. **Domain NUNCA importa Infrastructure**
   ```python
   # ❌ PROIBIDO em domain/
   from infrastructure.postgres import Session
   
   # ✅ CORRETO em domain/
   from abc import ABC, abstractmethod
   ```

2. **Repository é Interface no Domain**
   ```python
   # domain/restaurant/repository.py
   class RestaurantRepository(ABC):
       @abstractmethod
       async def save(self, restaurant: Restaurant) -> Result[Restaurant, Exception]:
           pass
   ```

3. **Aggregates Garantem Invariantes**
   ```python
   @dataclass
   class Restaurant:
       def __post_init__(self):
           self._validate_invariants()  # SEMPRE validar
   ```

4. **Use Cases Orquestram**
   ```python
   # application/use_cases/create_restaurant.py
   class CreateRestaurant:
       def __init__(self, repo: RestaurantRepository):
           self.repo = repo
       
       async def execute(self, dto: CreateRestaurantDTO) -> Result:
           # Orquestra lógica de negócio
   ```

### Verificação de Conformidade

```bash
# Verificar que domain não importa infrastructure
import-linter --config=.import-linter.ini

# Verificar cobertura de testes do domain
pytest --cov=tacto/domain --cov-report=term-missing
```

---

## Related Decisions

- ADR-002: Message Buffer Strategy
- ADR-003: Multi-level Memory Architecture

---

## References

- Evans, Eric. "Domain-Driven Design: Tackling Complexity in the Heart of Software" (2003)
- Martin, Robert C. "Clean Architecture" (2017)
- Vernon, Vaughn. "Implementing Domain-Driven Design" (2013)
- [DDD Community](https://www.domainlanguage.com/)

---

**Last Updated:** 2026-03-27  
**Review Date:** 2026-06-27 (após 3 meses de implementação)
