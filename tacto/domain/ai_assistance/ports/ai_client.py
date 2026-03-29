"""
AI Client Port.

SHIM: Re-exports from tacto.application.ports.ai_client for backward compatibility.
"""

from tacto.application.ports.ai_client import AIClient, AIRequest, AIResponse

__all__ = ["AIClient", "AIRequest", "AIResponse"]
