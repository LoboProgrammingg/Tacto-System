"""
JoinMessageClassifier.

Substitui a lógica frágil de `is_operator_message = from_me` por um classificador
robusto com 4 categorias de saída e fallback em múltiplas camadas.

Categorias:
  - "user"           → mensagem real do cliente → processar normalmente
  - "ai_echo"        → echo da mensagem que a IA enviou → ignorar
  - "human_operator" → operador humano assumiu → desativar IA 12h
  - "system"         → mensagem automática WA Business → ignorar

Fail-safe: qualquer from_me=True não identificado como AI = "human_operator".
Nunca mais ignorar operador humano acidentalmente.
"""

from typing import Any

import structlog

from tacto.infrastructure.messaging.instance_phone_cache import InstancePhoneCache
from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker


logger = structlog.get_logger()

MessageOrigin = str  # "user" | "ai_echo" | "human_operator" | "system"


class JoinMessageClassifier:
    """
    Classifica a origem de mensagens da Join API.

    Uso:
        classifier = JoinMessageClassifier(redis_client, db_session)
        origin = await classifier.classify(body, data, key)

        if origin == "ai_echo":        return ignore
        if origin == "human_operator": return disable_ai
        if origin == "system":         return ignore
        if origin == "user":           return process
    """

    def __init__(self, redis_client=None, db_session=None) -> None:
        self._redis = redis_client
        self._db = db_session
        self._tracker = SentMessageTracker(redis_client, db_session)
        self._phone_cache = InstancePhoneCache(redis_client)

    async def classify(
        self,
        body: dict[str, Any],
        data: dict[str, Any],
        key: dict[str, Any],
    ) -> MessageOrigin:
        """
        Classifica a origem da mensagem.

        Args:
            body: payload raiz do webhook
            data: body["data"]
            key: data["key"]

        Returns:
            "user" | "ai_echo" | "human_operator" | "system"
        """
        from_me: bool = key.get("fromMe", False)
        message_id: str = key.get("id", "")
        remote_jid: str = key.get("remoteJid", "") or key.get("remoteJidAlt", "")
        instance: str = body.get("instance", "")
        timestamp: int = data.get("messageTimestamp", 0)

        # Extrai sender de múltiplos campos (sender pode vir vazio)
        sender = _extract_sender(body, data, key)

        # ── from_me=False: é mensagem de cliente ou mensagem automática do WA ──
        if not from_me:
            is_system = await self._is_system_message(instance, sender, remote_jid)
            if is_system:
                return "system"
            return "user"

        # ── from_me=True: pode ser echo da IA ou operador humano ──

        # Cacheia o telefone da instância toda vez que vemos from_me=True
        if sender:
            await self._phone_cache.set_instance_phone(instance, sender)

        customer_phone = _extract_customer_phone(remote_jid, key, data)

        echo_message: dict[str, Any] = data.get("message", {})
        echo_message_type: str = data.get("messageType", "")
        echo_text = _extract_text(echo_message, echo_message_type)

        is_ai = await self._tracker.is_ai_sent_message(
            instance_key=instance,
            message_id=message_id,
            phone=customer_phone,
            echo_text=echo_text,
            timestamp=timestamp,
        )

        if is_ai:
            logger.debug("classified_ai_echo", instance=instance, message_id=message_id)
            return "ai_echo"

        # Nada confirmou que é da IA → FAIL-SAFE: é operador humano
        logger.info(
            "classified_human_operator",
            instance=instance,
            sender=sender,
            customer_phone=customer_phone,
        )
        return "human_operator"

    async def _is_system_message(
        self,
        instance: str,
        sender: str,
        remote_jid: str,
    ) -> bool:
        """
        Detecta mensagens automáticas do WA Business.
        from_me=False mas sender = telefone da instância → é mensagem automática.
        Funciona mesmo se sender vier vazio (usa remote_jid como fallback).
        """
        if not sender:
            return False

        is_instance = await self._phone_cache.is_instance_phone(instance, sender)
        if is_instance:
            return True

        # Se remote_jid também está vazio (sem destinatário), provavelmente é status update
        if not remote_jid:
            # Sem remote_jid não sabemos para quem é — ignorar como sistema
            logger.debug("no_remote_jid_treating_as_system", instance=instance, sender=sender)
            return True

        return False


# ── Helpers de módulo ──────────────────────────────────────────────────────────

def _extract_sender(body: dict, data: dict, key: dict) -> str:
    """
    Extrai o telefone do sender de múltiplos campos.
    A Join às vezes omite 'sender' — usa fallbacks.
    """
    candidates = [
        body.get("sender", ""),
        body.get("owner", ""),
        data.get("owner", ""),
        key.get("participant", ""),
        data.get("participant", ""),
    ]
    for c in candidates:
        if c and ("@" in c or c.isdigit()):
            return c.split("@")[0] if "@" in c else c
    return ""


def _extract_customer_phone(remote_jid: str, key: dict, data: dict) -> str:
    """Extrai o telefone do cliente (destinatário) a partir do remoteJid."""
    for jid in [
        remote_jid,
        key.get("remoteJid", ""),
        key.get("remoteJidAlt", ""),
        key.get("participant", ""),
        data.get("participant", ""),
    ]:
        if jid and "@s.whatsapp.net" in jid:
            return jid.split("@")[0]
    return ""


def _extract_text(message: dict, message_type: str) -> str | None:
    """Extrai texto do payload para comparação de hash."""
    if message_type == "conversation":
        return message.get("conversation") or None
    if message_type == "extendedTextMessage":
        ext = message.get("extendedTextMessage", {})
        return ext.get("text") if isinstance(ext, dict) else None
    return message.get("conversation") or message.get("text") or message.get("body") or None
