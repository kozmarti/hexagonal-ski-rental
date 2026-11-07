from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size


@dataclass(frozen=True)
class RegisterEquipmentCommand:
    type: EquipmentType
    brand: str
    model: str
    size: Size
    range: Range | None = None


@dataclass(frozen=True)
class RegisterEquipmentResult:
    equipment_id: UUID


class RegisterEquipment(Protocol):
    def execute(self, command: RegisterEquipmentCommand) -> RegisterEquipmentResult: ...
