from datetime import date
from uuid import uuid4

import pytest

from rental.application.ports.inbound.create_rental import CreateRentalCommand
from rental.application.ports.outbound.notifier import RentalCreated
from rental.application.services.create_rental import CreateRentalService
from rental.domain.equipment import EquipmentStatus
from rental.domain.exceptions import CustomerNotFound, EquipmentNotAvailable, InvalidRentalPeriod
from rental.domain.rental import RentalStatus
from tests.unit.application.conftest import SUNDAY
from tests.unit.factories import eur, make_boots, make_customer, make_skis

FRIDAY = date(2026, 12, 25)


def create_rental(shop, command):
    return CreateRentalService(
        shop.customers,
        shop.equipment,
        shop.rentals,
        shop.price_list,
        shop.clock,
        shop.notifier,
        shop.uow,
    ).execute(command)


def test_rental_starts_today_rents_the_items_and_notifies(shop):
    customer, skis, boots = make_customer(), make_skis(), make_boots()
    shop.add(customer, skis, boots)

    result = create_rental(shop, CreateRentalCommand(customer.id, (skis.id, boots.id), FRIDAY))

    assert result.start_date == SUNDAY
    assert result.end_date == FRIDAY
    assert result.price == eur("180")
    assert shop.rentals.get(result.rental_id).status is RentalStatus.ACTIVE
    assert shop.equipment.get(skis.id).status is EquipmentStatus.RENTED
    assert shop.equipment.get(boots.id).status is EquipmentStatus.RENTED
    assert shop.uow.committed
    assert shop.notifier.sent == [
        RentalCreated(result.rental_id, customer.id, (skis.id, boots.id), eur("180"))
    ]


def test_unknown_customer_is_rejected(shop):
    skis = make_skis()
    shop.add(skis)

    with pytest.raises(CustomerNotFound):
        create_rental(shop, CreateRentalCommand(uuid4(), (skis.id,), FRIDAY))

    assert not shop.uow.committed


def test_unavailable_item_rejects_the_whole_rental(shop):
    customer, skis, boots = make_customer(), make_skis(), make_boots()
    boots.rent()
    shop.add(customer, skis, boots)

    with pytest.raises(EquipmentNotAvailable):
        create_rental(shop, CreateRentalCommand(customer.id, (skis.id, boots.id), FRIDAY))

    assert shop.equipment.get(skis.id).status is EquipmentStatus.AVAILABLE
    assert not shop.uow.committed
    assert shop.notifier.sent == []


def test_end_date_before_today_is_rejected(shop):
    customer, skis = make_customer(), make_skis()
    shop.add(customer, skis)

    with pytest.raises(InvalidRentalPeriod):
        create_rental(shop, CreateRentalCommand(customer.id, (skis.id,), date(2026, 12, 19)))
