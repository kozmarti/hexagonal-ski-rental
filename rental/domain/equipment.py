from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4

from rental.domain.entity import Entity
from rental.domain.exceptions import (
    EquipmentNotAvailable,
    InvalidEquipment,
    InvalidStatusTransition,
)
from rental.domain.size import Size, SizeUnit


class EquipmentType(StrEnum):
    SKIS = "skis"
    SNOWBOARD = "snowboard"
    BOOTS = "boots"
    HELMET = "helmet"
    POLES = "poles"


class Range(StrEnum):
    DISCOVERY = "discovery"
    SPORT = "sport"
    PREMIUM = "premium"


class EquipmentStatus(StrEnum):
    AVAILABLE = "available"
    RENTED = "rented"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


RANGED_TYPES = frozenset({EquipmentType.SKIS, EquipmentType.SNOWBOARD, EquipmentType.BOOTS})


@dataclass(eq=False)
class Equipment(Entity):
    type: EquipmentType
    brand: str
    model: str
    size: Size
    range: Range | None
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    days_used: int = 0
    needs_repair: bool = False

    def __post_init__(self) -> None:
        if not self.brand.strip() or not self.model.strip():
            raise InvalidEquipment("Brand and model are required.")
        expected_unit = SizeUnit.MONDOPOINT if self.type is EquipmentType.BOOTS else SizeUnit.CM
        if self.size.unit is not expected_unit:
            raise InvalidEquipment(f"{self.type} size must be in {expected_unit}.")
        if self.type in RANGED_TYPES and self.range is None:
            raise InvalidEquipment(f"{self.type} must have a range.")
        if self.type not in RANGED_TYPES and self.range is not None:
            raise InvalidEquipment(f"{self.type} cannot have a range.")

    @classmethod
    def register(
        cls,
        type: EquipmentType,
        brand: str,
        model: str,
        size: Size,
        range: Range | None = None,
    ) -> Equipment:
        return cls(id=uuid4(), type=type, brand=brand, model=model, size=size, range=range)

    @property
    def is_available(self) -> bool:
        return self.status is EquipmentStatus.AVAILABLE

    def rent(self) -> None:
        if not self.is_available:
            raise EquipmentNotAvailable(f"Equipment {self.id} is {self.status}.")
        self.status = EquipmentStatus.RENTED

    def mark_returned(self, days: int, damaged: bool) -> None:
        """Every returned item is serviced (waxing, sharpening, drying) before its next rental."""
        self._require_status(EquipmentStatus.RENTED)
        self.days_used += days
        self.needs_repair = damaged
        self.status = EquipmentStatus.MAINTENANCE

    def complete_maintenance(self) -> None:
        self._require_status(EquipmentStatus.MAINTENANCE)
        self.needs_repair = False
        self.status = EquipmentStatus.AVAILABLE

    def retire(self) -> None:
        if self.status is EquipmentStatus.RETIRED:
            raise InvalidStatusTransition(f"Equipment {self.id} is already retired.")
        self.status = EquipmentStatus.RETIRED

    def _require_status(self, expected: EquipmentStatus) -> None:
        if self.status is not expected:
            raise InvalidStatusTransition(
                f"Equipment {self.id} is {self.status}, expected {expected}."
            )
