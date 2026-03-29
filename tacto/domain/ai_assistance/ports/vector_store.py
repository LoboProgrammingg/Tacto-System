"""
Vector Store Port.

SHIM: Re-exports from tacto.application.ports.vector_store for backward compatibility.
"""

from tacto.application.ports.vector_store import VectorStore

__all__ = ["VectorStore"]
