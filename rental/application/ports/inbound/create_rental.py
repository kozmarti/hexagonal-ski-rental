from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from rental.domain.money import Money


@dataclass(frozen=True)
class CreateRentalCommand:
    """A rental always starts today, so only the last day is given."""

    customer_id: UUID
    equipment_ids: tuple[UUID, ...]
    end_date: date


@dataclass(frozen=True)
class CreateRentalResult:
    rental_id: UUID
    start_date: date
    end_date: date
    price: Money


class CreateRental(Protocol):
    def execute(self, command: CreateRentalCommand) -> CreateRentalResult: ...
