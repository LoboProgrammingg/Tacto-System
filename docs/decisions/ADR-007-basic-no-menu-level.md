# ADR-007: Nível de automação BASIC — SEM CARDÁPIO

**Data:** 2026-10-09  
**Status:** ✅ Implemented  
**Autores:** Engineering Team  
**Referências:** ADR-006 (Level 2), BR-AL001 / BR-AL004 (vault `02 - Regras de Negocio`)

## Contexto

A Predileta (`wp-empresa-1105`, automação 1 — BASIC) reclamou que a IA respondia sobre itens do cardápio ("a menor pizza é a Pizza P, que faz parte do Combo…"). Não era falha: desde o commit `71fff54` (2026-04-13) o Level 1 injeta até 10 itens do cardápio (pgvector, sem corte por similaridade) em toda mensagem e o prompt manda informar sobre os itens. Não existia configuração para desligar isso, e os 47 restaurantes de produção estavam em `automation_type=1`.

## Decisão

Criar o nível `AutomationType.BASIC_NO_MENU = 4`, em vez de alterar o BASIC ou adicionar um flag em `agent_config`.

- Mesmo `Level1Agent`. Para o nível 4: a busca semântica no cardápio é pulada (`AutomationType.can_discuss_menu_items`) e o prompt usa a variante `_NO_MENU_SECTIONS`, sem instruções nem exemplos de itens.
- Qualquer pergunta de produto (item, sabor, tamanho, ingrediente, preço, sugestão) vira uma frase curta + link do cardápio. Institucional, horário, endereço e handoff humano não mudam.
- Valor 4 e não 0: zero é falsy em Python. Não há comparação de ordem entre níveis em uso.
- Sem migration: `restaurants.automation_type` é `integer` sem CHECK.

## Por que não as alternativas

| Alternativa | Motivo da rejeição |
|---|---|
| Corrigir o BASIC para seguir a BR-AL001 | Mudaria o comportamento dos 47 restaurantes de uma vez |
| Flag `menu_rag_enabled` em `agent_config` | Dois campos acoplados; o admin lê `agent_config` por um PATCH vazio |
| Apagar `menu_embeddings` do restaurante | Volta ao clicar em "Re-sync cardápio"; o prompt continuaria com exemplos de itens |
| Só "Prompt default" customizado | Instrução customizada brigaria com o prompt base e com os itens injetados |

## Consequências

- O caminho do nível 1 não muda: a saída de `build_system_prompt` foi comparada byte a byte antes/depois (288 combinações de persona).
- **Ordem de deploy:** código antes de gravar o valor 4 no banco. Com código antigo, `AutomationType(4)` lança `ValueError` e o restaurante para de responder. Rollback é o inverso: voltar o restaurante para 1 antes de reverter o código.
- O admin (`/opt/tacto-admin`, deploy por scp) precisa ir antes da virada: a versão antiga quebra o form de edição com o valor 4.
- `BASIC` continua divergindo da BR-AL001 (fala de itens). A regra escrita passa a ser atendida pelo nível 4.
