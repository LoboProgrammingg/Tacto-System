"""
AutomationType Value Object.

Represents the automation level for a restaurant's AI assistant.
"""

from enum import IntEnum


class AutomationType(IntEnum):
    """
    Level of AI automation for restaurant.

    BASIC (1): Informativo - responde dúvidas, horários, endereço, menu básico
    INTERMEDIATE (2): Coleta pedidos - monta carrinho mas NÃO finaliza,
                      sempre faz handoff para atendente confirmar taxa e pedido
    ADVANCED (3): Automação completa - finaliza pedido sem intervenção humana (futuro)
    """

    BASIC = 1
    INTERMEDIATE = 2
    ADVANCED = 3

    @property
    def display_name(self) -> str:
        """Get human-readable name."""
        names = {
            AutomationType.BASIC: "Básico (Informativo)",
            AutomationType.INTERMEDIATE: "Intermediário (Pedidos + Handoff)",
            AutomationType.ADVANCED: "Avançado (Automação Completa)",
        }
        return names.get(self, "Unknown")

    @property
    def can_access_menu(self) -> bool:
        """Check if this level can access detailed menu information."""
        return self in (AutomationType.INTERMEDIATE, AutomationType.ADVANCED)

    @property
    def can_collect_orders(self) -> bool:
        """Check if this level can collect orders (but may need handoff)."""
        return self in (AutomationType.INTERMEDIATE, AutomationType.ADVANCED)

    @property
    def can_finalize_orders(self) -> bool:
        """Check if this level can finalize orders WITHOUT human intervention."""
        return self == AutomationType.ADVANCED

    @property
    def requires_handoff(self) -> bool:
        """Check if this level requires handoff to human for order confirmation."""
        return self == AutomationType.INTERMEDIATE

    @property
    def can_recommend_products(self) -> bool:
        """Check if this level can recommend products."""
        return self in (AutomationType.INTERMEDIATE, AutomationType.ADVANCED)

    @classmethod
    def from_value(cls, value: int) -> "AutomationType":
        """Create from integer value with validation."""
        try:
            return cls(value)
        except ValueError:
            raise ValueError(
                f"Invalid automation type: {value}. Must be 1 (BASIC), 2 (INTERMEDIATE), or 3 (ADVANCED)"
            )

    def __str__(self) -> str:
        return self.name
