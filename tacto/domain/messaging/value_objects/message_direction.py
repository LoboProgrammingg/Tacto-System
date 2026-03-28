"""
MessageDirection Value Object.

Represents the direction of a message (incoming from customer or outgoing to customer).
"""

from enum import StrEnum


class MessageDirection(StrEnum):
    """Direction of message flow."""

    INCOMING = "incoming"
    OUTGOING = "outgoing"

    @property
    def is_incoming(self) -> bool:
        """Check if message is from customer."""
        return self == MessageDirection.INCOMING

    @property
    def is_outgoing(self) -> bool:
        """Check if message is to customer."""
        return self == MessageDirection.OUTGOING
