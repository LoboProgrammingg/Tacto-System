"""
Join Webhook Handler.

Receives incoming WhatsApp messages from Join Developer API.
"""

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel

from tacto.application.dto.message_dto import IncomingMessageDTO
from tacto.application.use_cases.process_incoming_message import (
    ProcessIncomingMessageUseCase,
)
from tacto.interfaces.http.dependencies import get_process_message_use_case


logger = structlog.get_logger()
router = APIRouter()


class JoinWebhookPayload(BaseModel):
    """Payload received from Join webhook."""

    event: str = "messages.upsert"
    instance: str
    data: dict[str, Any]


class WebhookResponse(BaseModel):
    """Response to webhook request."""

    success: bool
    message: str = "OK"


@router.post(
    "/join",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Join Developer Webhook",
    description="Receives incoming WhatsApp messages from Join Developer API",
)
async def join_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    """
    Handle incoming webhook from Join Developer.

    The webhook payload contains message data that needs to be processed.
    Processing is done in background to return quickly to Join.
    """
    try:
        body = await request.json()
        log = logger.bind(event=body.get("event"), instance=body.get("instance"))

        event = body.get("event", "")

        if event != "messages.upsert":
            log.debug("Ignoring non-message event")
            return WebhookResponse(success=True, message="Event ignored")

        data = body.get("data", {})
        message_data = data.get("message", data)

        instance_key = body.get("instance", "")
        from_phone = message_data.get("from", "")
        message_body = message_data.get("body", "")
        from_me = message_data.get("fromMe", False)
        source = message_data.get("source", "app")
        timestamp = message_data.get("timestamp", 0)
        message_id = message_data.get("key", {}).get("id", "")
        push_name = message_data.get("pushName", "")

        if not from_phone or not message_body:
            log.warning("Missing required fields in webhook payload")
            return WebhookResponse(success=True, message="Missing fields")

        dto = IncomingMessageDTO(
            instance_key=instance_key,
            from_phone=from_phone,
            body=message_body,
            from_me=from_me,
            source=source,
            timestamp=timestamp,
            message_id=message_id,
            push_name=push_name,
            media_url=message_data.get("mediaUrl"),
            media_type=message_data.get("mediaType"),
        )

        background_tasks.add_task(process_message_background, dto)

        log.info("Webhook received, processing in background")
        return WebhookResponse(success=True, message="Processing")

    except Exception as e:
        logger.error("Webhook processing error", error=str(e))
        return WebhookResponse(success=False, message=str(e))


async def process_message_background(dto: IncomingMessageDTO) -> None:
    """
    Process message in background task.

    This allows the webhook to return quickly while processing continues.
    """
    from tacto.interfaces.http.dependencies import create_process_message_use_case

    try:
        use_case = await create_process_message_use_case()
        result = await use_case.execute(dto)

        if result.is_failure():
            logger.error(
                "Background message processing failed",
                error=str(result.error),
                phone=dto.clean_phone,
            )
        else:
            logger.info(
                "Background message processing completed",
                phone=dto.clean_phone,
                response_sent=result.value.response_sent,
            )

    except Exception as e:
        logger.error(
            "Background task error",
            error=str(e),
            phone=dto.clean_phone,
        )
