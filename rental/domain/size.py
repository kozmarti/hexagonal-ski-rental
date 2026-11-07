from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from rental.domain.exceptions import InvalidSize


class SizeUnit(StrEnum):
    CM = "cm"
    MONDOPOINT = "mondopoint"


@dataclass(frozen=True)
class Size:
    value: Decimal
    unit: SizeUnit

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise InvalidSize("Size must be positive.")

    @classmethod
    def cm(cls, value: int | str | Decimal) -> Size:
        return cls(Decimal(value), SizeUnit.CM)

    @classmethod
    def mondopoint(cls, value: int | str | Decimal) -> Size:
        return cls(Decimal(value), SizeUnit.MONDOPOINT)
