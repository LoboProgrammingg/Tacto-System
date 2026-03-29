# ADR-004: Detecção de Operador Humano via `fromMe`

**Data:** 2026-03-29
**Status:** Accepted
**Contexto:** Webhook da Join API

---

## Problema

Quando o webhook da Join API chega com `fromMe=true`, precisamos distinguir entre:
1. **Echo da IA** — mensagem que a IA acabou de enviar (deve ser ignorada)
2. **Operador humano** — alguém enviou manualmente pelo WhatsApp Web/App (deve desativar IA)

Ambos os cenários produzem payloads **estruturalmente idênticos**.

---

## Estrutura do Payload (Real da Join API)

```json
{
  "event": "messages.upsert",
  "instance": "wp-empresa-7",
  "sender": "554187273618@s.whatsapp.net",
  "data": {
    "key": {
      "remoteJid": "556592540370@s.whatsapp.net",
      "fromMe": true,
      "id": "3EB0C6017DD9C2B3CEDC0A"
    },
    "source": "web",
    "message": {
      "conversation": "Texto da mensagem"
    }
  }
}
```

### Campos Críticos

| Campo | Descrição |
|-------|-----------|
| `fromMe` | `true` = mensagem enviada PELO número conectado na instância |
| `sender` | Número do RESTAURANTE conectado (quem enviou) |
| `remoteJid` | Número do CLIENTE (destinatário quando `fromMe=true`) |
| `source` | Origem: `"web"` = WhatsApp Web, `"android"`/`"ios"` = celular |
| `id` | ID único da mensagem gerado pelo WhatsApp |

---

## Decisão: Tracking via Redis

### Fluxo de Detecção

```
Webhook chega com fromMe=true
    │
    ▼
SentMessageTracker.is_ai_sent_message(instance, message_id, phone)
    │
    ├── Encontrado no Redis → É echo da IA → IGNORAR
    │
    └── NÃO encontrado → É operador humano → DESATIVAR IA 12h
```

### Implementação

1. **Quando IA envia mensagem** (`JoinClient.send_message`):
   ```python
   await tracker.track_sent_message(
       instance_key="restaurante_teste",
       phone="5565992540370",
       message_id="AI_MSG_123",  # pode ser None se Join não retornar
   )
   ```
   - Salva `tacto:sent_msg_id:{instance}:{message_id}` com TTL 300s
   - Salva `tacto:sent_msg_num:{instance}:{phone}` com TTL 15s

2. **Quando webhook chega com `fromMe=true`**:
   ```python
   is_ai = await tracker.is_ai_sent_message(instance, message_id, phone)
   if is_ai:
       return "AI message ignored"
   else:
       # Human operator detected!
       conversation.disable_ai(reason="human_intervention", duration_hours=12)
   ```

---

## Configurações (settings.py)

```python
echo_tracker_ttl: int = 15        # segundos (TTL curto para phone)
message_id_tracker_ttl: int = 300  # segundos (TTL longo para message_id)
ai_disable_hours: int = 12         # horas de pausa da IA
```

### Por que dois TTLs?

- **message_id (300s)**: Join API às vezes retorna o ID; se tiver, é mais confiável
- **phone (15s)**: Fallback para quando Join não retorna ID; janela curta para evitar falsos positivos

---

## Matriz de Decisão

| fromMe | Redis Tracker | Ação |
|--------|---------------|------|
| `false` | N/A | Processar como mensagem do cliente |
| `true` | Encontrado | Ignorar (echo da IA) |
| `true` | Não encontrado | DESATIVAR IA 12h |

---

## Testes

15 testes criados em `tests/unit/infrastructure/messaging/test_webhook_join.py`:

- `TestWebhookJoinBasicFiltering` — filtra grupos, mídia, eventos
- `TestWebhookJoinCustomerMessage` — processa mensagem do cliente
- `TestWebhookJoinFromMeLogic` — distingue AI vs operador
- `TestSentMessageTracker` — tracking no Redis
- `TestFromMeDecisionMatrix` — documentação da matriz

---

## Consequências

### Positivas
- Detecção confiável de operador humano
- AI pausa automaticamente quando humano intervém
- Zero falsos positivos quando TTLs estão corretos

### Negativas
- Se TTL expirar antes do echo chegar, falso positivo (humano detectado)
- Solução: aumentar `echo_tracker_ttl` se necessário (atualmente 15s)

---

## Alternativas Consideradas

1. **Comparar número do remetente com número da instância**
   - Rejeitado: Join não fornece o número do remetente no payload `fromMe=true`
   - `remoteJid` é sempre o destinatário (cliente)

2. **Webhook separado para mensagens enviadas**
   - Rejeitado: Join usa o mesmo evento `messages.upsert`

3. **Marcar mensagens da IA com prefixo especial**
   - Rejeitado: Visível para o cliente, UX ruim
