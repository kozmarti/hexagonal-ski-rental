from dataclasses import dataclass
from typing import Protocol

from rental.domain.equipment import EquipmentType, Range
from rental.domain.money import Money


@dataclass(frozen=True)
class RateView:
    type: EquipmentType
    range: Range | None
    day: Money
    week: Money


class GetPriceList(Protocol):
    def execute(self) -> list[RateView]: ...
