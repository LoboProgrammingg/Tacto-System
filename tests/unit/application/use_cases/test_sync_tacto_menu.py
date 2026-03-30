"""
Unit Tests for SyncTactoMenu helpers and MenuItem.

Tests menu sync helper functions without importing the full use case
which depends on google.genai.
"""

import hashlib
from uuid import uuid4

import pytest

from tacto.application.ports.menu_provider import MenuItem, MenuData
from tacto.shared.domain.value_objects import RestaurantId


# ──────────────────────────────────────────────────────────────────────────────
# Local copies of helper functions for testing
# ──────────────────────────────────────────────────────────────────────────────

def _compute_hash(content: str) -> str:
    """Compute MD5 hash of content for change detection."""
    return hashlib.md5(content.encode()).hexdigest()


def _build_embedding_item(item: MenuItem, embedding: list[float], content_hash: str) -> dict:
    """Build embedding item dict for pgvector storage."""
    return {
        "content": item.to_context_text(),
        "embedding": embedding,
        "metadata": {
            "name": item.name,
            "category": item.category,
            "has_description": item.description is not None,
            "content_hash": content_hash,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# MenuItem Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMenuItem:
    """Tests for MenuItem data class."""

    def test_to_embed_content_with_description(self):
        """Should generate embed content with name, category, description."""
        item = MenuItem(
            name="Pizza Margherita",
            description="Molho de tomate, mozzarella, manjericão",
            price=45.90,
            category="Pizzas",
        )

        content = item.to_embed_content()

        assert "Pizza Margherita" in content
        assert "Pizzas" in content
        assert "Molho de tomate" in content
        assert "45.90" not in content  # NO price ever

    def test_to_embed_content_without_description(self):
        """Should generate embed content without description."""
        item = MenuItem(
            name="Água Mineral",
            description=None,
            price=5.00,
            category="Bebidas",
        )

        content = item.to_embed_content()

        assert "Água Mineral" in content
        assert "Bebidas" in content
        assert "5.00" not in content

    def test_to_context_text_with_description(self):
        """Should format context text as 'name: description'."""
        item = MenuItem(
            name="Pizza Calabresa",
            description="Calabresa fatiada, cebola, azeitonas",
            price=42.90,
            category="Pizzas",
        )

        text = item.to_context_text()

        assert text == "Pizza Calabresa: Calabresa fatiada, cebola, azeitonas"
        assert "42.90" not in text

    def test_to_context_text_without_description(self):
        """Should return just name when no description."""
        item = MenuItem(
            name="Refrigerante Lata",
            description=None,
            price=6.00,
            category="Bebidas",
        )

        text = item.to_context_text()

        assert text == "Refrigerante Lata"

    def test_is_available_default_true(self):
        """is_available should default to True."""
        item = MenuItem(
            name="Item Teste",
            description="Desc",
            price=10.0,
            category="Cat",
        )

        assert item.is_available is True

    def test_is_available_false(self):
        """Should track unavailable items."""
        item = MenuItem(
            name="Item Indisponível",
            description="Em falta",
            price=10.0,
            category="Cat",
            is_available=False,
        )

        assert item.is_available is False


# ──────────────────────────────────────────────────────────────────────────────
# MenuData Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMenuData:
    """Tests for MenuData data class."""

    def test_menu_data_creation(self):
        """Should create MenuData with all fields."""
        rid = RestaurantId(uuid4())
        items = [
            MenuItem("Item 1", "Desc 1", 10.0, "Cat1"),
            MenuItem("Item 2", "Desc 2", 20.0, "Cat2"),
        ]

        menu = MenuData(
            restaurant_id=rid,
            items=items,
            categories=["Cat1", "Cat2"],
            raw_text="Raw menu text",
            last_updated="2026-03-30",
            address="Rua Teste, 123",
            hours_text="Seg-Sex: 18h às 23h",
        )

        assert menu.restaurant_id == rid
        assert len(menu.items) == 2
        assert "Cat1" in menu.categories
        assert menu.address == "Rua Teste, 123"

    def test_menu_data_optional_fields(self):
        """Optional fields should have defaults."""
        rid = RestaurantId(uuid4())

        menu = MenuData(
            restaurant_id=rid,
            items=[],
            categories=[],
            raw_text="",
            last_updated="",
        )

        assert menu.address is None
        assert menu.hours_text == ""
        assert menu.restaurant_description == ""


# ──────────────────────────────────────────────────────────────────────────────
# Helper Function Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestSyncHelperFunctions:
    """Tests for sync helper functions."""

    def test_compute_hash_deterministic(self):
        """Same content should produce same hash."""
        content = "Pizza Margherita | Pizzas | Molho de tomate"
        hash1 = _compute_hash(content)
        hash2 = _compute_hash(content)
        assert hash1 == hash2

    def test_compute_hash_different_content(self):
        """Different content should produce different hash."""
        hash1 = _compute_hash("Pizza Margherita")
        hash2 = _compute_hash("Pizza Calabresa")
        assert hash1 != hash2

    def test_compute_hash_is_md5(self):
        """Should produce valid MD5 hash (32 hex chars)."""
        hash_val = _compute_hash("Test content")
        assert len(hash_val) == 32
        assert all(c in "0123456789abcdef" for c in hash_val)

    def test_build_embedding_item_structure(self):
        """Should build correct embedding item dict."""
        item = MenuItem(
            name="Pizza Teste",
            description="Descrição teste",
            price=40.0,
            category="Pizzas",
        )
        embedding = [0.1, 0.2, 0.3]
        content_hash = "abc123"

        result = _build_embedding_item(item, embedding, content_hash)

        assert "content" in result
        assert "embedding" in result
        assert "metadata" in result
        assert result["content"] == "Pizza Teste: Descrição teste"
        assert result["embedding"] == [0.1, 0.2, 0.3]

    def test_build_embedding_item_metadata(self):
        """Should include correct metadata fields."""
        item = MenuItem(
            name="Pizza Teste",
            description="Descrição teste",
            price=40.0,
            category="Pizzas",
        )

        result = _build_embedding_item(item, [0.1], "hash123")

        metadata = result["metadata"]
        assert metadata["name"] == "Pizza Teste"
        assert metadata["category"] == "Pizzas"
        assert metadata["has_description"] is True
        assert metadata["content_hash"] == "hash123"

    def test_build_embedding_item_no_description(self):
        """Should handle items without description."""
        item = MenuItem(
            name="Água",
            description=None,
            price=5.0,
            category="Bebidas",
        )

        result = _build_embedding_item(item, [0.1], "hash456")

        assert result["metadata"]["has_description"] is False
        assert result["content"] == "Água"


# ──────────────────────────────────────────────────────────────────────────────
# Incremental Sync Logic Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestIncrementalSyncLogic:
    """Tests for incremental sync content hash logic."""

    def test_unchanged_item_has_same_hash(self):
        """Unchanged item should produce same hash."""
        item = MenuItem("Pizza", "Descrição", 10.0, "Pizzas")
        content = item.to_embed_content()

        hash1 = _compute_hash(content)
        hash2 = _compute_hash(content)

        assert hash1 == hash2

    def test_changed_description_changes_hash(self):
        """Changed description should produce different hash."""
        item1 = MenuItem("Pizza", "Descrição original", 10.0, "Pizzas")
        item2 = MenuItem("Pizza", "Descrição modificada", 10.0, "Pizzas")

        hash1 = _compute_hash(item1.to_embed_content())
        hash2 = _compute_hash(item2.to_embed_content())

        assert hash1 != hash2

    def test_price_change_does_not_affect_hash(self):
        """Price change should NOT affect hash (price not in embed content)."""
        item1 = MenuItem("Pizza", "Descrição", 10.0, "Pizzas")
        item2 = MenuItem("Pizza", "Descrição", 99.0, "Pizzas")

        hash1 = _compute_hash(item1.to_embed_content())
        hash2 = _compute_hash(item2.to_embed_content())

        assert hash1 == hash2  # Same because price not included

    def test_category_change_affects_hash(self):
        """Category change should affect hash."""
        item1 = MenuItem("Item", "Desc", 10.0, "Categoria A")
        item2 = MenuItem("Item", "Desc", 10.0, "Categoria B")

        hash1 = _compute_hash(item1.to_embed_content())
        hash2 = _compute_hash(item2.to_embed_content())

        assert hash1 != hash2


# ──────────────────────────────────────────────────────────────────────────────
# Filter Available Items Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestFilterAvailableItems:
    """Tests for filtering available items (sync logic)."""

    def test_filter_available_items(self):
        """Should filter out unavailable items."""
        items = [
            MenuItem("Available 1", "D1", 10.0, "Cat", is_available=True),
            MenuItem("Unavailable", "D2", 20.0, "Cat", is_available=False),
            MenuItem("Available 2", "D3", 30.0, "Cat", is_available=True),
        ]

        available = [i for i in items if i.is_available]

        assert len(available) == 2
        assert all(i.is_available for i in available)
        assert "Unavailable" not in [i.name for i in available]

    def test_all_available(self):
        """All items available should return all."""
        items = [
            MenuItem("Item 1", "D1", 10.0, "Cat"),
            MenuItem("Item 2", "D2", 20.0, "Cat"),
        ]

        available = [i for i in items if i.is_available]

        assert len(available) == 2

    def test_none_available(self):
        """No items available should return empty list."""
        items = [
            MenuItem("Item 1", "D1", 10.0, "Cat", is_available=False),
            MenuItem("Item 2", "D2", 20.0, "Cat", is_available=False),
        ]

        available = [i for i in items if i.is_available]

        assert len(available) == 0
