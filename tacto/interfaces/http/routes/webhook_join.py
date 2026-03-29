"""Join Webhook Handler.

Decision flow:
  1. Ignore non "messages.upsert" events
  2. Ignore group messages (@g.us)
  3. fromMe=true → check if AI-sent (ignore) or human operator (disable AI 12h)
  4. Extract text — ignore media
  5. Buffer messages (5s window) to combine rapid consecutive messages
  6. Route to ProcessIncomingMessageUseCase

Human Operator Detection (fromMe=true):
  - When fromMe=true, the message was sent FROM the instance's connected phone
  - remoteJid is always the RECIPIENT (customer's phone)
  - To distinguish AI vs human:
    1. Check Redis SentMessageTracker (message_id or phone)
    2. If found → AI echo → ignore
    3. If NOT found → human operator → disable AI 12h
"""

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Request, status
from pydantic import BaseModel

from tacto.application.dto.message_dto import IncomingMessageDTO
from tacto.application.services.message_buffer_service import MessageBufferService
from tacto.infrastructure.messaging.instance_phone_cache import InstancePhoneCache


logger = structlog.get_logger()
router = APIRouter()


class WebhookResponse(BaseModel):
    """Standardized response returned to Join (always HTTP 200)."""

    success: bool
    message: str = "OK"


# ── Webhook Entry Point ────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Join Developer Webhook",
    description="Receives WhatsApp events from Join Developer API",
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
        log = logger.bind(event=event, instance=instance)

        # ── Step 1: Only process messages.upsert ─────────────────────────
        if event != "messages.upsert":
            log.debug("webhook_event_ignored", reason="not_messages_upsert")
            return WebhookResponse(success=True, message="Event ignored")

        data: dict[str, Any] = body.get("data", {})
        key: dict[str, Any] = data.get("key", {})
        from_me: bool = key.get("fromMe", False)
        message_id: str = key.get("id", "")
        remote_jid: str = key.get("remoteJid", "") or key.get("remoteJidAlt", "")
        
        # ── Step 2: Ignore group messages ─────────────────────────────────
        if "@g.us" in remote_jid:
            log.debug("webhook_message_ignored", reason="group_message")
            return WebhookResponse(success=True, message="Group ignored")

        push_name: str = data.get("pushName", "")
        timestamp: int = data.get("messageTimestamp", 0)

        # ── Step 3: fromMe=true → check if AI-sent or human operator ─────────
        if from_me:
            # Log FULL payload for debugging — capture ALL fields
            message_content = data.get("message", {})
            message_type = data.get("messageType", "unknown")
            
            # Log complete payload to identify instance phone number field
            log.warning(
                "FROM_ME_FULL_PAYLOAD_DEBUG",
                full_body=body,
                full_data=data,
                full_key=key,
                message_type=message_type,
                message_id=message_id,
                remote_jid=remote_jid,
                participant=key.get("participant"),
                data_participant=data.get("participant"),
                owner=data.get("owner"),
                source=data.get("source"),
                broadcast=data.get("broadcast"),
                status=data.get("status"),
                all_data_keys=list(data.keys()),
                all_key_keys=list(key.keys()),
                all_body_keys=list(body.keys()),
            )
            
            # Pass remoteJid as phone_for_check.
            # The AI tracker stores the customer's phone with a very short TTL.
            # This catches the echo webhook Join fires ~1s after the AI sends a message.
            phone_for_check = remote_jid.split("@")[0] if "@" in remote_jid else None
            is_ai_message = await _check_if_ai_sent_message(request, instance, message_id, phone_for_check)
            
            if is_ai_message:
                return WebhookResponse(success=True, message="AI message ignored")
            
            # Extract customer phone from remoteJid (the conversation partner)
            customer_phone = _extract_sender_number(key, data)
            if customer_phone:
                dto = IncomingMessageDTO(
                    instance_key=instance,
                    from_phone=customer_phone,
                    body="__human_operator__",
                    from_me=True,
                    source="phone",
                    timestamp=timestamp,
                    message_id=message_id,
                    push_name=push_name,
                )
                background_tasks.add_task(_process_message_background, dto)
                log.info("human_operator_detected", customer_phone=customer_phone)
            return WebhookResponse(success=True, message="Operator message — AI paused")

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
        redis_client = getattr(request.app.state, "redis", None)
        
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
        process_callback=lambda dto: _process_message_background(dto, redis_client),
    )


async def _process_message_background(dto: IncomingMessageDTO, redis_client=None) -> None:
    """Process message in background."""
    from tacto.interfaces.http.dependencies import create_and_execute_process_message

    try:
        await create_and_execute_process_message(dto, redis_client)
    except Exception as exc:
        logger.error("background_task_error", error=str(exc), phone=dto.clean_phone)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _check_if_ai_sent_message(
    request: Request,
    instance_key: str,
    message_id: str,
    phone: str | None = None,
) -> bool:
    """Check if message was sent by AI (by message_id or phone number)."""
    from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker
    
    redis_client = getattr(request.app.state, "redis", None)
    if not redis_client or not redis_client.is_connected:
        return True  # Assume AI to avoid false positives
    
    tracker = SentMessageTracker(redis_client)
    return await tracker.is_ai_sent_message(instance_key, message_id, phone)


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
