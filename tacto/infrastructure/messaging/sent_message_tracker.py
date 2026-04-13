"""
Sent Message Tracker — v2.

Estratégia de detecção em 3 camadas:
1. Redis (rápido, TTL curto) — melhor caso
2. Banco de dados (persistente) — fallback quando Redis cai ou race condition
3. Janela de tempo (anti-race-condition) — fallback de último recurso

Isso elimina os dois problemas críticos do tracker original:
  - Redis down → antes: False (tratava como operador). Agora: verifica banco.
  - Race condition de timing → antes: mensagem vira operador. Agora: janela de tempo.
"""

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import structlog

from tacto.config.settings import get_settings
from tacto.infrastructure.redis.redis_client import RedisClient


logger = structlog.get_logger()

_PREFIX_ID   = "tacto:sent_msg_id:"
_PREFIX_HASH = "tacto:sent_msg_hash:"

# Janela de tempo para detectar race condition de timing (webhook chega antes do Redis salvar)
_ECHO_WINDOW_SECONDS = 5


class SentMessageTracker:
    """
    Rastreia mensagens enviadas pela IA com 3 camadas de fallback.

    IMPORTANTE: db_session é opcional. Quando fornecido, habilita fallback no banco.
    """

    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        db_session=None,  # AsyncSession do SQLAlchemy
    ) -> None:
        self._redis = redis_client
        self._db = db_session
        _settings = get_settings()
        self._ttl_message_id = _settings.redis.message_id_tracker_ttl
        self._ttl_hash = self._ttl_message_id

    async def track_sent_message(
        self,
        instance_key: str,
        phone: str,
        message_id: Optional[str] = None,
        message_text: Optional[str] = None,
    ) -> None:
        """
        Registra mensagem como enviada pela IA.

        ORDEM CORRETA: chamar ANTES de send_message() para evitar race condition.
        Salva em Redis (rápido) E no banco (persistente).
        """
        clean_phone = _clean_phone(phone)
        content_hash = _hash_text(message_text) if message_text else ""

        # 1. Salva no banco PRIMEIRO (fonte da verdade)
        if self._db and message_text:
            await self._save_to_db(instance_key, clean_phone, message_id, content_hash, message_text)

        # 2. Salva no Redis (cache rápido)
        if self._redis and self._redis.is_connected:
            if message_id:
                await self._redis.set(
                    f"{_PREFIX_ID}{instance_key}:{message_id}",
                    "1",
                    ttl=self._ttl_message_id,
                )
            if clean_phone and content_hash:
                await self._redis.set(
                    f"{_PREFIX_HASH}{instance_key}:{clean_phone}:{content_hash}",
                    "1",
                    ttl=self._ttl_hash,
                )

    async def update_message_id(
        self,
        instance_key: str,
        phone: str,
        old_temp_hash: str,
        real_message_id: str,
    ) -> None:
        """
        Atualiza o message_id real no banco e Redis após o send retornar o ID.
        Necessário porque o send pode demorar e o ID real só vem depois.
        """
        clean_phone = _clean_phone(phone)

        if self._db:
            try:
                from sqlalchemy import text
                await self._db.execute(
                    text("""
                        UPDATE ai_sent_messages
                        SET message_id = :message_id
                        WHERE instance_key = :instance AND phone = :phone
                          AND content_hash = :hash
                          AND sent_at > NOW() - INTERVAL '5 minutes'
                    """),
                    {"message_id": real_message_id, "instance": instance_key, "phone": clean_phone, "hash": old_temp_hash},
                )
                await self._db.commit()
            except Exception as exc:
                logger.warning("ai_sent_messages_update_id_failed", error=str(exc))

        if self._redis and self._redis.is_connected:
            await self._redis.set(
                f"{_PREFIX_ID}{instance_key}:{real_message_id}",
                "1",
                ttl=self._ttl_message_id,
            )

    async def is_ai_sent_message(
        self,
        instance_key: str,
        message_id: str,
        phone: Optional[str] = None,
        echo_text: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Verifica se uma mensagem from_me=True foi enviada pela IA.

        Ordem de verificação (mais confiável → menos confiável):
        1. Redis por message_id     — mais rápido, pode falhar
        2. Redis por hash de texto  — fallback de timing rápido
        3. Banco por message_id     — Redis down ou expirado
        4. Banco por hash de texto  — Redis down + timing
        5. Janela de tempo          — anti-race-condition final

        Se NADA confirmar que é da IA → retorna False (é operador humano)
        """
        clean_phone = _clean_phone(phone) if phone else None
        content_hash = _hash_text(echo_text) if echo_text else None

        # CAMADA 1: Redis por message_id
        if self._redis and self._redis.is_connected and message_id:
            result = await self._redis.exists(f"{_PREFIX_ID}{instance_key}:{message_id}")
            if result.is_success() and result.value:
                logger.debug("ai_echo_detected_redis_id", message_id=message_id)
                return True

        # CAMADA 2: Redis por hash
        if self._redis and self._redis.is_connected and clean_phone and content_hash:
            result = await self._redis.exists(
                f"{_PREFIX_HASH}{instance_key}:{clean_phone}:{content_hash}"
            )
            if result.is_success() and result.value:
                logger.debug("ai_echo_detected_redis_hash", phone=clean_phone)
                return True

        # CAMADA 3 + 4: Banco (quando Redis falhou ou TTL expirou)
        if self._db:
            found = await self._check_db(instance_key, message_id, clean_phone, content_hash)
            if found:
                logger.debug("ai_echo_detected_db", message_id=message_id)
                return True

        # CAMADA 5: Janela de tempo (anti-race-condition)
        # Se o webhook chegou dentro de X segundos da última mensagem da IA,
        # provavelmente é o echo antes do Redis ter salvo.
        if timestamp and clean_phone and self._db:
            within = await self._within_echo_window(instance_key, clean_phone, timestamp)
            if within:
                logger.debug("ai_echo_detected_time_window", phone=clean_phone, timestamp=timestamp)
                return True

        # Nada confirmou que é da IA → tratar como operador humano
        return False

    # ── Helpers privados ──────────────────────────────────────────────────────

    async def _save_to_db(
        self,
        instance_key: str,
        phone: str,
        message_id: Optional[str],
        content_hash: str,
        message_text: str,
    ) -> None:
        """Persiste no banco como outbox."""
        try:
            from sqlalchemy import text
            await self._db.execute(
                text("""
                    INSERT INTO ai_sent_messages
                        (id, instance_key, phone, message_id, content_hash, message_text, sent_at)
                    VALUES
                        (:id, :instance, :phone, :message_id, :hash, :text, NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "instance": instance_key,
                    "phone": phone,
                    "message_id": message_id,
                    "hash": content_hash,
                    "text": message_text,
                },
            )
            await self._db.commit()
        except Exception as exc:
            logger.warning("ai_sent_messages_db_save_failed", error=str(exc))

    async def _check_db(
        self,
        instance_key: str,
        message_id: Optional[str],
        phone: Optional[str],
        content_hash: Optional[str],
    ) -> bool:
        """Verifica no banco (camadas 3 e 4)."""
        try:
            from sqlalchemy import text

            # Por message_id
            if message_id:
                result = await self._db.execute(
                    text("""
                        SELECT 1 FROM ai_sent_messages
                        WHERE instance_key = :instance AND message_id = :message_id
                          AND sent_at > NOW() - INTERVAL '10 minutes'
                        LIMIT 1
                    """),
                    {"instance": instance_key, "message_id": message_id},
                )
                if result.fetchone():
                    return True

            # Por hash
            if phone and content_hash:
                result = await self._db.execute(
                    text("""
                        SELECT 1 FROM ai_sent_messages
                        WHERE instance_key = :instance AND phone = :phone
                          AND content_hash = :hash
                          AND sent_at > NOW() - INTERVAL '5 minutes'
                        LIMIT 1
                    """),
                    {"instance": instance_key, "phone": phone, "hash": content_hash},
                )
                if result.fetchone():
                    return True

        except Exception as exc:
            logger.warning("ai_sent_messages_db_check_failed", error=str(exc))

        return False

    async def _within_echo_window(
        self,
        instance_key: str,
        phone: str,
        webhook_timestamp: int,
    ) -> bool:
        """
        Verifica se o webhook chegou dentro da janela de echo (anti-race-condition).

        Caso: IA envia → webhook chega ANTES do Redis salvar → falsamente vira operador.
        Solução: se existe registro no banco de mensagem enviada há menos de N segundos, é echo.
        """
        try:
            from sqlalchemy import text
            # Normaliza timestamp (Join às vezes envia em ms)
            ts = webhook_timestamp
            if ts > 10_000_000_000:
                ts = ts // 1000
            webhook_dt = datetime.fromtimestamp(ts, tz=timezone.utc)

            result = await self._db.execute(
                text("""
                    SELECT 1 FROM ai_sent_messages
                    WHERE instance_key = :instance AND phone = :phone
                      AND sent_at BETWEEN :start AND :end
                    LIMIT 1
                """),
                {
                    "instance": instance_key,
                    "phone": phone,
                    "start": webhook_dt - timedelta(seconds=_ECHO_WINDOW_SECONDS),
                    "end": webhook_dt + timedelta(seconds=_ECHO_WINDOW_SECONDS),
                },
            )
            return result.fetchone() is not None
        except Exception as exc:
            logger.warning("echo_window_check_failed", error=str(exc))
            return False


# ── Helpers de módulo ──────────────────────────────────────────────────────────

def _clean_phone(phone: str) -> str:
    return phone.replace("@s.whatsapp.net", "").replace("@c.us", "")


def _hash_text(text: str) -> str:
    """MD5 do texto normalizado (sem espaços extras, sem BOM)."""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()
