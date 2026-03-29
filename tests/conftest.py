"""
Pytest configuration and fixtures.

Provides common fixtures for testing the Tacto System.
"""

import asyncio
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from tacto.interfaces.http.routes.webhook_join import router as webhook_router


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Create a mock Redis client."""
    client = MagicMock()
    client.is_connected = True
    client.set = AsyncMock(return_value=MagicMock(is_success=lambda: True))
    client.get = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=None))
    client.exists = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=False))
    client.delete = AsyncMock(return_value=MagicMock(is_success=lambda: True))
    client.rpush = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=1))
    client.lrange = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=[]))
    client.expire = AsyncMock(return_value=MagicMock(is_success=lambda: True))
    client.setnx = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=True))
    return client


@pytest.fixture
def mock_redis_with_ai_tracking(mock_redis_client: MagicMock) -> MagicMock:
    """Redis client that simulates AI message tracking."""
    # Simulates that a message was tracked by AI
    mock_redis_client.exists = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=True))
    return mock_redis_client


@pytest.fixture
def mock_redis_no_ai_tracking(mock_redis_client: MagicMock) -> MagicMock:
    """Redis client that simulates NO AI message tracking (human operator)."""
    mock_redis_client.exists = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=False))
    return mock_redis_client


@pytest.fixture
def app(mock_redis_client: MagicMock) -> FastAPI:
    """Create FastAPI app with webhook router."""
    app = FastAPI()
    app.include_router(webhook_router, prefix="/webhook/join")
    app.state.redis = mock_redis_client
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# ──────────────────────────────────────────────────────────────────────────────
# Join API Payload Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def join_payload_customer_message() -> dict[str, Any]:
    """
    Payload when CUSTOMER sends a message to the restaurant.
    
    fromMe: false — message is FROM the customer
    remoteJid: customer's phone number
    """
    return {
        "event": "messages.upsert",
        "instance": "restaurante_teste",
        "data": {
            "key": {
                "remoteJid": "5565992540370@s.whatsapp.net",
                "fromMe": False,
                "id": "3EB0A1B2C3D4E5F6"
            },
            "pushName": "Cliente Teste",
            "message": {
                "conversation": "Oi, quero fazer um pedido"
            },
            "messageType": "conversation",
            "messageTimestamp": 1711728000
        }
    }


@pytest.fixture
def join_payload_ai_response() -> dict[str, Any]:
    """
    Payload when AI sends a message (echo from Join).
    
    fromMe: true — message is FROM the restaurant's number
    remoteJid: customer's phone number (the recipient)
    
    This is the ECHO webhook that Join fires after AI sends via API.
    """
    return {
        "event": "messages.upsert",
        "instance": "restaurante_teste",
        "data": {
            "key": {
                "remoteJid": "5565992540370@s.whatsapp.net",
                "fromMe": True,
                "id": "3EB0A1B2C3D4E5F7"
            },
            "pushName": "",
            "message": {
                "conversation": "Olá! Bem-vindo ao restaurante. Como posso ajudar?"
            },
            "messageType": "conversation",
            "messageTimestamp": 1711728005
        }
    }


@pytest.fixture
def join_payload_human_operator() -> dict[str, Any]:
    """
    Payload when HUMAN OPERATOR sends a message from WhatsApp Web/App.
    
    fromMe: true — message is FROM the restaurant's number
    remoteJid: customer's phone number (the recipient)
    
    This looks IDENTICAL to AI response, but:
    - message_id is NOT in Redis tracker
    - phone is NOT in Redis tracker (TTL expired or never set)
    
    THIS is when we need to DISABLE AI for 12 hours.
    """
    return {
        "event": "messages.upsert",
        "instance": "restaurante_teste",
        "data": {
            "key": {
                "remoteJid": "5565992540370@s.whatsapp.net",
                "fromMe": True,
                "id": "WHATSAPP_MANUAL_MSG_123"
            },
            "pushName": "",
            "message": {
                "conversation": "Oi, aqui é o atendente do restaurante!"
            },
            "messageType": "conversation",
            "messageTimestamp": 1711728100
        }
    }


@pytest.fixture
def join_payload_group_message() -> dict[str, Any]:
    """Payload for group message (should be ignored)."""
    return {
        "event": "messages.upsert",
        "instance": "restaurante_teste",
        "data": {
            "key": {
                "remoteJid": "120363123456789@g.us",
                "fromMe": False,
                "id": "3EB0GROUP123"
            },
            "pushName": "Membro do Grupo",
            "message": {
                "conversation": "Mensagem no grupo"
            },
            "messageType": "conversation",
            "messageTimestamp": 1711728000
        }
    }


@pytest.fixture
def join_payload_media_message() -> dict[str, Any]:
    """Payload for media message (should be ignored)."""
    return {
        "event": "messages.upsert",
        "instance": "restaurante_teste",
        "data": {
            "key": {
                "remoteJid": "5565992540370@s.whatsapp.net",
                "fromMe": False,
                "id": "3EB0MEDIA123"
            },
            "pushName": "Cliente",
            "message": {
                "imageMessage": {
                    "url": "https://example.com/image.jpg",
                    "mimetype": "image/jpeg"
                }
            },
            "messageType": "imageMessage",
            "messageTimestamp": 1711728000
        }
    }


@pytest.fixture
def join_payload_connection_event() -> dict[str, Any]:
    """Non-message event (should be ignored)."""
    return {
        "event": "connection.update",
        "instance": "restaurante_teste",
        "data": {
            "state": "open"
        }
    }
