from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ReturnRentalCommand:
    rental_id: UUID
    damaged_equipment_ids: frozenset[UUID] = frozenset()


@dataclass(frozen=True)
class ReturnRentalResult:
    rental_id: UUID
    returned_on: date
    needs_repair_ids: frozenset[UUID]


class ReturnRental(Protocol):
    def execute(self, command: ReturnRentalCommand) -> ReturnRentalResult: ...
