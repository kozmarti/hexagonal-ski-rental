import pytest
from django.utils import timezone

from rental import bootstrap
from rental.adapters.outbound.clock import SystemClock
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipmentQuery
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size

pytestmark = pytest.mark.django_db


def test_registered_equipment_is_listed_through_the_real_adapters():
    command = RegisterEquipmentCommand(
        type=EquipmentType.SKIS,
        brand="Rossignol",
        model="Experience 80 Ti",
        size=Size.cm(160),
        range=Range.SPORT,
    )

    result = bootstrap.register_equipment().execute(command)
    views = bootstrap.list_available_equipment().execute(ListAvailableEquipmentQuery())

    assert [view.id for view in views] == [result.equipment_id]


def test_empty_dashboard_is_for_today():
    dashboard = bootstrap.get_dashboard().execute()

    assert dashboard.today == timezone.localdate()
    assert dashboard.active_rentals == []


def test_system_clock_uses_the_shop_time_zone():
    assert SystemClock().today() == timezone.localdate()
