"""
Embedding Client Port.

SHIM: Re-exports from tacto.application.ports.embedding_client for backward compatibility.
"""

from tacto.application.ports.embedding_client import EmbeddingClient

__all__ = ["EmbeddingClient"]
