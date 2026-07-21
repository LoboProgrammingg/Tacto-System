"""
Integration Tests for Level 2 Agent Order Flow.

Tests the complete order flow from message to order submission.
Uses mocks for external services (WhatsApp, Tacto API).
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from tacto.domain.order.value_objects.order_state import OrderState
from tacto.domain.order.value_objects.order_item import OrderItem
from tacto.domain.order.value_objects.order_status import OrderStatus
from tacto.application.services.order_state_service import OrderStateService
from tacto.application.use_cases.finalize_order import FinalizeOrderUseCase
from tacto.infrastructure.agents.level2_agent import Level2Agent
from tacto.shared.application import Ok, Success, Failure


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def restaurant_id():
    """Sample restaurant UUID."""
    return uuid4()


@pytest.fixture
def customer_phone():
    """Sample customer phone."""
    return "5511999998888"


class InMemoryOrderStatePort:
    """In-memory implementation of OrderStatePort for testing."""

    def __init__(self):
        self._storage: dict[str, OrderState] = {}

    def _key(self, restaurant_id, customer_phone: str) -> str:
        return f"{restaurant_id}:{customer_phone}"

    async def get(self, restaurant_id, customer_phone: str):
        key = self._key(restaurant_id, customer_phone)
        order = self._storage.get(key)
        return Ok(order)

    async def save(self, order: OrderState):
        key = self._key(order.restaurant_id, order.customer_phone)
        self._storage[key] = order
        return Ok(True)

    async def delete(self, restaurant_id, customer_phone: str):
        key = self._key(restaurant_id, customer_phone)
        if key in self._storage:
            del self._storage[key]
        return Ok(True)


@pytest.fixture
def mock_order_state_port():
    """In-memory OrderStatePort for testing."""
    return InMemoryOrderStatePort()


@pytest.fixture
def order_service(mock_order_state_port):
    """OrderStateService with in-memory port."""
    return OrderStateService(mock_order_state_port)


@pytest.fixture
def mock_tacto_client():
    """Mock TactoClient for testing."""
    client = AsyncMock()
    client.submit_order.return_value = Ok({
        "pedidoId": "TACTO-12345",
        "status": "RECEBIDO",
        "mensagem": "Pedido recebido com sucesso",
    })
    client.get_order_status.return_value = Ok({
        "pedidoId": "TACTO-12345",
        "status": "EM_PREPARO",
    })
    return client


@pytest.fixture
def mock_menu_provider():
    """Mock MenuProvider for testing."""
    provider = AsyncMock()
    provider.search_menu_with_prices.return_value = Ok([
        {
            "name": "Pizza Calabresa",
            "category": "Pizzas",
            "description": "Pizza de calabresa com cebola",
            "price": 45.90,
            "variations": [
                {"name": "Pequena", "price": 35.90},
                {"name": "Média", "price": 45.90},
                {"name": "Grande", "price": 55.90},
            ],
            "is_available": True,
        },
        {
            "name": "Pizza Margherita",
            "category": "Pizzas",
            "description": "Tomate, mussarela e manjericão",
            "price": 42.90,
            "variations": [
                {"name": "Pequena", "price": 32.90},
                {"name": "Média", "price": 42.90},
                {"name": "Grande", "price": 52.90},
            ],
            "is_available": True,
        },
    ])
    provider.get_item_by_name.return_value = Ok({
        "name": "Pizza Calabresa",
        "variation": "Grande",
        "price": 55.90,
        "category": "Pizzas",
        "description": "Pizza de calabresa com cebola",
    })
    return provider


# ──────────────────────────────────────────────────────────────────────────────
# Order State Service Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderStateService:
    """Tests for OrderStateService."""

    @pytest.mark.asyncio
    async def test_get_or_create_new_order(self, order_service, restaurant_id, customer_phone):
        """Should create a new order session."""
        result = await order_service.get_or_create(restaurant_id, customer_phone)

        assert isinstance(result, Success)
        order = result.value
        assert order.restaurant_id == restaurant_id
        assert order.customer_phone == customer_phone
        assert order.status == OrderStatus.BROWSING
        assert order.is_empty

    @pytest.mark.asyncio
    async def test_add_item_to_order(self, order_service, restaurant_id, customer_phone):
        """Should add item to order."""
        await order_service.get_or_create(restaurant_id, customer_phone)

        item = OrderItem(
            name="Pizza Calabresa",
            quantity=1,
            unit_price=55.90,
            variation="Grande",
        )
        result = await order_service.add_item(restaurant_id, customer_phone, item)

        assert isinstance(result, Success)
        order = result.value
        assert order.item_count == 1
        assert order.total == 55.90

    @pytest.mark.asyncio
    async def test_add_multiple_items(self, order_service, restaurant_id, customer_phone):
        """Should handle multiple items."""
        await order_service.get_or_create(restaurant_id, customer_phone)

        item1 = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90, variation="Grande")
        await order_service.add_item(restaurant_id, customer_phone, item1)

        item2 = OrderItem(name="Refrigerante", quantity=2, unit_price=8.00)
        result = await order_service.add_item(restaurant_id, customer_phone, item2)

        assert isinstance(result, Success)
        order = result.value
        assert order.item_count == 3  # 1 pizza + 2 refrigerantes
        assert order.total == 55.90 + (2 * 8.00)

    @pytest.mark.asyncio
    async def test_set_delivery_address(self, order_service, restaurant_id, customer_phone):
        """Should set delivery address."""
        await order_service.get_or_create(restaurant_id, customer_phone)

        item = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90)
        await order_service.add_item(restaurant_id, customer_phone, item)

        result = await order_service.set_delivery_address(
            restaurant_id, customer_phone,
            "Rua das Flores, 123 - Centro"
        )

        assert isinstance(result, Success)
        order = result.value
        assert order.delivery_address == "Rua das Flores, 123 - Centro"
        # After setting address, status transitions to COLLECTING_PAYMENT
        assert order.status == OrderStatus.COLLECTING_PAYMENT

    @pytest.mark.asyncio
    async def test_set_payment_method(self, order_service, restaurant_id, customer_phone):
        """Should set payment method."""
        await order_service.get_or_create(restaurant_id, customer_phone)

        item = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90)
        await order_service.add_item(restaurant_id, customer_phone, item)
        await order_service.set_delivery_address(restaurant_id, customer_phone, "Rua das Flores, 123")

        result = await order_service.set_payment_method(restaurant_id, customer_phone, "PIX")

        assert isinstance(result, Success)
        order = result.value
        assert order.payment_method == "PIX"
        # After setting payment, status transitions to CONFIRMING
        assert order.status == OrderStatus.CONFIRMING

    @pytest.mark.asyncio
    async def test_get_order_summary(self, order_service, restaurant_id, customer_phone):
        """Should return order summary."""
        await order_service.get_or_create(restaurant_id, customer_phone)

        item1 = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90, variation="Grande")
        await order_service.add_item(restaurant_id, customer_phone, item1)

        item2 = OrderItem(name="Refrigerante 2L", quantity=1, unit_price=12.00)
        await order_service.add_item(restaurant_id, customer_phone, item2)

        result = await order_service.get_current(restaurant_id, customer_phone)

        assert isinstance(result, Success)
        order = result.value
        summary = order.to_summary()
        assert "Pizza Calabresa" in summary
        assert "55" in summary  # price
        assert "67" in summary  # total


# ──────────────────────────────────────────────────────────────────────────────
# Finalize Order Use Case Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestFinalizeOrderUseCase:
    """Tests for FinalizeOrderUseCase."""

    @pytest.fixture
    def finalize_use_case(self, order_service, mock_tacto_client):
        """FinalizeOrderUseCase with mocked dependencies."""
        return FinalizeOrderUseCase(
            order_service=order_service,
            tacto_client=mock_tacto_client,
        )

    @pytest.mark.asyncio
    async def test_finalize_valid_order(
        self, finalize_use_case, order_service, mock_tacto_client,
        restaurant_id, customer_phone
    ):
        """Should finalize a complete order."""
        # Setup: Create complete order
        await order_service.get_or_create(restaurant_id, customer_phone)

        item = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90, variation="Grande")
        await order_service.add_item(restaurant_id, customer_phone, item)
        await order_service.set_delivery_address(restaurant_id, customer_phone, "Rua das Flores, 123")
        await order_service.set_payment_method(restaurant_id, customer_phone, "PIX")

        # Execute
        result = await finalize_use_case.execute(
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            empresa_base_id="EMP123",
            grupo_empresarial="GRP456",
        )

        # Verify
        assert isinstance(result, Success)
        assert result.value["success"] is True
        assert result.value["order_id"] == "TACTO-12345"
        assert result.value["status"] == "CONFIRMED"

        # Verify Tacto API was called
        mock_tacto_client.submit_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_empty_cart_fails(
        self, finalize_use_case, order_service, restaurant_id, customer_phone
    ):
        """Should fail if cart is empty."""
        await order_service.get_or_create(restaurant_id, customer_phone)

        result = await finalize_use_case.execute(
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            empresa_base_id="EMP123",
            grupo_empresarial="GRP456",
        )

        assert isinstance(result, Failure)
        assert "vazio" in str(result.error).lower() or "empty" in str(result.error).lower()

    @pytest.mark.asyncio
    async def test_finalize_without_address_fails(
        self, finalize_use_case, order_service, restaurant_id, customer_phone
    ):
        """Should fail if address not set."""
        await order_service.get_or_create(restaurant_id, customer_phone)

        item = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90)
        await order_service.add_item(restaurant_id, customer_phone, item)

        result = await finalize_use_case.execute(
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            empresa_base_id="EMP123",
            grupo_empresarial="GRP456",
        )

        assert isinstance(result, Failure)
        assert "endereço" in str(result.error).lower() or "address" in str(result.error).lower()

    @pytest.mark.asyncio
    async def test_finalize_without_payment_fails(
        self, finalize_use_case, order_service, restaurant_id, customer_phone
    ):
        """Should fail if payment method not set."""
        await order_service.get_or_create(restaurant_id, customer_phone)

        item = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90)
        await order_service.add_item(restaurant_id, customer_phone, item)
        await order_service.set_delivery_address(restaurant_id, customer_phone, "Rua das Flores, 123")

        result = await finalize_use_case.execute(
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            empresa_base_id="EMP123",
            grupo_empresarial="GRP456",
        )

        assert isinstance(result, Failure)
        assert "pagamento" in str(result.error).lower() or "payment" in str(result.error).lower()


# ──────────────────────────────────────────────────────────────────────────────
# Level 2 Agent Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestLevel2Agent:
    """Tests for Level2Agent message processing."""

    @pytest.fixture
    def level2_agent(self, order_service):
        """Level2Agent with mocked dependencies."""
        return Level2Agent(
            order_service=order_service,
            memory_manager=None,
        )

    def test_agent_properties(self, level2_agent):
        """Should have correct agent properties."""
        assert level2_agent.level == 2
        assert level2_agent.name == "Level2Agent"

    @pytest.mark.asyncio
    async def test_agent_initialization(self, level2_agent):
        """Should initialize successfully."""
        await level2_agent.initialize()
        assert level2_agent._chain is not None


# ──────────────────────────────────────────────────────────────────────────────
# WhatsApp Message Flow Simulation
# ──────────────────────────────────────────────────────────────────────────────

class TestWhatsAppOrderFlow:
    """Simulates complete WhatsApp order flow."""

    @pytest.mark.asyncio
    async def test_complete_order_flow(
        self, order_service, mock_tacto_client, restaurant_id, customer_phone
    ):
        """
        Simulates complete order flow:
        1. Customer asks about menu
        2. Customer orders pizza
        3. Customer provides address
        4. Customer chooses payment
        5. Order is confirmed and sent to Tacto
        """
        # Step 1: Start order session
        start_result = await order_service.get_or_create(restaurant_id, customer_phone)
        assert isinstance(start_result, Success)

        # Step 2: Add item (pizza calabresa grande)
        item1 = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90, variation="Grande")
        add_result = await order_service.add_item(restaurant_id, customer_phone, item1)
        assert isinstance(add_result, Success)
        assert add_result.value.item_count == 1

        # Step 3: Add another item (refrigerante)
        item2 = OrderItem(name="Refrigerante 2L", quantity=2, unit_price=12.00)
        add_result2 = await order_service.add_item(restaurant_id, customer_phone, item2)
        assert isinstance(add_result2, Success)
        assert add_result2.value.total == 55.90 + 24.00

        # Step 4: Set delivery address
        address_result = await order_service.set_delivery_address(
            restaurant_id, customer_phone,
            "Rua das Flores, 123 - Centro - São Paulo/SP"
        )
        assert isinstance(address_result, Success)

        # Step 5: Set payment method
        payment_result = await order_service.set_payment_method(
            restaurant_id, customer_phone,
            "Cartão de Crédito"
        )
        assert isinstance(payment_result, Success)

        # Step 6: Finalize order
        finalize_uc = FinalizeOrderUseCase(order_service, mock_tacto_client)
        finalize_result = await finalize_uc.execute(
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            empresa_base_id="EMP001",
            grupo_empresarial="GRP001",
        )

        assert isinstance(finalize_result, Success)
        assert finalize_result.value["success"] is True
        assert finalize_result.value["order_id"] == "TACTO-12345"
        assert finalize_result.value["total"] == 79.90
        assert finalize_result.value["item_count"] == 3

    @pytest.mark.asyncio
    async def test_order_modification_flow(
        self, order_service, restaurant_id, customer_phone
    ):
        """
        Simulates order modification:
        1. Add items
        2. Remove item
        3. Change quantity
        """
        await order_service.get_or_create(restaurant_id, customer_phone)

        # Add pizza
        item1 = OrderItem(name="Pizza Calabresa", quantity=2, unit_price=55.90, variation="Grande")
        await order_service.add_item(restaurant_id, customer_phone, item1)

        # Add refrigerante
        item2 = OrderItem(name="Refrigerante", quantity=1, unit_price=8.00)
        await order_service.add_item(restaurant_id, customer_phone, item2)

        # Get current state
        current = await order_service.get_current(restaurant_id, customer_phone)
        assert current.value.item_count == 3
        assert current.value.total == (2 * 55.90) + 8.00

        # Remove refrigerante
        remove_result = await order_service.remove_item(
            restaurant_id, customer_phone,
            "Refrigerante"
        )
        assert isinstance(remove_result, Success)

        # Verify
        final = await order_service.get_current(restaurant_id, customer_phone)
        assert final.value.item_count == 2
        assert final.value.total == 2 * 55.90

    @pytest.mark.asyncio
    async def test_order_cancellation_flow(
        self, order_service, restaurant_id, customer_phone
    ):
        """
        Simulates order cancellation.
        """
        await order_service.get_or_create(restaurant_id, customer_phone)

        item = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=55.90)
        await order_service.add_item(restaurant_id, customer_phone, item)

        # Cancel order
        cancel_result = await order_service.cancel_order(restaurant_id, customer_phone)
        assert isinstance(cancel_result, Success)
