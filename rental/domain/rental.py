from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID, uuid4

from rental.domain.customer import Customer
from rental.domain.entity import Entity
from rental.domain.equipment import Equipment
from rental.domain.exceptions import EquipmentNotAvailable, InvalidRental, RentalAlreadyReturned
from rental.domain.money import Money
from rental.domain.pricing import PriceList, PricingPolicy
from rental.domain.rental_period import RentalPeriod


class RentalStatus(StrEnum):
    ACTIVE = "active"
    RETURNED = "returned"


@dataclass(eq=False)
class Rental(Entity):
    customer_id: UUID
    equipment_ids: tuple[UUID, ...]
    period: RentalPeriod
    price: Money
    status: RentalStatus = RentalStatus.ACTIVE
    returned_on: date | None = None

    @classmethod
    def open(
        cls,
        customer: Customer,
        equipment: Sequence[Equipment],
        period: RentalPeriod,
        price_list: PriceList,
        today: date,
    ) -> Rental:
        if not equipment:
            raise InvalidRental("A rental needs at least one item.")
        equipment_ids = tuple(item.id for item in equipment)
        if len(set(equipment_ids)) != len(equipment_ids):
            raise InvalidRental("The same item cannot be rented twice.")
        if period.start != today:
            raise InvalidRental("A rental must start today.")
        # Check every item before renting any, so a failure leaves all items untouched.
        unavailable = [item for item in equipment if not item.is_available]
        if unavailable:
            ids = ", ".join(str(item.id) for item in unavailable)
            raise EquipmentNotAvailable(f"Not available: {ids}.")

        price = PricingPolicy().price_for(equipment, period, price_list)
        for item in equipment:
            item.rent()
        return cls(
            id=uuid4(),
            customer_id=customer.id,
            equipment_ids=equipment_ids,
            period=period,
            price=price,
        )

    def close(
        self,
        equipment: Sequence[Equipment],
        today: date,
        damaged_ids: Collection[UUID] = (),
    ) -> None:
        if self.status is RentalStatus.RETURNED:
            raise RentalAlreadyReturned(f"Rental {self.id} is already returned.")
        returned_ids = [item.id for item in equipment]
        if sorted(returned_ids) != sorted(self.equipment_ids):
            raise InvalidRental("Returned items do not match the rental.")
        if not set(damaged_ids) <= set(self.equipment_ids):
            raise InvalidRental("Damaged items must belong to the rental.")
        if today < self.period.start:
            raise InvalidRental("A rental cannot be returned before it starts.")

        days_used = (today - self.period.start).days + 1
        for item in equipment:
            item.mark_returned(days_used, damaged=item.id in damaged_ids)
        self.status = RentalStatus.RETURNED
        self.returned_on = today
