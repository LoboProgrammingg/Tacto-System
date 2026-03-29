"""
Join Developer API Client — Infrastructure Implementation.

Handles WhatsApp messaging through Join Developer API (api-prd.joindeveloper.com.br).

Authentication: `tokenCliente` header + `instancia` header per request.

Retry policy (Phase 5 — Reliability):
- Exponential backoff on 502/503/504 and transport errors
- Max 3 attempts, delays: 1s → 2s → 4s
- 4xx errors are NOT retried (definitive client failures)
"""

import asyncio
import random
import re
from typing import Optional

import httpx
import structlog

from tacto.config import JoinAPISettings, get_settings
from tacto.domain.ai_assistance.ports.messaging_client import MessagingClient, SendMessageResult
from tacto.domain.shared.result import Err, Failure, Ok, Success
from tacto.infrastructure.circuit_breaker import CircuitBreaker, CircuitOpenError
from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker


logger = structlog.get_logger()

_RETRYABLE_STATUS_CODES = {502, 503, 504}


def convert_markdown_to_whatsapp(text: str) -> str:
    """
    Convert standard markdown formatting to WhatsApp formatting.
    
    WhatsApp uses different syntax:
    - Bold: *text* (same as markdown)
    - Italic: _text_ (markdown uses *text* or _text_)
    - Strikethrough: ~text~ (markdown uses ~~text~~)
    - Monospace: ```text``` (same as markdown)
    
    This function converts:
    - **bold** → *bold*
    - ~~strikethrough~~ → ~strikethrough~
    - Removes unsupported markdown (headers, links, etc.)
    """
    result = text
    
    # Convert **bold** to *bold* (WhatsApp style)
    result = re.sub(r'\*\*(.+?)\*\*', r'*\1*', result)
    
    # Convert ~~strikethrough~~ to ~strikethrough~
    result = re.sub(r'~~(.+?)~~', r'~\1~', result)
    
    # Convert [text](url) links to just "text: url"
    result = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1: \2', result)
    
    # Remove markdown headers (# ## ### etc) but keep the text
    result = re.sub(r'^#{1,6}\s*', '', result, flags=re.MULTILINE)
    
    # Remove horizontal rules (---, ***, ___)
    result = re.sub(r'^[\-\*_]{3,}\s*$', '', result, flags=re.MULTILINE)
    
    # Clean up multiple consecutive newlines (max 2)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()


class JoinClient(MessagingClient):
    """
    Join Developer API client for WhatsApp messaging.

    Handles:
    - Sending text messages with humanized typing delay
    - Replying to messages (quoted)
    - Instance connection status
    - Markdown to WhatsApp format conversion

    Authentication: `tokenCliente` header (from JOIN_TOKEN_CLIENTE env var).
    The `instancia` name is passed per-call, not at construction time.
    """

    def __init__(
        self,
        settings: Optional[JoinAPISettings] = None,
        message_tracker: Optional[SentMessageTracker] = None,
    ) -> None:
        self._settings = settings or get_settings().join
        self._tracker = message_tracker
        self._circuit_breaker = CircuitBreaker(
            name="join_api",
            failure_threshold=5,
            recovery_timeout=30.0,
        )

    def _calc_typing_delay_ms(self, text: str) -> int:
        """Calculate a humanized typing delay (ms) based on message length."""
        base_ms = (len(text) / self._settings.typing_chars_per_sec) * 1000
        variance_ms = base_ms * self._settings.typing_variance * (random.random() * 2 - 1)
        delay_ms = int(base_ms + variance_ms)
        return max(self._settings.typing_min_ms, min(self._settings.typing_max_ms, delay_ms))

    def _base_headers(self, instance_key: str) -> dict[str, str]:
        """Build per-request headers with token and instance."""
        return {
            "Content-Type": "application/json",
            "tokenCliente": self._settings.token_cliente,
            "instancia": instance_key,
        }

    async def _with_retry(
        self, request_fn, operation: str
    ) -> httpx.Response:
        """Execute an HTTP request with exponential backoff retry and circuit breaker."""
        # Check circuit breaker before attempting
        if self._circuit_breaker.is_open():
            logger.warning(
                "join_circuit_open",
                operation=operation,
            )
            raise CircuitOpenError(self._circuit_breaker.name)

        last_exc: Exception | None = None
        max_attempts = self._settings.retry_max_attempts
        base_delay = self._settings.retry_base_delay

        for attempt in range(max_attempts):
            try:
                response = await request_fn()

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "join_retry_on_status",
                            operation=operation,
                            attempt=attempt + 1,
                            status_code=response.status_code,
                            next_delay_s=delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(
                            "join_retry_exhausted",
                            operation=operation,
                            status_code=response.status_code,
                        )

                # Success — record and return
                self._circuit_breaker.record_success()
                return response

            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "join_retry_on_transport",
                        operation=operation,
                        attempt=attempt + 1,
                        error=str(exc),
                        next_delay_s=delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "join_transport_error_exhausted",
                        operation=operation,
                        error=str(exc),
                    )

        # All retries exhausted — record failure in circuit breaker
        self._circuit_breaker.record_failure()
        raise last_exc  # type: ignore[misc]

    async def connect(self) -> Success[bool] | Failure[Exception]:
        """No-op: client is lazy-initialized per request. kept for API compat."""
        return Ok(True)

    async def disconnect(self) -> Success[bool] | Failure[Exception]:
        """No-op: no persistent connection. Kept for API compatibility."""
        return Ok(True)

    async def send_message(
        self,
        instance_key: str,
        phone: str,
        message: str,
        simulate_typing: bool = True,
    ) -> Success[SendMessageResult] | Failure[Exception]:
        """
        Send a text message via WhatsApp.

        POST /mensagens/enviartexto
        Auth: tokenCliente (header) + instancia (header)
        """
        try:
            # Convert markdown to WhatsApp format
            formatted_message = convert_markdown_to_whatsapp(message)
            
            delay_ms = self._calc_typing_delay_ms(formatted_message) if simulate_typing else 1000

            clean_phone = (
                phone.replace("@c.us", "").replace("@s.whatsapp.net", "")
            )

            payload = {
                "number": clean_phone,
                "options": {
                    "delay": delay_ms,
                    "presence": "composing",
                },
                "textMessage": {"text": formatted_message},
            }

            headers = self._base_headers(instance_key)

            async def _do_request() -> httpx.Response:
                async with httpx.AsyncClient(
                    base_url=self._settings.base_url,
                    timeout=self._settings.http_timeout,
                ) as client:
                    return await client.post(
                        "/mensagens/enviartexto",
                        json=payload,
                        headers=headers,
                    )

            response = await self._with_retry(_do_request, "send_message")
            response.raise_for_status()

            data = response.json()
            
            # Log full response to understand the format
            logger.info(
                "join_api_response_debug",
                response_data=data,
                response_keys=list(data.keys()) if isinstance(data, dict) else type(data).__name__,
            )
            
            message_id = self._extract_message_id(data)

            logger.info(
                "join_message_sent",
                instance_key=instance_key,
                phone=clean_phone,
                message_id=message_id,
            )

            # Track the message so we can distinguish AI vs human messages
            # Uses TWO strategies: by message_id (if available) AND by phone number
            if self._tracker:
                await self._tracker.track_sent_message(
                    instance_key=instance_key,
                    phone=clean_phone,
                    message_id=message_id,  # May be None, that's OK
                )

            return Ok(SendMessageResult(message_id=message_id, sent=True))

        except httpx.HTTPStatusError as exc:
            logger.error(
                "join_http_error_send",
                status=exc.response.status_code,
                body=exc.response.text,
            )
            return Err(exc)
        except Exception as exc:
            logger.error("join_error_send", error=str(exc))
            return Err(exc)

    async def send_reply(
        self,
        instance_key: str,
        phone: str,
        message: str,
        quoted_message_id: str,
        quoted_remote_jid: str,
        quoted_text: str,
        simulate_typing: bool = True,
    ) -> Success[str] | Failure[Exception]:
        """
        Reply to a specific message via WhatsApp.

        POST /mensagens/respondermensagem
        """
        try:
            # Convert markdown to WhatsApp format
            formatted_message = convert_markdown_to_whatsapp(message)
            
            delay_ms = self._calc_typing_delay_ms(formatted_message) if simulate_typing else 1000
            clean_phone = phone.replace("@c.us", "").replace("@s.whatsapp.net", "")

            payload = {
                "number": clean_phone,
                "options": {
                    "delay": delay_ms,
                    "presence": "composing",
                    "quoted": {
                        "key": {
                            "remoteJid": quoted_remote_jid,
                            "fromMe": False,
                            "id": quoted_message_id,
                            "participant": "",
                        },
                        "message": {"conversation": quoted_text},
                    },
                },
                "textMessage": {"text": formatted_message},
            }

            headers = self._base_headers(instance_key)

            async def _do_request() -> httpx.Response:
                async with httpx.AsyncClient(
                    base_url=self._settings.base_url,
                    timeout=self._settings.http_timeout,
                ) as client:
                    return await client.post(
                        "/mensagens/respondermensagem",
                        json=payload,
                        headers=headers,
                    )

            response = await self._with_retry(_do_request, "send_reply")
            response.raise_for_status()

            data = response.json()
            message_id = self._extract_message_id(data)

            logger.info(
                "join_reply_sent",
                instance_key=instance_key,
                phone=clean_phone,
                quoted_message_id=quoted_message_id,
                sent_message_id=message_id,
            )

            return Ok(message_id or "")

        except httpx.HTTPStatusError as exc:
            logger.error(
                "join_http_error_reply",
                status=exc.response.status_code,
                body=exc.response.text,
            )
            return Err(exc)
        except Exception as exc:
            logger.error("join_error_reply", error=str(exc))
            return Err(exc)

    @staticmethod
    def _extract_message_id(data: dict | None) -> str | None:
        """
        Extract message ID from Join API response.

        Join API returns the message ID in different structures depending
        on the endpoint version. We try the most common ones.
        """
        if not data or not isinstance(data, dict):
            return None

        # Format 1: {key: {id: "..."}}
        if "key" in data and isinstance(data["key"], dict):
            msg_id = data["key"].get("id")
            if msg_id:
                return msg_id

        # Format 2: {id: "..."}
        if "id" in data:
            return data.get("id")

        # Format 3: {messageId: "..."}
        if "messageId" in data:
            return data.get("messageId")

        # Format 4: {data: {key: {id: "..."}}}
        inner = data.get("data")
        if isinstance(inner, dict):
            key_obj = inner.get("key")
            if isinstance(key_obj, dict):
                return key_obj.get("id")
            if "id" in inner:
                return inner["id"]

        return None
