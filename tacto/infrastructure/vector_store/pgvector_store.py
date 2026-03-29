"""
Backward-compatibility shim.

The authoritative implementation lives in:
    tacto/infrastructure/database/pgvector_store.py

This module re-exports everything so existing imports continue to work.
"""

from tacto.infrastructure.database.pgvector_store import PgvectorStore  # noqa: F401

__all__ = ["PgvectorStore"]
