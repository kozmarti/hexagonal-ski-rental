"""The MongoDB unit of work: a real transaction on the replica set."""

import pytest

from rental.adapters.outbound.mongo.repositories import (
    MongoEquipmentRepository,
    MongoRentalRepository,
)
from rental.adapters.outbound.mongo.unit_of_work import MongoUnitOfWork
from rental.domain.rental import Rental
from rental.domain.rental_period import RentalPeriod
from tests.unit.application.conftest import SUNDAY
from tests.unit.factories import make_customer, make_price_list, make_skis


def test_changes_are_kept_after_commit(mongo_context):
    repository, skis = MongoEquipmentRepository(mongo_context), make_skis()

    with MongoUnitOfWork(mongo_context) as uow:
        repository.save(skis)
        uow.commit()

    assert repository.get(skis.id) == skis


def test_changes_are_rolled_back_without_commit(mongo_context):
    repository = MongoEquipmentRepository(mongo_context)

    with MongoUnitOfWork(mongo_context):
        repository.save(make_skis())

    assert repository.find_available() == []


def test_changes_are_rolled_back_on_error(mongo_context):
    repository = MongoEquipmentRepository(mongo_context)

    with pytest.raises(RuntimeError), MongoUnitOfWork(mongo_context) as uow:
        repository.save(make_skis())
        uow.commit()
        raise RuntimeError("something failed after the commit call")

    assert repository.find_available() == []


def test_a_rental_and_its_rented_items_are_saved_together_or_not_at_all(mongo_context):
    equipment = MongoEquipmentRepository(mongo_context)
    rentals = MongoRentalRepository(mongo_context)
    skis = make_skis()
    equipment.save(skis)
    period = RentalPeriod(SUNDAY, SUNDAY)
    rental = Rental.open(make_customer(), [skis], period, make_price_list(), SUNDAY)

    with pytest.raises(RuntimeError), MongoUnitOfWork(mongo_context):
        equipment.save(skis)
        rentals.save(rental)
        raise RuntimeError("the shop's network went down")

    assert equipment.find_available() == [skis]
    assert rentals.find_active() == []
