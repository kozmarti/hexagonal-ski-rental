from datetime import date
from uuid import uuid4

import pytest

from rental.adapters.outbound.memory.clock import FixedClock
from rental.adapters.outbound.memory.notifier import RecordingNotifier
from rental.adapters.outbound.memory.unit_of_work import InMemoryUnitOfWork
from rental.application.ports.inbound.create_rental import CreateRentalCommand
from rental.application.ports.inbound.return_rental import ReturnRentalCommand
from rental.application.ports.outbound.notifier import EquipmentSentToMaintenance, RentalReturned
from rental.application.services.create_rental import CreateRentalService
from rental.application.services.return_rental import ReturnRentalService
from rental.domain.equipment import EquipmentStatus
from rental.domain.exceptions import RentalAlreadyReturned, RentalNotFound
from rental.domain.rental import RentalStatus
from tests.unit.factories import make_boots, make_customer, make_skis

TUESDAY = date(2026, 12, 22)
FRIDAY = date(2026, 12, 25)


def rented(shop, *items):
    """Creates a rental on Sunday, then moves the shop to Tuesday with a fresh notifier."""
    customer = make_customer()
    shop.add(customer, *items)
    result = CreateRentalService(
        shop.customers,
        shop.equipment,
        shop.rentals,
        shop.price_list,
        shop.clock,
        shop.notifier,
        shop.uow,
    ).execute(CreateRentalCommand(customer.id, tuple(item.id for item in items), FRIDAY))
    shop.clock = FixedClock(TUESDAY)
    shop.notifier = RecordingNotifier()
    shop.uow = InMemoryUnitOfWork()
    return result.rental_id


def return_rental(shop, command):
    return ReturnRentalService(
        shop.rentals, shop.equipment, shop.clock, shop.notifier, shop.uow
    ).execute(command)


def test_returned_items_all_go_to_maintenance(shop):
    skis, boots = make_skis(), make_boots()
    rental_id = rented(shop, skis, boots)

    result = return_rental(shop, ReturnRentalCommand(rental_id, frozenset({boots.id})))

    assert result.returned_on == TUESDAY
    assert result.needs_repair_ids == {boots.id}
    assert shop.rentals.get(rental_id).status is RentalStatus.RETURNED
    returned_skis, returned_boots = shop.equipment.get_many([skis.id, boots.id])
    assert returned_skis.status is EquipmentStatus.MAINTENANCE
    assert not returned_skis.needs_repair
    assert returned_boots.status is EquipmentStatus.MAINTENANCE
    assert returned_boots.needs_repair
    assert returned_skis.days_used == 3
    assert shop.uow.committed


def test_return_sends_one_notification_per_item(shop):
    skis, boots = make_skis(), make_boots()
    rental_id = rented(shop, skis, boots)

    return_rental(shop, ReturnRentalCommand(rental_id, frozenset({boots.id})))

    assert shop.notifier.sent == [
        RentalReturned(rental_id, TUESDAY),
        EquipmentSentToMaintenance(skis.id, needs_repair=False),
        EquipmentSentToMaintenance(boots.id, needs_repair=True),
    ]


def test_rental_cannot_be_returned_twice(shop):
    skis = make_skis()
    rental_id = rented(shop, skis)
    return_rental(shop, ReturnRentalCommand(rental_id))

    with pytest.raises(RentalAlreadyReturned):
        return_rental(shop, ReturnRentalCommand(rental_id))


def test_unknown_rental_is_not_found(shop):
    with pytest.raises(RentalNotFound):
        return_rental(shop, ReturnRentalCommand(uuid4()))
