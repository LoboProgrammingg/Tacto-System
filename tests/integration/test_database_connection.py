"""
Integration Test - Database Connection.

Basic test to verify PostgreSQL connection is working.
"""

import pytest
from sqlalchemy import text


class TestDatabaseConnection:
    """Test database connectivity."""

    @pytest.mark.asyncio
    async def test_database_connection(self, test_engine):
        """Should connect to PostgreSQL and execute query."""
        async with test_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as value"))
            row = result.fetchone()
            assert row.value == 1

    @pytest.mark.asyncio
    async def test_database_tables_exist(self, test_engine):
        """Should have required tables in database."""
        async with test_engine.connect() as conn:
            # Check restaurants table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'restaurants'
                )
            """))
            assert result.scalar() is True

            # Check conversations table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'conversations'
                )
            """))
            assert result.scalar() is True

            # Check messages table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'messages'
                )
            """))
            assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_pgvector_extension(self, test_engine):
        """Should have pgvector extension installed."""
        async with test_engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM pg_extension WHERE extname = 'vector'
                )
            """))
            assert result.scalar() is True
