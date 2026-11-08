"""A full rental, from registration to the end of maintenance, through the real wiring:
bootstrap.py with the Django ORM, the system clock, the static prices and the logging notifier.
"""

import logging

import pytest
from django.utils import timezone

from rental import bootstrap
from rental.application.ports.inbound.complete_maintenance import CompleteMaintenanceCommand
from rental.application.ports.inbound.create_rental import CreateRentalCommand
from rental.application.ports.inbound.register_customer import RegisterCustomerCommand
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.application.ports.inbound.return_rental import ReturnRentalCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel

pytestmark = pytest.mark.django_db


def register_skis() -> RegisterEquipmentCommand:
    return RegisterEquipmentCommand(
        type=EquipmentType.SKIS,
        brand="Rossignol",
        model="Experience 80 Ti",
        size=Size.cm(165),
        range=Range.SPORT,
    )


def test_rent_return_and_service_a_pair_of_skis(caplog):
    caplog.set_level(logging.INFO, logger="rental.notifications")
    customer = bootstrap.register_customer().execute(
        RegisterCustomerCommand(
            name="Alex Martin",
            height_cm=175,
            boot_size=Size.mondopoint("26.5"),
            skill_level=SkillLevel.INTERMEDIATE,
        )
    )
    skis = bootstrap.register_equipment().execute(register_skis())
    today = timezone.localdate()

    rental = bootstrap.create_rental().execute(
        CreateRentalCommand(customer.customer_id, (skis.equipment_id,), end_date=today)
    )
    assert rental.start_date == today
    due_back = bootstrap.get_dashboard().execute().due_back_today
    assert [view.id for view in due_back] == [rental.rental_id]

    returned = bootstrap.return_rental().execute(
        ReturnRentalCommand(rental.rental_id, frozenset({skis.equipment_id}))
    )
    assert returned.needs_repair_ids == {skis.equipment_id}
    in_maintenance = bootstrap.list_equipment_in_maintenance().execute()
    assert [view.id for view in in_maintenance] == [skis.equipment_id]

    bootstrap.complete_maintenance().execute(CompleteMaintenanceCommand(skis.equipment_id))
    assert bootstrap.get_dashboard().execute().in_maintenance == []

    assert len(caplog.messages) == 4
    assert caplog.messages[0].startswith(f"Rental {rental.rental_id} created: 1 item(s)")
    assert caplog.messages[-1] == f"Equipment {skis.equipment_id} is available again."
