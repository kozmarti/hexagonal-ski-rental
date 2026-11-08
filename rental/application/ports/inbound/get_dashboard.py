from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.domain.money import Money


@dataclass(frozen=True)
class RentalView:
    """Read-only data for display; inbound adapters never get the entity itself."""

    id: UUID
    customer_id: UUID
    customer_name: str
    equipment: list[EquipmentView]
    start_date: date
    end_date: date
    price: Money


@dataclass(frozen=True)
class Dashboard:
    today: date
    active_rentals: list[RentalView]
    due_back_today: list[RentalView]
    overdue: list[RentalView]
    in_maintenance: list[EquipmentView]


class GetDashboard(Protocol):
    def execute(self) -> Dashboard: ...
