from datetime import date
from uuid import uuid4

import pytest

from rental.adapters.outbound.memory.repositories import (
    InMemoryCustomerRepository,
    InMemoryEquipmentRepository,
    InMemoryRentalRepository,
)
from rental.domain.equipment import EquipmentStatus, EquipmentType, Range
from rental.domain.exceptions import CustomerNotFound, EquipmentNotFound, RentalNotFound
from rental.domain.rental import Rental
from rental.domain.rental_period import RentalPeriod
from rental.domain.size import Size
from tests.unit.factories import make_boots, make_customer, make_price_list, make_skis

SUNDAY = date(2026, 12, 20)
WEDNESDAY = date(2026, 12, 23)
FRIDAY = date(2026, 12, 25)


def saved(repository, *entities):
    for entity in entities:
        repository.save(entity)
    return repository


def open_rental(equipment=None, end=FRIDAY):
    equipment = equipment or [make_skis()]
    return Rental.open(
        make_customer(), equipment, RentalPeriod(SUNDAY, end), make_price_list(), SUNDAY
    )


class TestEquipmentRepository:
    def test_saved_item_can_be_read_back(self):
        skis = make_skis()
        repository = saved(InMemoryEquipmentRepository(), skis)

        assert repository.get(skis.id) == skis

    def test_changes_are_stored_only_on_save(self):
        skis = make_skis()
        repository = saved(InMemoryEquipmentRepository(), skis)

        skis.rent()
        assert repository.get(skis.id).status is EquipmentStatus.AVAILABLE

        repository.save(skis)
        assert repository.get(skis.id).status is EquipmentStatus.RENTED

    def test_unknown_item_is_not_found(self):
        with pytest.raises(EquipmentNotFound):
            InMemoryEquipmentRepository().get(uuid4())

    def test_get_many_keeps_the_requested_order(self):
        skis, boots = make_skis(), make_boots()
        repository = saved(InMemoryEquipmentRepository(), skis, boots)

        assert repository.get_many([boots.id, skis.id]) == [boots, skis]

    def test_find_available_excludes_rented_items_and_filters(self):
        sport_skis, premium_skis, boots, rented_skis = (
            make_skis(Range.SPORT),
            make_skis(Range.PREMIUM),
            make_boots(),
            make_skis(),
        )
        rented_skis.rent()
        repository = saved(
            InMemoryEquipmentRepository(), sport_skis, premium_skis, boots, rented_skis
        )

        assert set(repository.find_available()) == {sport_skis, premium_skis, boots}
        assert repository.find_available(type=EquipmentType.BOOTS) == [boots]
        assert repository.find_available(range=Range.PREMIUM) == [premium_skis]
        assert repository.find_available(size=Size.mondopoint("26.5")) == [boots]

    def test_find_in_maintenance(self):
        skis, boots = make_skis(), make_boots()
        skis.rent()
        skis.mark_returned(days=1, damaged=False)
        repository = saved(InMemoryEquipmentRepository(), skis, boots)

        assert repository.find_in_maintenance() == [skis]


class TestCustomerRepository:
    def test_saved_customer_can_be_read_back(self):
        customer = make_customer()
        repository = saved(InMemoryCustomerRepository(), customer)

        assert repository.get(customer.id) == customer

    def test_unknown_customer_is_not_found(self):
        with pytest.raises(CustomerNotFound):
            InMemoryCustomerRepository().get(uuid4())


class TestRentalRepository:
    def test_saved_rental_can_be_read_back(self):
        rental = open_rental()
        repository = saved(InMemoryRentalRepository(), rental)

        assert repository.get(rental.id) == rental

    def test_unknown_rental_is_not_found(self):
        with pytest.raises(RentalNotFound):
            InMemoryRentalRepository().get(uuid4())

    def test_find_active_excludes_returned_rentals(self):
        skis = make_skis()
        active, returned = open_rental(), open_rental([skis])
        returned.close([skis], today=FRIDAY)
        repository = saved(InMemoryRentalRepository(), active, returned)

        assert repository.find_active() == [active]

    def test_find_due_back_on(self):
        due_wednesday, due_friday = open_rental(end=WEDNESDAY), open_rental(end=FRIDAY)
        repository = saved(InMemoryRentalRepository(), due_wednesday, due_friday)

        assert repository.find_due_back_on(WEDNESDAY) == [due_wednesday]

    def test_find_overdue(self):
        due_wednesday, due_friday = open_rental(end=WEDNESDAY), open_rental(end=FRIDAY)
        repository = saved(InMemoryRentalRepository(), due_wednesday, due_friday)

        assert repository.find_overdue(WEDNESDAY) == []
        assert repository.find_overdue(date(2026, 12, 24)) == [due_wednesday]
