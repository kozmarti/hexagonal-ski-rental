from dataclasses import dataclass, field
from datetime import date

import pytest

from rental.adapters.outbound.memory.clock import FixedClock
from rental.adapters.outbound.memory.notifier import RecordingNotifier
from rental.adapters.outbound.memory.repositories import (
    InMemoryCustomerRepository,
    InMemoryEquipmentRepository,
    InMemoryRentalRepository,
)
from rental.adapters.outbound.memory.unit_of_work import InMemoryUnitOfWork
from rental.domain.customer import Customer
from rental.domain.equipment import Equipment
from rental.domain.pricing import PriceList
from tests.unit.factories import make_price_list

SUNDAY = date(2026, 12, 20)


class FactoryPriceList:
    """Uses the test prices from the factories, independent of the real shop prices."""

    def get(self) -> PriceList:
        return make_price_list()


@dataclass
class Shop:
    """Every outbound port plugged into an in-memory adapter."""

    customers: InMemoryCustomerRepository = field(default_factory=InMemoryCustomerRepository)
    equipment: InMemoryEquipmentRepository = field(default_factory=InMemoryEquipmentRepository)
    rentals: InMemoryRentalRepository = field(default_factory=InMemoryRentalRepository)
    price_list: FactoryPriceList = field(default_factory=FactoryPriceList)
    clock: FixedClock = field(default_factory=lambda: FixedClock(SUNDAY))
    notifier: RecordingNotifier = field(default_factory=RecordingNotifier)
    uow: InMemoryUnitOfWork = field(default_factory=InMemoryUnitOfWork)

    def add(self, *entities: Customer | Equipment) -> None:
        for entity in entities:
            if isinstance(entity, Customer):
                self.customers.save(entity)
            else:
                self.equipment.save(entity)


@pytest.fixture
def shop() -> Shop:
    return Shop()
