from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.size import Size


@dataclass(frozen=True)
class ListAvailableEquipmentQuery:
    type: EquipmentType | None = None
    size: Size | None = None
    range: Range | None = None


@dataclass(frozen=True)
class EquipmentView:
    """Read-only data for display; inbound adapters never get the entity itself."""

    id: UUID
    type: EquipmentType
    brand: str
    model: str
    size: Size
    range: Range | None
    days_used: int
    needs_repair: bool

    @classmethod
    def from_entity(cls, equipment: Equipment) -> EquipmentView:
        return cls(
            id=equipment.id,
            type=equipment.type,
            brand=equipment.brand,
            model=equipment.model,
            size=equipment.size,
            range=equipment.range,
            days_used=equipment.days_used,
            needs_repair=equipment.needs_repair,
        )


class ListAvailableEquipment(Protocol):
    def execute(self, query: ListAvailableEquipmentQuery) -> list[EquipmentView]: ...
