from collections.abc import Sequence
from copy import deepcopy
from datetime import date
from uuid import UUID

from rental.domain.customer import Customer
from rental.domain.equipment import Equipment, EquipmentStatus, EquipmentType, Range
from rental.domain.exceptions import CustomerNotFound, EquipmentNotFound, RentalNotFound
from rental.domain.rental import Rental, RentalStatus
from rental.domain.size import Size

# Every read and write is a copy, like a real database: a change made to an entity
# is only stored when save() is called.


class InMemoryEquipmentRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Equipment] = {}

    def get(self, equipment_id: UUID) -> Equipment:
        try:
            return deepcopy(self._items[equipment_id])
        except KeyError:
            raise EquipmentNotFound(f"Equipment {equipment_id} not found.") from None

    def get_many(self, equipment_ids: Sequence[UUID]) -> list[Equipment]:
        return [self.get(equipment_id) for equipment_id in equipment_ids]

    def save(self, equipment: Equipment) -> None:
        self._items[equipment.id] = deepcopy(equipment)

    def find_available(
        self,
        type: EquipmentType | None = None,
        size: Size | None = None,
        range: Range | None = None,
    ) -> list[Equipment]:
        return [
            deepcopy(item)
            for item in self._items.values()
            if item.is_available
            and (type is None or item.type is type)
            and (size is None or item.size == size)
            and (range is None or item.range is range)
        ]

    def find_in_maintenance(self) -> list[Equipment]:
        return [
            deepcopy(item)
            for item in self._items.values()
            if item.status is EquipmentStatus.MAINTENANCE
        ]


class InMemoryCustomerRepository:
    def __init__(self) -> None:
        self._customers: dict[UUID, Customer] = {}

    def get(self, customer_id: UUID) -> Customer:
        try:
            return deepcopy(self._customers[customer_id])
        except KeyError:
            raise CustomerNotFound(f"Customer {customer_id} not found.") from None

    def save(self, customer: Customer) -> None:
        self._customers[customer.id] = deepcopy(customer)


class InMemoryRentalRepository:
    def __init__(self) -> None:
        self._rentals: dict[UUID, Rental] = {}

    def get(self, rental_id: UUID) -> Rental:
        try:
            return deepcopy(self._rentals[rental_id])
        except KeyError:
            raise RentalNotFound(f"Rental {rental_id} not found.") from None

    def save(self, rental: Rental) -> None:
        self._rentals[rental.id] = deepcopy(rental)

    def find_active(self) -> list[Rental]:
        return [
            deepcopy(rental)
            for rental in self._rentals.values()
            if rental.status is RentalStatus.ACTIVE
        ]

    def find_due_back_on(self, day: date) -> list[Rental]:
        return [rental for rental in self.find_active() if rental.period.end == day]

    def find_overdue(self, today: date) -> list[Rental]:
        return [rental for rental in self.find_active() if rental.is_overdue(today)]
