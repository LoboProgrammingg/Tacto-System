from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from tacto.domain.messaging.entities.conversation import Conversation
from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.restaurant.value_objects.opening_hours import DaySchedule, OpeningHours
from tacto.interfaces.http.routes.chat import _build_agent_context
from tacto.shared.domain.value_objects import PhoneNumber, RestaurantId


def _opening_hours() -> OpeningHours:
    return OpeningHours(
        monday=DaySchedule.open("11:00", "23:00"),
        tuesday=DaySchedule.open("11:00", "23:00"),
        wednesday=DaySchedule.open("11:00", "23:00"),
        thursday=DaySchedule.open("11:00", "23:00"),
        friday=DaySchedule.open("11:00", "23:00"),
        saturday=DaySchedule.open("11:00", "23:00"),
        sunday=DaySchedule.open("11:00", "23:00"),
    )


def test_build_agent_context_includes_restaurant_local_datetime(monkeypatch):
    restaurant = Restaurant.create(
        restaurant_id=RestaurantId.generate(),
        name="Restaurante Teste",
        prompt_default="",
        menu_url="https://cardapio.teste.com",
        opening_hours=_opening_hours(),
        integration_type=IntegrationType.JOIN,
        automation_type=AutomationType.BASIC,
        chave_grupo_empresarial=uuid4(),
        canal_master_id="wp-empresa-1",
        empresa_base_id="1",
        timezone="America/Cuiaba",
    )
    conversation = Conversation.create(
        restaurant_id=restaurant.id,
        customer_phone=PhoneNumber("5565999999999"),
        customer_name="João",
    )

    fixed_now = datetime(2026, 5, 2, 9, 30, tzinfo=ZoneInfo("America/Cuiaba"))
    monkeypatch.setattr(
        "tacto.interfaces.http.routes.chat._get_restaurant_current_datetime",
        lambda _tz: fixed_now,
    )
    monkeypatch.setattr(restaurant, "is_open_now", lambda: True)

    context = _build_agent_context(
        restaurant=restaurant,
        conversation=conversation,
        customer_phone="5565999999999",
        customer_name=None,
    )

    assert context.restaurant_timezone == "America/Cuiaba"
    assert context.current_weekday_pt == "sábado"
    assert context.current_date_br == "02/05/2026"
    assert context.current_time_br == "09:30"
    assert context.current_datetime_iso == "2026-05-02T09:30:00-04:00"
    assert context.customer_name == "João"


def test_build_agent_context_fail_open_when_hours_undefined(monkeypatch):
    """When the restaurant has no hours data (all days closed), the bot must treat
    it as OPEN so it never wrongly tells a customer it is closed (fail-open)."""
    restaurant = Restaurant.create(
        restaurant_id=RestaurantId.generate(),
        name="Restaurante Teste",
        prompt_default="",
        menu_url="https://cardapio.teste.com",
        opening_hours=OpeningHours.from_dict({}),  # all days closed = no data
        integration_type=IntegrationType.JOIN,
        automation_type=AutomationType.BASIC,
        chave_grupo_empresarial=uuid4(),
        canal_master_id="wp-empresa-2",
        empresa_base_id="2",
        timezone="America/Sao_Paulo",
    )
    conversation = Conversation.create(
        restaurant_id=restaurant.id,
        customer_phone=PhoneNumber("5511999999999"),
        customer_name="Ana",
    )

    # Force bypass OFF so is_open is driven by the fail-open path, not the flag.
    class _App:
        bypass_hours_check = False
        default_timezone = "America/Sao_Paulo"

    class _Settings:
        app = _App()

    monkeypatch.setattr(
        "tacto.interfaces.http.routes.chat.get_settings", lambda: _Settings()
    )

    context = _build_agent_context(
        restaurant=restaurant,
        conversation=conversation,
        customer_phone="5511999999999",
        customer_name=None,
    )

    assert context.is_open is True
