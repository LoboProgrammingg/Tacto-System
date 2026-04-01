"""
FinalizeOrder Use Case.

Use case for finalizing customer orders and sending to Tacto API.
"""

from typing import Optional
from uuid import UUID

import structlog

from tacto.application.services.order_state_service import OrderStateService
from tacto.domain.order.value_objects.order_state import OrderState
from tacto.domain.order.value_objects.order_status import OrderStatus
from tacto.infrastructure.external.tacto_client import TactoClient
from tacto.shared.application import Err, Failure, Ok, Success


logger = structlog.get_logger()


class FinalizeOrderUseCase:
    """
    Use case for finalizing orders.

    Implements the order finalization flow:
    1. Validate order state is ready for confirmation
    2. Build order payload for Tacto API
    3. Submit order to Tacto
    4. Update order state to CONFIRMED
    5. Cleanup order from session storage
    """

    def __init__(
        self,
        order_service: OrderStateService,
        tacto_client: TactoClient,
    ) -> None:
        """
        Initialize use case with dependencies.

        Args:
            order_service: Service for order state management
            tacto_client: Client for Tacto API integration
        """
        self._order_service = order_service
        self._tacto = tacto_client

    async def execute(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        empresa_base_id: str,
        grupo_empresarial: str,
    ) -> Success[dict] | Failure[Exception]:
        """
        Execute order finalization.

        Args:
            restaurant_id: Restaurant UUID
            customer_phone: Customer phone number
            empresa_base_id: Tacto empresa base ID
            grupo_empresarial: Tacto grupo empresarial

        Returns:
            Success with order confirmation data or Failure
        """
        log = logger.bind(
            restaurant_id=str(restaurant_id),
            customer_phone=customer_phone,
        )

        # 1. Get current order state
        order_result = await self._order_service.get_current(restaurant_id, customer_phone)
        if isinstance(order_result, Failure):
            log.error("Failed to get order", error=str(order_result.error))
            return order_result

        order = order_result.value
        if order is None:
            log.warning("No order found")
            return Err(ValueError("Nenhum pedido encontrado para confirmar"))

        # 2. Validate order is ready
        validation = self._validate_order(order)
        if isinstance(validation, Failure):
            log.warning("Order validation failed", error=str(validation.error))
            return validation

        # 3. Build Tacto order payload
        payload = self._build_tacto_payload(order, empresa_base_id, grupo_empresarial)

        # 4. Submit to Tacto API
        log.info("Submitting order to Tacto", payload_items=len(order.items))

        submit_result = await self._tacto.submit_order(
            grupo_empresarial=grupo_empresarial,
            empresa_base_id=empresa_base_id,
            order_payload=payload,
        )

        if isinstance(submit_result, Failure):
            log.error("Failed to submit order to Tacto", error=str(submit_result.error))
            return submit_result

        tacto_response = submit_result.value
        tacto_order_id = (
            tacto_response.get("pedidoId")
            or tacto_response.get("id")
            or f"TACTO-{restaurant_id.hex[:8]}"
        )

        log.info("Order submitted successfully", tacto_order_id=tacto_order_id)

        # 5. Confirm order in local state
        confirm_result = await self._order_service.confirm_order(restaurant_id, customer_phone)
        if isinstance(confirm_result, Failure):
            log.warning("Failed to confirm order locally", error=str(confirm_result.error))
            # Don't fail - order was already submitted to Tacto

        # 6. Cleanup session (order is done)
        await self._order_service.finalize_order(restaurant_id, customer_phone)

        return Ok({
            "success": True,
            "order_id": tacto_order_id,
            "total": order.total,
            "item_count": order.item_count,
            "delivery_address": order.delivery_address,
            "payment_method": order.payment_method,
            "status": "CONFIRMED",
        })

    def _validate_order(self, order: OrderState) -> Success[bool] | Failure[Exception]:
        """Validate order is ready for finalization."""
        if order.is_empty:
            return Err(ValueError("Carrinho está vazio"))

        if not order.delivery_address:
            return Err(ValueError("Endereço de entrega não informado"))

        if not order.payment_method:
            return Err(ValueError("Forma de pagamento não informada"))

        if order.status not in (OrderStatus.CONFIRMING, OrderStatus.COLLECTING_PAYMENT):
            return Err(ValueError(f"Pedido não está pronto para confirmação (status: {order.status.value})"))

        return Ok(True)

    def _build_tacto_payload(
        self,
        order: OrderState,
        empresa_base_id: str,
        grupo_empresarial: str,
    ) -> dict:
        """
        Build order payload for Tacto API.

        Maps OrderState to Tacto's expected format.
        """
        items = []
        for item in order.items:
            items.append({
                "nome": item.name,
                "quantidade": item.quantity,
                "precoUnitario": item.unit_price,
                "precoTotal": item.total_price,
                "tamanho": item.variation,
                "observacao": item.observations,
            })

        return {
            "empresaBaseId": empresa_base_id,
            "grupoEmpresarial": grupo_empresarial,
            "cliente": {
                "telefone": order.customer_phone,
                "nome": order.customer_name or "Cliente",
            },
            "enderecoEntrega": {
                "endereco": order.delivery_address,
            },
            "formaPagamento": order.payment_method,
            "itens": items,
            "subtotal": order.subtotal,
            "total": order.total,
            "observacaoGeral": order.observations,
            "origem": "WHATSAPP_AI",
        }
