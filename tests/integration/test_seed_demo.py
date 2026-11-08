from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from rental import bootstrap
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipmentQuery

pytestmark = pytest.mark.django_db


def seed() -> str:
    output = StringIO()
    call_command("seed_demo", stdout=output)
    return output.getvalue()


def test_demo_data_fills_every_dashboard_section():
    assert "Demo data created: 37 items, 5 customers, 5 rentals." in seed()

    dashboard = bootstrap.get_dashboard().execute()
    available = bootstrap.list_available_equipment().execute(ListAvailableEquipmentQuery())

    assert len(dashboard.active_rentals) == 3
    assert len(dashboard.due_back_today) == 1
    assert len(dashboard.overdue) == 1
    assert len(dashboard.in_maintenance) == 4
    assert sum(item.needs_repair for item in dashboard.in_maintenance) == 1
    assert len(available) == 37 - 8 - 4


def test_seed_refuses_a_database_that_already_has_data():
    seed()

    with pytest.raises(CommandError, match="already has data"):
        seed()
