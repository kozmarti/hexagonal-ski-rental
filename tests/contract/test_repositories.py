"""The same tests run against every adapter of the repository ports.

If both the in-memory and the Django ORM repositories pass them, the core can use
either one without noticing the difference.
"""

from dataclasses import asdict, dataclass
from datetime import date
from uuid import uuid4

import pytest

from rental.adapters.outbound.memory.repositories import (
    InMemoryCustomerRepository,
    InMemoryEquipmentRepository,
    InMemoryRentalRepository,
)
from rental.adapters.outbound.orm.repositories import (
    DjangoCustomerRepository,
    DjangoEquipmentRepository,
    DjangoRentalRepository,
)
from rental.application.ports.outbound.customer_repository import CustomerRepository
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.application.ports.outbound.rental_repository import RentalRepository
from rental.domain.equipment import EquipmentStatus, EquipmentType, Range
from rental.domain.exceptions import CustomerNotFound, EquipmentNotFound, RentalNotFound
from rental.domain.rental import Rental
from rental.domain.rental_period import RentalPeriod
from rental.domain.size import Size
from tests.unit.factories import make_boots, make_customer, make_price_list, make_skis

SUNDAY = date(2026, 12, 20)
WEDNESDAY = date(2026, 12, 23)
FRIDAY = date(2026, 12, 25)


@dataclass
class Repositories:
    equipment: EquipmentRepository
    customers: CustomerRepository
    rentals: RentalRepository


@pytest.fixture(params=["memory", pytest.param("orm", marks=pytest.mark.django_db)])
def repos(request) -> Repositories:
    if request.param == "memory":
        return Repositories(
            InMemoryEquipmentRepository(), InMemoryCustomerRepository(), InMemoryRentalRepository()
        )
    return Repositories(
        DjangoEquipmentRepository(), DjangoCustomerRepository(), DjangoRentalRepository()
    )


def same_fields(left, right) -> bool:
    """Entities are equal by id; this also checks that no field was lost on the way."""
    return asdict(left) == asdict(right)


def save_equipment(repos, *items):
    for item in items:
        repos.equipment.save(item)


def stored_rental(repos, items=None, end=FRIDAY) -> Rental:
    """Opens a rental on Sunday and saves it with its customer and items."""
    customer, items = make_customer(), items or [make_skis()]
    rental = Rental.open(customer, items, RentalPeriod(SUNDAY, end), make_price_list(), SUNDAY)
    repos.customers.save(customer)
    save_equipment(repos, *items)
    repos.rentals.save(rental)
    return rental


class TestEquipmentRepository:
    def test_saved_item_can_be_read_back_with_all_its_fields(self, repos):
        skis = make_skis()
        skis.rent()
        skis.mark_returned(days=4, damaged=True)
        save_equipment(repos, skis, make_boots())

        assert same_fields(repos.equipment.get(skis.id), skis)

    def test_changes_are_stored_only_on_save(self, repos):
        skis = make_skis()
        save_equipment(repos, skis)

        skis.rent()
        assert repos.equipment.get(skis.id).status is EquipmentStatus.AVAILABLE

        repos.equipment.save(skis)
        assert repos.equipment.get(skis.id).status is EquipmentStatus.RENTED

    def test_unknown_item_is_not_found(self, repos):
        with pytest.raises(EquipmentNotFound):
            repos.equipment.get(uuid4())

    def test_get_many_keeps_the_requested_order(self, repos):
        skis, boots = make_skis(), make_boots()
        save_equipment(repos, skis, boots)

        assert repos.equipment.get_many([boots.id, skis.id]) == [boots, skis]

    def test_get_many_reports_unknown_items(self, repos):
        skis = make_skis()
        save_equipment(repos, skis)

        with pytest.raises(EquipmentNotFound):
            repos.equipment.get_many([skis.id, uuid4()])

    def test_find_available_excludes_rented_items_and_filters(self, repos):
        sport_skis, premium_skis, boots, rented_skis = (
            make_skis(Range.SPORT),
            make_skis(Range.PREMIUM),
            make_boots(),
            make_skis(),
        )
        rented_skis.rent()
        save_equipment(repos, sport_skis, premium_skis, boots, rented_skis)

        assert set(repos.equipment.find_available()) == {sport_skis, premium_skis, boots}
        assert repos.equipment.find_available(type=EquipmentType.BOOTS) == [boots]
        assert repos.equipment.find_available(range=Range.PREMIUM) == [premium_skis]
        assert repos.equipment.find_available(size=Size.mondopoint("26.5")) == [boots]

    def test_find_in_maintenance(self, repos):
        skis, boots = make_skis(), make_boots()
        skis.rent()
        skis.mark_returned(days=1, damaged=False)
        save_equipment(repos, skis, boots)

        assert repos.equipment.find_in_maintenance() == [skis]


class TestCustomerRepository:
    def test_saved_customer_can_be_read_back_with_all_its_fields(self, repos):
        customer = make_customer()
        repos.customers.save(customer)

        assert same_fields(repos.customers.get(customer.id), customer)

    def test_unknown_customer_is_not_found(self, repos):
        with pytest.raises(CustomerNotFound):
            repos.customers.get(uuid4())

    def test_deleted_customer_is_gone(self, repos):
        customer, other = make_customer(), make_customer()
        repos.customers.save(customer)
        repos.customers.save(other)

        repos.customers.delete(customer.id)

        with pytest.raises(CustomerNotFound):
            repos.customers.get(customer.id)
        assert repos.customers.get(other.id) == other


class TestRentalRepository:
    def test_saved_rental_can_be_read_back_with_its_items_in_order(self, repos):
        skis, boots = make_skis(), make_boots()
        rental = stored_rental(repos, [skis, boots])

        loaded = repos.rentals.get(rental.id)

        assert same_fields(loaded, rental)
        assert loaded.equipment_ids == (skis.id, boots.id)

    def test_closed_rental_is_updated(self, repos):
        skis = make_skis()
        rental = stored_rental(repos, [skis])
        rental.close([skis], today=FRIDAY)
        repos.rentals.save(rental)

        assert same_fields(repos.rentals.get(rental.id), rental)

    def test_has_rentals_for_counts_active_and_returned_rentals(self, repos):
        skis = make_skis()
        rental = stored_rental(repos, [skis])
        newcomer = make_customer()
        repos.customers.save(newcomer)

        assert repos.rentals.has_rentals_for(rental.customer_id)
        rental.close([skis], today=FRIDAY)
        repos.rentals.save(rental)
        assert repos.rentals.has_rentals_for(rental.customer_id)
        assert not repos.rentals.has_rentals_for(newcomer.id)

    def test_unknown_rental_is_not_found(self, repos):
        with pytest.raises(RentalNotFound):
            repos.rentals.get(uuid4())

    def test_find_active_excludes_returned_rentals(self, repos):
        skis = make_skis()
        active, returned = stored_rental(repos), stored_rental(repos, [skis])
        returned.close([skis], today=FRIDAY)
        repos.rentals.save(returned)

        assert repos.rentals.find_active() == [active]

    def test_find_due_back_on(self, repos):
        due_wednesday = stored_rental(repos, end=WEDNESDAY)
        stored_rental(repos, end=FRIDAY)

        assert repos.rentals.find_due_back_on(WEDNESDAY) == [due_wednesday]

    def test_find_overdue(self, repos):
        due_wednesday = stored_rental(repos, end=WEDNESDAY)
        stored_rental(repos, end=FRIDAY)

        assert repos.rentals.find_overdue(WEDNESDAY) == []
        assert repos.rentals.find_overdue(date(2026, 12, 24)) == [due_wednesday]
