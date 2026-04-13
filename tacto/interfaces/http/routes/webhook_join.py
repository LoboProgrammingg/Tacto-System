"""Join Webhook Handler.

Decision flow:
  1. Validate HMAC signature (if configured)
  2. Ignore non "messages.upsert" events
  3. Ignore group messages (@g.us)
  4. Classify message origin via JoinMessageClassifier:
     - "ai_echo"        → ignore (echo of AI-sent message)
     - "human_operator" → disable AI 12h
     - "ignored"        → ignore (no remote_jid, can't identify customer)
     - "user"           → process normally
  5. Extract text — ignore media
  6. Buffer messages (5s window) to combine rapid consecutive messages
  7. Route to ProcessIncomingMessageUseCase

Classification uses 5-layer detection (Redis ID → Redis hash → DB ID → DB hash → time window).
Fail-safe: any from_me=True not confirmed as AI = human_operator.

Security:
  - HMAC-SHA256 signature validation via X-Hub-Signature-256 header
  - Set JOIN_WEBHOOK_SECRET in .env to enable
"""

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from tacto.application.dto.message_dto import IncomingMessageDTO
from tacto.application.services.message_buffer_service import MessageBufferService
from tacto.infrastructure.database.connection import get_async_session
from tacto.infrastructure.messaging.join_message_classifier import JoinMessageClassifier
from tacto.interfaces.http.middlewares.webhook_security import validate_webhook_signature
from tacto.interfaces.http.schemas.webhook import WebhookResponse


logger = structlog.get_logger()
router = APIRouter()


# ── Webhook Entry Point ────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Join Developer Webhook",
    description="Receives WhatsApp events from Join Developer API",
    dependencies=[Depends(validate_webhook_signature)],
)
async def join_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    """
    Handle incoming webhook from Join Developer.

    Always returns 200 immediately so Join does not retry.
    Message processing happens in a background task.
    """
    try:
        body: dict[str, Any] = await request.json()

        event: str = body.get("event", "")
        instance: str = body.get("instance", "")
        log = logger.bind(webhook_event=event, instance=instance)

        data: dict[str, Any] = body.get("data", {})
        key: dict[str, Any] = data.get("key", {})
        from_me: bool = key.get("fromMe", False)
        message_id: str = key.get("id", "")

        # ── Step 1: Ignore irrelevant events but allow send.message from operator ──
        if event != "messages.upsert":
            if event == "send.message" and from_me:
                pass  # Human operator response from another client
            else:
                log.debug("webhook_event_ignored", reason="not_messages_upsert")
                return WebhookResponse(success=True, message="Event ignored")
        remote_jid: str = key.get("remoteJid", "") or key.get("remoteJidAlt", "")
        
        # ── Step 2: Ignore group messages ─────────────────────────────────
        if "@g.us" in remote_jid:
            log.debug("webhook_message_ignored", reason="group_message")
            return WebhookResponse(success=True, message="Group ignored")

        push_name: str = data.get("pushName", "")
        timestamp: int = data.get("messageTimestamp", 0)

        # ── DEBUG: log raw fields to diagnose operator detection ──────────
        log.debug(
            "webhook_raw_fields",
            from_me=from_me,
            remote_jid=remote_jid,
            sender=body.get("sender", ""),
            source=data.get("source", ""),
            push_name=push_name,
            message_id=message_id,
            participant=data.get("participant", "") or key.get("participant", ""),
        )

        # ── Step 3: Classify message origin via JoinMessageClassifier ────────
        redis_client = getattr(request.app.state, "redis", None)
        tacto_client = getattr(request.app.state, "tacto_client", None)

        db_session = None
        try:
            async with get_async_session() as session:
                db_session = session
                classifier = JoinMessageClassifier(redis_client, db_session)
                origin = await classifier.classify(body, data, key)
        except Exception as cls_exc:
            log.warning("classifier_db_error_falling_back", error=str(cls_exc))
            # Fallback: classify without DB (Redis-only)
            classifier = JoinMessageClassifier(redis_client, None)
            origin = await classifier.classify(body, data, key)

        if origin == "ai_echo":
            log.debug("ai_echo_ignored", message_id=message_id)
            return WebhookResponse(success=True, message="AI echo ignored")

        if origin == "ignored":
            log.debug("message_ignored_no_remote_jid", sender=body.get("sender", ""))
            return WebhookResponse(success=True, message="Message ignored")

        if origin == "human_operator":
            customer_phone = _extract_sender_number(key, data)
            if customer_phone:
                # Flush any pending message buffer for this customer so the sleeping
                # buffer coroutine finds an empty list and exits without calling the LLM.
                if redis_client and redis_client.is_connected:
                    buffer_key = f"tacto:msg_buffer:{instance}:{customer_phone}"
                    await redis_client.delete(buffer_key)
                    log.debug("buffer_flushed_for_operator", customer_phone=customer_phone)

                dto = IncomingMessageDTO(
                    instance_key=instance,
                    from_phone=customer_phone,
                    body="__human_operator__",
                    from_me=True,
                    source="human_operator",
                    timestamp=timestamp,
                    message_id=message_id,
                    push_name=push_name,
                )
                background_tasks.add_task(_process_message_background, dto, redis_client, tacto_client)
                log.info("human_operator_detected", customer_phone=customer_phone)
            return WebhookResponse(success=True, message="Operator message — AI paused 12h")

        # ── Step 4: Extract text content ──────────────────────────────────
        message: dict[str, Any] = data.get("message", {})
        message_type: str = data.get("messageType", "")

        if _is_media_message(message, message_type):
            log.debug("webhook_message_ignored", reason="media_message")
            return WebhookResponse(success=True, message="Media ignored")

        text = _extract_text(message, message_type)
        if not text or not text.strip():
            log.debug("webhook_message_ignored", reason="no_text")
            return WebhookResponse(success=True, message="No text")

        # ── Step 5: Extract sender phone ──────────────────────────────────
        phone = _extract_sender_number(key, data)
        if not phone:
            log.warning("webhook_sender_extraction_failed", remote_jid=remote_jid)
            return WebhookResponse(success=True, message="Cannot extract phone")

        # ── Step 6: Buffer message and schedule processing ───────────────
        
        # Add message to buffer and schedule delayed processing
        background_tasks.add_task(
            _buffer_and_process,
            instance_key=instance,
            phone=phone,
            text=text.strip(),
            timestamp=timestamp,
            message_id=message_id,
            push_name=push_name,
            redis_client=redis_client,
            tacto_client=tacto_client,
        )

        log.info("webhook_accepted", phone=phone, message_preview=text[:60])
        return WebhookResponse(success=True, message="Buffering")

    except Exception as exc:
        logger.error("webhook_error", error=str(exc))
        # Always 200 — never let Join see a 5xx so it stops retrying
        return WebhookResponse(success=False, message=str(exc))


# ── Message Buffer ────────────────────────────────────────────────────────────

async def _buffer_and_process(
    instance_key: str,
    phone: str,
    text: str,
    timestamp: int,
    message_id: str,
    push_name: str,
    redis_client,
    tacto_client=None,
) -> None:
    """Delegate buffering logic to MessageBufferService (application layer)."""
    buffer_service = MessageBufferService(redis_client)
    await buffer_service.buffer_and_process(
        instance_key=instance_key,
        phone=phone,
        text=text,
        timestamp=timestamp,
        message_id=message_id,
        push_name=push_name,
        process_callback=lambda dto: _process_message_background(dto, redis_client, tacto_client),
    )


async def _process_message_background(dto: IncomingMessageDTO, redis_client=None, tacto_client=None) -> None:
    """Process message in background."""
    from tacto.interfaces.http.dependencies import create_and_execute_process_message

    try:
        await create_and_execute_process_message(dto, redis_client, tacto_client)
    except Exception as exc:
        logger.error("background_task_error", error=str(exc), phone=dto.clean_phone)


# ── Helpers ────────────────────────────────────────────────────────────────────

_MEDIA_TYPES = {
    "imageMessage", "videoMessage", "audioMessage", "documentMessage",
    "stickerMessage", "locationMessage", "contactMessage", "reactionMessage",
}


def _is_media_message(message: dict[str, Any], message_type: str) -> bool:
    """Return True if message contains media (not text)."""
    if message_type in _MEDIA_TYPES:
        return True
    return any(mt in message and message.get(mt) for mt in _MEDIA_TYPES)


def _extract_text(message: dict[str, Any], message_type: str) -> str:
    """Extract plain text from Join message payload."""
    if message_type == "conversation":
        return message.get("conversation", "")
    if message_type == "extendedTextMessage":
        ext = message.get("extendedTextMessage", {})
        return ext.get("text", "") if isinstance(ext, dict) else ""
    return message.get("conversation", "") or message.get("text", "") or message.get("body", "")


def _extract_sender_number(key: dict[str, Any], data: dict[str, Any]) -> str | None:
    """Extract sender phone number from JID (e.g., '5548...@s.whatsapp.net' → '5548...')."""
    for jid in [
        key.get("remoteJid", ""),
        key.get("remoteJidAlt", ""),
        key.get("participant", ""),
        data.get("participant", ""),
    ]:
        if jid and "@s.whatsapp.net" in jid:
            return jid.split("@")[0]
    return None
