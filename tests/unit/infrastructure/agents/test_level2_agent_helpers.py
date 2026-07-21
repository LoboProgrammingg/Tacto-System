"""Unit tests for Level2Agent module helpers (menu resend + closed-once)."""

from tacto.infrastructure.agents.level2_agent import (
    _history_recently_sent_closed,
    _history_recently_sent_menu,
    _is_explicit_menu_request,
)


_MENU_URL = "https://cardapio.teste.com"
_HISTORY_WITH_MENU = [
    {"role": "assistant", "content": f"📋 Cardápio: {_MENU_URL}"},
    {"role": "user", "content": "obrigado"},
]


class TestExplicitMenuRequest:
    def test_cardapio_word_is_explicit(self):
        assert _is_explicit_menu_request("manda o cardápio de novo", [], _MENU_URL)

    def test_generic_resend_after_menu_link(self):
        assert _is_explicit_menu_request(
            "não recebi, manda de novo", _HISTORY_WITH_MENU, _MENU_URL
        )

    def test_generic_resend_without_prior_menu_is_not_explicit(self):
        assert not _is_explicit_menu_request("manda de novo", [], _MENU_URL)

    def test_resend_about_address_is_not_menu(self):
        assert not _is_explicit_menu_request(
            "manda o endereço de novo", _HISTORY_WITH_MENU, _MENU_URL
        )


class TestHistoryScans:
    def test_detects_recent_menu_link(self):
        assert _history_recently_sent_menu(_HISTORY_WITH_MENU, _MENU_URL)

    def test_no_menu_in_history(self):
        assert not _history_recently_sent_menu(
            [{"role": "assistant", "content": "Olá!"}], _MENU_URL
        )

    def test_detects_recent_closed_template(self):
        history = [
            {"role": "assistant", "content": "Olá! 😊\n\nNo momento, estamos fechados."}
        ]
        assert _history_recently_sent_closed(history)

    def test_no_closed_template_in_history(self):
        assert not _history_recently_sent_closed(
            [{"role": "assistant", "content": "Olá! Como posso ajudar?"}]
        )
