"""Join Webhook Handler.

Decision flow:
  1. Validate HMAC signature (if configured)
  2. Ignore non "messages.upsert" events
  3. Ignore group messages (@g.us)
  4. fromMe=True → check if AI-sent (ignore) or human operator (disable AI 12h)
  5. fromMe=False + sender=instance_phone → WA Business automated msg → IGNORE
  6. Extract text — ignore media
  7. Buffer messages (5s window) to combine rapid consecutive messages
  8. Route to ProcessIncomingMessageUseCase

Human Operator Detection:
  - fromMe=True + NOT in SentMessageTracker → human operator → disable AI 12h
  - fromMe=True + in SentMessageTracker → AI echo → ignore
  
WhatsApp Business Automated Messages (greeting, away msg):
  - fromMe=False + sender=instance_phone → WA Business automated msg → IGNORE
  - These are sent BY the WA server on behalf of the business, NOT by a human.
  - Human operators ALWAYS produce fromMe=True regardless of device (web/mobile/desktop).

Security:
  - HMAC-SHA256 signature validation via X-Hub-Signature-256 header
  - Set JOIN_WEBHOOK_SECRET in .env to enable
"""

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from tacto.application.dto.message_dto import IncomingMessageDTO
from tacto.application.services.message_buffer_service import MessageBufferService
from tacto.infrastructure.messaging.instance_phone_cache import InstancePhoneCache
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

        # ── Step 3: fromMe=true OR sender is instance → check if AI-sent or human operator ─────────
        sender: str = body.get("sender", "")
        clean_sender: str = sender.split("@")[0] if "@" in sender else sender

        is_operator_message = from_me

        if clean_sender:
            redis_client_step3 = getattr(request.app.state, "redis", None)
            if redis_client_step3 and redis_client_step3.is_connected:
                phone_cache = InstancePhoneCache(redis_client_step3)
                if from_me:
                    # Cache the instance's own phone number for future detection.
                    await phone_cache.set_instance_phone(instance, clean_sender)
                else:
                    # from_me=False but sender matches the instance's own phone.
                    # Per Evolution/Join API: messages from the connected account always
                    # arrive as from_me=True. from_me=False + sender=instance_phone is an
                    # anomaly that represents WA Business automated messages (greeting/away)
                    # sent by the WA platform on behalf of the business — NOT a human operator.
                    # Human operators always produce from_me=True (handled in Step 3 above).
                    # → Ignore silently, never disable AI.
                    if await phone_cache.is_instance_phone(instance, clean_sender):
                        log.info(
                            "automated_business_message_ignored",
                            sender=clean_sender,
                            reason="from_me=False + instance_phone = WA Business automated msg",
                        )
                        return WebhookResponse(success=True, message="Automated business message ignored")

        if is_operator_message:
            source: str = data.get("source", "")

            # Extract echo text to compare with AI-sent content hash
            echo_message: dict[str, Any] = data.get("message", {})
            echo_message_type: str = data.get("messageType", "")
            echo_text: str | None = _extract_text(echo_message, echo_message_type) or None

            customer_phone = remote_jid.split("@")[0] if "@" in remote_jid else None
            is_ai_message = await _check_if_ai_sent_message(
                request, instance, message_id, customer_phone, echo_text
            )

            if is_ai_message:
                log.debug("ai_echo_ignored", message_id=message_id, source=source)
                return WebhookResponse(success=True, message="AI echo ignored")

            # NOT an AI echo → human operator sent this manually (fromMe=True path)
            if customer_phone:
                redis_client = getattr(request.app.state, "redis", None)
                tacto_client = getattr(request.app.state, "tacto_client", None)

                # Flush any pending message buffer for this customer so the sleeping
                # buffer coroutine finds an empty list and exits without calling the LLM.
                # This prevents the race condition where the AI responds AFTER the operator.
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
                log.info(
                    "human_operator_detected",
                    customer_phone=customer_phone,
                    sender=clean_sender,
                    source=source,
                )
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

        # ── Step 5b: Detect operator via phone cache (fromMe=False edge case) ─
        # Join API sometimes sends fromMe=False for messages sent from the physical
        # device (not via API). We compare the sender's phone against the cached
        # instance phone to catch this case.
        redis_client = getattr(request.app.state, "redis", None)
        tacto_client = getattr(request.app.state, "tacto_client", None)

        # Step 5b is now DISABLED.
        # The logic was: from_me=False + sender=instance_phone → detect operator.
        # But this catches WhatsApp Business automated messages (greeting, away msg)
        # which are sent BY the WA server on behalf of the business with from_me=False.
        #
        # The CORRECT detection is:
        #   - from_me=True → Human operator (any device: web, mobile, desktop)
        #   - from_me=False + sender=instance_phone → WA Business automated msg → IGNORE
        #
        # Human operators ALWAYS produce from_me=True regardless of device.
        # This check is handled in Step 3 (from_me=True path).

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

async def _check_if_ai_sent_message(
    request: Request,
    instance_key: str,
    message_id: str,
    phone: str | None = None,
    echo_text: str | None = None,
) -> bool:
    """Check if from_me=True message was sent by AI (not by a human operator)."""
    from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker

    redis_client = getattr(request.app.state, "redis", None)
    if not redis_client or not redis_client.is_connected:
        return True  # Redis down: assume AI echo to avoid false disable

    tracker = SentMessageTracker(redis_client)
    return await tracker.is_ai_sent_message(instance_key, message_id, phone, echo_text)


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
