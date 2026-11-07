from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from rental.domain.money import Money


@dataclass(frozen=True)
class RentalCreated:
    rental_id: UUID
    customer_id: UUID
    equipment_ids: tuple[UUID, ...]
    price: Money


@dataclass(frozen=True)
class RentalReturned:
    rental_id: UUID
    returned_on: date


@dataclass(frozen=True)
class EquipmentSentToMaintenance:
    equipment_id: UUID
    needs_repair: bool


@dataclass(frozen=True)
class MaintenanceCompleted:
    equipment_id: UUID


type Notification = (
    RentalCreated | RentalReturned | EquipmentSentToMaintenance | MaintenanceCompleted
)


class Notifier(Protocol):
    def notify(self, notification: Notification) -> None: ...
