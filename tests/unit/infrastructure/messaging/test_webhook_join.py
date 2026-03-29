"""
Tests for Join Webhook Handler.

These tests validate the behavior of the webhook when receiving different
types of messages from the Join API.

Key scenarios:
1. Customer sends message → process normally
2. AI sends message (echo) → ignore (detected by Redis tracker)
3. Human operator sends message → DISABLE AI for 12 hours
4. Group message → ignore
5. Media message → ignore
6. Non-message events → ignore
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestWebhookJoinBasicFiltering:
    """Test basic message filtering (groups, media, events)."""

    def test_ignores_non_message_events(
        self,
        client: TestClient,
        join_payload_connection_event: dict,
    ):
        """Connection events should be ignored."""
        response = client.post("/webhook/join/", json=join_payload_connection_event)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "ignored" in response.json()["message"].lower()

    def test_ignores_group_messages(
        self,
        client: TestClient,
        join_payload_group_message: dict,
    ):
        """Group messages (@g.us) should be ignored."""
        response = client.post("/webhook/join/", json=join_payload_group_message)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "group" in response.json()["message"].lower()

    def test_ignores_media_messages(
        self,
        client: TestClient,
        join_payload_media_message: dict,
    ):
        """Media messages should be ignored."""
        response = client.post("/webhook/join/", json=join_payload_media_message)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "media" in response.json()["message"].lower()


class TestWebhookJoinCustomerMessage:
    """Test handling of customer messages."""

    @pytest.mark.asyncio
    async def test_accepts_customer_text_message(
        self,
        app,
        join_payload_customer_message: dict,
    ):
        """Customer text messages should be accepted and buffered."""
        from httpx import AsyncClient
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/webhook/join/", json=join_payload_customer_message)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        # Message should be buffered for processing
        assert "buffer" in response.json()["message"].lower()

    def test_extracts_phone_from_remote_jid(
        self,
        join_payload_customer_message: dict,
    ):
        """Phone number should be correctly extracted from remoteJid."""
        from tacto.interfaces.http.routes.webhook_join import _extract_sender_number
        
        key = join_payload_customer_message["data"]["key"]
        data = join_payload_customer_message["data"]
        
        phone = _extract_sender_number(key, data)
        
        assert phone == "5565992540370"
        assert "@" not in phone


class TestWebhookJoinFromMeLogic:
    """
    Test the critical fromMe logic for distinguishing AI vs Human operator.
    
    This is the MOST IMPORTANT test suite — it validates that:
    1. AI echoes are correctly ignored
    2. Human operator messages DISABLE AI for 12 hours
    """

    @pytest.mark.asyncio
    async def test_ai_echo_is_ignored_when_tracked(
        self,
        app,
        join_payload_ai_response: dict,
        mock_redis_with_ai_tracking: MagicMock,
    ):
        """
        When fromMe=true AND message is in Redis tracker → ignore (AI echo).
        
        Flow:
        1. AI sends message via JoinClient
        2. JoinClient calls SentMessageTracker.track_sent_message()
        3. Join API fires webhook with fromMe=true
        4. Webhook checks tracker → message_id or phone found → ignore
        """
        from httpx import AsyncClient
        
        app.state.redis = mock_redis_with_ai_tracking
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/webhook/join/", json=join_payload_ai_response)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ai" in data["message"].lower() and "ignored" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_human_operator_disables_ai(
        self,
        app,
        join_payload_human_operator: dict,
        mock_redis_no_ai_tracking: MagicMock,
    ):
        """
        When fromMe=true AND message is NOT in Redis tracker → human operator.
        
        Flow:
        1. Human opens WhatsApp Web/App and sends message manually
        2. Join API fires webhook with fromMe=true
        3. Webhook checks tracker → NOT found → human operator detected
        4. AI should be DISABLED for 12 hours
        """
        from httpx import AsyncClient
        
        app.state.redis = mock_redis_no_ai_tracking
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/webhook/join/", json=join_payload_human_operator)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should indicate operator/paused
        assert "operator" in data["message"].lower() or "paused" in data["message"].lower()


class TestWebhookJoinPayloadStructure:
    """
    Test to understand and document the payload structure from Join API.
    
    These tests serve as documentation for the expected payload format.
    """

    def test_payload_structure_customer_message(
        self,
        join_payload_customer_message: dict,
    ):
        """Document customer message payload structure."""
        # Top level
        assert "event" in join_payload_customer_message
        assert "instance" in join_payload_customer_message
        assert "data" in join_payload_customer_message
        
        # Data level
        data = join_payload_customer_message["data"]
        assert "key" in data
        assert "message" in data
        assert "messageType" in data
        assert "pushName" in data
        assert "messageTimestamp" in data
        
        # Key level - CRITICAL for fromMe detection
        key = data["key"]
        assert "remoteJid" in key
        assert "fromMe" in key
        assert "id" in key
        
        # fromMe=false means customer is sender
        assert key["fromMe"] is False
        
        # remoteJid is customer's phone when fromMe=false
        assert "@s.whatsapp.net" in key["remoteJid"]

    def test_payload_structure_from_me_true(
        self,
        join_payload_ai_response: dict,
    ):
        """
        Document fromMe=true payload structure.
        
        When fromMe=true:
        - The message was sent FROM the instance's connected phone
        - remoteJid is the RECIPIENT (customer's phone)
        - This can be AI or human operator
        """
        key = join_payload_ai_response["data"]["key"]
        
        assert key["fromMe"] is True
        # remoteJid is still customer's phone (the recipient)
        assert "@s.whatsapp.net" in key["remoteJid"]

    def test_from_me_true_ai_vs_human_are_identical(
        self,
        join_payload_ai_response: dict,
        join_payload_human_operator: dict,
    ):
        """
        AI response and human operator payloads are STRUCTURALLY IDENTICAL.
        
        The ONLY way to distinguish them is:
        1. Check if message_id is in Redis tracker (AI tracked it)
        2. Check if phone is in Redis tracker (recent AI activity)
        
        If neither found → it's a human operator → DISABLE AI
        """
        ai_key = join_payload_ai_response["data"]["key"]
        human_key = join_payload_human_operator["data"]["key"]
        
        # Both have fromMe=true
        assert ai_key["fromMe"] is True
        assert human_key["fromMe"] is True
        
        # Both have remoteJid pointing to customer
        assert "@s.whatsapp.net" in ai_key["remoteJid"]
        assert "@s.whatsapp.net" in human_key["remoteJid"]
        
        # The ONLY difference is the message_id
        # AI message_id should be in Redis tracker
        # Human message_id will NOT be in Redis tracker


class TestSentMessageTracker:
    """Test the SentMessageTracker that distinguishes AI from human."""

    @pytest.mark.asyncio
    async def test_track_and_detect_ai_message(
        self,
        mock_redis_client: MagicMock,
    ):
        """AI messages should be tracked and detected."""
        from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker
        
        tracker = SentMessageTracker(mock_redis_client)
        
        # Track a message
        await tracker.track_sent_message(
            instance_key="restaurante_teste",
            phone="5565992540370",
            message_id="AI_MSG_123",
        )
        
        # Verify set was called for both message_id and phone
        assert mock_redis_client.set.call_count == 2

    @pytest.mark.asyncio
    async def test_ai_message_detected_by_message_id(
        self,
        mock_redis_client: MagicMock,
    ):
        """AI message should be detected by message_id in Redis."""
        from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker
        
        # Simulate message_id exists in Redis
        mock_redis_client.exists = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=True)
        )
        
        tracker = SentMessageTracker(mock_redis_client)
        
        result = await tracker.is_ai_sent_message(
            instance_key="restaurante_teste",
            message_id="AI_MSG_123",
            phone=None,
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_ai_message_detected_by_phone(
        self,
        mock_redis_client: MagicMock,
    ):
        """AI message should be detected by phone in Redis (echo tracker)."""
        from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker
        
        # First call for message_id returns False, second for phone returns True
        mock_redis_client.exists = AsyncMock(
            side_effect=[
                MagicMock(is_success=lambda: True, value=False),  # message_id not found
                MagicMock(is_success=lambda: True, value=True),   # phone found
            ]
        )
        
        tracker = SentMessageTracker(mock_redis_client)
        
        result = await tracker.is_ai_sent_message(
            instance_key="restaurante_teste",
            message_id="UNKNOWN_MSG",
            phone="5565992540370",
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_human_operator_not_detected(
        self,
        mock_redis_client: MagicMock,
    ):
        """Human operator message should NOT be detected as AI."""
        from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker
        
        # Neither message_id nor phone found
        mock_redis_client.exists = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=False)
        )
        
        tracker = SentMessageTracker(mock_redis_client)
        
        result = await tracker.is_ai_sent_message(
            instance_key="restaurante_teste",
            message_id="HUMAN_MSG_123",
            phone="5565992540370",
        )
        
        assert result is False


class TestFromMeDecisionMatrix:
    """
    Decision matrix for fromMe handling.
    
    | fromMe | Redis Tracker | Action |
    |--------|---------------|--------|
    | false  | N/A           | Process as customer message |
    | true   | Found         | Ignore (AI echo) |
    | true   | Not Found     | DISABLE AI 12h (human operator) |
    """

    def test_decision_matrix_documentation(self):
        """
        This test documents the decision flow.
        
        When webhook arrives:
        
        1. Check `fromMe` field in `data.key.fromMe`
        
        2. If `fromMe=false`:
           → Customer sent message
           → Extract phone from remoteJid
           → Buffer and process normally
        
        3. If `fromMe=true`:
           → Message was sent FROM the restaurant's number
           → Could be AI or human operator
           → Check Redis tracker:
              a) SentMessageTracker.is_ai_sent_message(instance, message_id, phone)
              b) If True → AI sent this message → ignore (echo)
              c) If False → Human operator sent this → DISABLE AI 12h
        
        4. To disable AI:
           → Create IncomingMessageDTO with body="__human_operator__"
           → ProcessIncomingMessageUseCase will call conversation.disable_ai()
           → AI will be paused for 12 hours for this customer
        """
        assert True  # Documentation test
