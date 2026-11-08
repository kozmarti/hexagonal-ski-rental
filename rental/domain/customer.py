from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from rental.domain.entity import Entity
from rental.domain.exceptions import CustomerHasRentals, InvalidCustomer
from rental.domain.size import Size, SizeUnit
from rental.domain.skill_level import SkillLevel


@dataclass(eq=False)
class Customer(Entity):
    name: str
    height_cm: int
    boot_size: Size
    skill_level: SkillLevel

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidCustomer("Name is required.")
        if self.height_cm <= 0:
            raise InvalidCustomer("Height must be positive.")
        if self.boot_size.unit is not SizeUnit.MONDOPOINT:
            raise InvalidCustomer("Boot size must be in mondopoint.")

    @classmethod
    def register(
        cls,
        name: str,
        height_cm: int,
        boot_size: Size,
        skill_level: SkillLevel,
    ) -> Customer:
        return cls(
            id=uuid4(),
            name=name,
            height_cm=height_cm,
            boot_size=boot_size,
            skill_level=skill_level,
        )

    def ensure_can_be_removed(self, has_rented: bool) -> None:
        """Only a customer who never rented can be removed: rentals are the shop's history."""
        if has_rented:
            raise CustomerHasRentals(f"{self.name} has rentals and cannot be removed.")
