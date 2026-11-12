from dataclasses import dataclass
from typing import Protocol

from rental.domain.equipment import EquipmentType, Range
from rental.domain.money import Money


@dataclass(frozen=True)
class RateChange:
    type: EquipmentType
    range: Range | None
    day: Money
    week: Money


@dataclass(frozen=True)
class UpdatePriceListCommand:
    changes: tuple[RateChange, ...]


@dataclass(frozen=True)
class UpdatePriceListResult:
    changed: int


class UpdatePriceList(Protocol):
    def execute(self, command: UpdatePriceListCommand) -> UpdatePriceListResult: ...
