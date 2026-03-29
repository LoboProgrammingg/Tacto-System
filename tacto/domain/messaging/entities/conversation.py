"""
Conversation Entity - Aggregate Root.

Represents a conversation thread between a customer and the restaurant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from tacto.domain.restaurant.value_objects.opening_hours import OpeningHours

from tacto.domain.messaging.events.ai_disabled import AIDisabled
from tacto.domain.messaging.events.ai_enabled import AIEnabled
from tacto.domain.messaging.events.message_received import MessageReceived
from tacto.domain.shared.events.domain_event import DomainEvent
from tacto.domain.shared.exceptions import BusinessRuleViolationError
from tacto.domain.shared.value_objects import ConversationId, PhoneNumber, RestaurantId


_DEFAULT_AI_DISABLE_DURATION_HOURS = 12


@dataclass
class Conversation:
    """
    Conversation Aggregate Root.

    Represents a conversation thread between a customer and the restaurant.
    Controls AI activation state and tracks message history metadata.

    Invariants:
    - Must belong to a restaurant (multi-tenancy)
    - Customer phone must be valid
    - AI can only be disabled with a reason
    """

    id: ConversationId
    restaurant_id: RestaurantId
    customer_phone: PhoneNumber
    customer_name: Optional[str] = None
    is_ai_active: bool = True
    ai_disabled_until: Optional[datetime] = None
    ai_disabled_reason: Optional[str] = None
    last_message_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Pending domain events — lidos e despachados pelo repositório/use case após save
    pending_events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    def can_ai_respond(self) -> bool:
        """
        Check if AI can respond to this conversation.

        AI cannot respond if:
        - is_ai_active is False
        - ai_disabled_until is in the future
        """
        if not self.is_ai_active:
            return False

        if self.ai_disabled_until and self.ai_disabled_until > datetime.now(timezone.utc):
            return False

        return True

    def _add_event(self, event: DomainEvent) -> None:
        """Acumula evento para despacho após persistência."""
        self.pending_events.append(event)

    def disable_ai(
        self,
        reason: str,
        duration_hours: int = _DEFAULT_AI_DISABLE_DURATION_HOURS,
    ) -> None:
        """
        Disable AI for this conversation.

        Args:
            reason: Why AI is being disabled (e.g., 'human_intervention')
            duration_hours: How long to disable AI (default: 12 hours)
        """
        self.is_ai_active = False
        self.ai_disabled_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        self.ai_disabled_reason = reason
        self._touch()
        self._add_event(AIDisabled(
            conversation_id=self.id.value,
            restaurant_id=self.restaurant_id.value,
            customer_phone=self.customer_phone.value,
            reason=reason,
            disabled_until=self.ai_disabled_until,
        ))

    def enable_ai(self) -> None:
        """Re-enable AI for this conversation."""
        self.is_ai_active = True
        self.ai_disabled_until = None
        self.ai_disabled_reason = None
        self._touch()
        self._add_event(AIEnabled(
            conversation_id=self.id.value,
            restaurant_id=self.restaurant_id.value,
            customer_phone=self.customer_phone.value,
        ))

    def disable_ai_until_opening(
        self,
        opening_hours: "OpeningHours",
        tz: str,
        buffer_minutes: int = 10,
        fallback_hours: int = 12,
    ) -> None:
        """
        Disable AI until buffer_minutes before the restaurant's next opening.

        Used when restaurant is closed — AI re-enables automatically as the
        restaurant approaches its next opening time, so the customer gets a
        response as soon as ordering becomes possible.

        Args:
            opening_hours: Restaurant's weekly schedule.
            tz: Restaurant's local timezone string (e.g. 'America/Cuiaba').
            buffer_minutes: Minutes before opening to re-enable AI (default: 10).
            fallback_hours: Hours to disable if no opening is found (default: 12).
        """
        next_opening_utc = opening_hours.get_next_opening_utc(tz)

        if next_opening_utc is None:
            # No opening found in the next 8 days — fall back to fixed duration
            self.disable_ai(reason="restaurant_closed", duration_hours=fallback_hours)
            return

        reactivate_at = next_opening_utc - timedelta(minutes=buffer_minutes)

        # If reactivate_at is already in the past, enable AI immediately
        if reactivate_at <= datetime.now(timezone.utc):
            self.enable_ai()
            return

        self.is_ai_active = False
        self.ai_disabled_until = reactivate_at
        self.ai_disabled_reason = "restaurant_closed"
        self._touch()

    def handle_human_intervention(self) -> None:
        """
        Handle human operator intervention.

        When a human operator sends a message (source=phone, fromMe=true),
        AI should be disabled for 12 hours.
        """
        self.disable_ai(reason="human_intervention")

    def record_message(self, timestamp: datetime) -> None:
        """Record that a message was sent/received."""
        self.last_message_at = timestamp
        self._touch()
        self._add_event(MessageReceived(
            conversation_id=self.id.value,
            restaurant_id=self.restaurant_id.value,
            customer_phone=self.customer_phone.value,
        ))

    def update_customer_name(self, name: str) -> None:
        """Update customer name if discovered."""
        if name and name.strip():
            self.customer_name = name.strip()
            self._touch()

    def _touch(self) -> None:
        """Update timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        restaurant_id: RestaurantId,
        customer_phone: PhoneNumber,
        customer_name: Optional[str] = None,
        conversation_id: Optional[ConversationId] = None,
    ) -> "Conversation":
        """Factory method to create a new Conversation."""
        return cls(
            id=conversation_id or ConversationId.generate(),
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
        )

    @classmethod
    def get_or_create_key(cls, restaurant_id: RestaurantId, phone: PhoneNumber) -> str:
        """Generate unique key for conversation lookup."""
        return f"{restaurant_id}:{phone.value}"
