"""
Messaging Client Port.

SHIM: Re-exports from tacto.application.ports.messaging_client for backward compatibility.
"""

from tacto.application.ports.messaging_client import MessagingClient, SendMessageResult

__all__ = ["MessagingClient", "SendMessageResult"]
