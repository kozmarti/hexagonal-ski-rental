from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rental.domain.exceptions import InvalidRentalPeriod


@dataclass(frozen=True)
class RentalPeriod:
    """A rental period; both start and end days are included."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise InvalidRentalPeriod("The end date cannot be before the start date.")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def overlaps(self, other: RentalPeriod) -> bool:
        return self.start <= other.end and other.start <= self.end
