"""Join Webhook Handler.

Decision flow:
  1. Validate HMAC signature (if configured)
  2. Ignore non "messages.upsert" events
  3. Ignore group messages (@g.us)
  4. fromMe=true → check if AI-sent (ignore) or human operator (disable AI 12h)
  5. Extract text — ignore media
  6. Buffer messages (5s window) to combine rapid consecutive messages
  7. Route to ProcessIncomingMessageUseCase

Human Operator Detection (two paths):
  Path A — fromMe=True:
    - remoteJid = RECIPIENT (customer's phone)
    - Check SentMessageTracker (message_id or content hash)
    - If found → AI echo → ignore
    - If NOT found → human operator → disable AI 12h
    - Also: cache sender phone → InstancePhoneCache (for Path B)

  Path B — fromMe=False but sender IS the instance phone:
    - Join API sometimes sends fromMe=False for messages from the physical device
    - Compare sender phone against InstancePhoneCache
    - If match → human operator → disable AI 12h

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
                    # Cache the instance's own phone number logic.
                    await phone_cache.set_instance_phone(instance, clean_sender)
                else:
                    # Check if the message is coming from the known instance phone even if fromMe is false
                    if await phone_cache.is_instance_phone(instance, clean_sender):
                        is_operator_message = True

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

            # NOT confirmed as AI echo — but Join API doesn't return message_id on send,
            # so hash is the only tracker. Only treat as human operator if source="app"
            # (physical device) AND there's actual text content (not a status/system message).
            # Unidentifiable fromMe messages (source="api", empty text, etc.) are silently ignored
            # to avoid false positives that disable AI incorrectly.
            is_likely_human = (
                source == "app"  # sent from physical device, not via API
                and echo_text is not None
                and len(echo_text.strip()) > 0
                and remote_jid  # has a recipient (not a status update)
            )

            if is_likely_human and customer_phone:
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
                redis_client = getattr(request.app.state, "redis", None)
                tacto_client = getattr(request.app.state, "tacto_client", None)
                background_tasks.add_task(_process_message_background, dto, redis_client, tacto_client)
                log.info(
                    "human_operator_detected",
                    customer_phone=customer_phone,
                    sender=clean_sender,
                    source=source,
                )
                return WebhookResponse(success=True, message="Operator message — AI paused 12h")

            log.debug("from_me_unidentified_ignored", source=source, has_text=echo_text is not None)
            return WebhookResponse(success=True, message="fromMe ignored — not confirmed human")

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

        if clean_sender and redis_client and redis_client.is_connected:
            phone_cache = InstancePhoneCache(redis_client)
            if await phone_cache.is_instance_phone(instance, clean_sender):
                # The 'remote_jid' contains the customer's phone if the operator is talking to them.
                customer_phone = remote_jid.split("@")[0] if "@" in remote_jid else None
                if customer_phone:
                    dto = IncomingMessageDTO(
                        instance_key=instance,
                        from_phone=customer_phone,
                        body="__human_operator__",
                        from_me=False,
                        source="human_operator",
                        timestamp=timestamp,
                        message_id=message_id,
                        push_name=push_name,
                    )
                    background_tasks.add_task(_process_message_background, dto, redis_client, tacto_client)
                    log.info(
                        "human_operator_detected_via_sender",
                        sender=clean_sender,
                        instance=instance,
                        customer_phone=customer_phone,
                    )
                    return WebhookResponse(success=True, message="Operator message (sender match) — AI paused 12h")

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
