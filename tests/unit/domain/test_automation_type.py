"""Tests for AutomationType — menu-item capability per automation level."""

import pytest

from tacto.domain.restaurant.value_objects.automation_type import AutomationType


def test_basic_no_menu_is_level_four():
    assert AutomationType.BASIC_NO_MENU == 4
    assert AutomationType.from_value(4) is AutomationType.BASIC_NO_MENU
    assert AutomationType.BASIC_NO_MENU.display_name == "Básico — Sem Cardápio"


def test_only_basic_no_menu_cannot_discuss_menu_items():
    assert AutomationType.BASIC_NO_MENU.can_discuss_menu_items is False
    for level in (AutomationType.BASIC, AutomationType.INTERMEDIATE, AutomationType.ADVANCED):
        assert level.can_discuss_menu_items is True


def test_basic_no_menu_has_no_order_or_menu_capabilities():
    level = AutomationType.BASIC_NO_MENU
    assert level.can_access_menu is False
    assert level.can_collect_orders is False
    assert level.can_finalize_orders is False
    assert level.requires_handoff is False
    assert level.can_recommend_products is False


def test_from_value_rejects_unknown_level():
    with pytest.raises(ValueError):
        AutomationType.from_value(5)
