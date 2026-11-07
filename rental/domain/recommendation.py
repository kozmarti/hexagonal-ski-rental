from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from rental.domain.customer import Customer
from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.size import Size, SizeUnit
from rental.domain.skill_level import SkillLevel

RANGE_FOR_LEVEL = {
    SkillLevel.BEGINNER: Range.DISCOVERY,
    SkillLevel.INTERMEDIATE: Range.SPORT,
    SkillLevel.ADVANCED: Range.PREMIUM,
    SkillLevel.EXPERT: Range.PREMIUM,
}

# Centimeters taken off the customer's height.
SKI_OFFSET_CM = {
    SkillLevel.BEGINNER: 15,
    SkillLevel.INTERMEDIATE: 10,
    SkillLevel.ADVANCED: 5,
    SkillLevel.EXPERT: 0,
}
SNOWBOARD_OFFSET_CM = {
    SkillLevel.BEGINNER: 25,
    SkillLevel.INTERMEDIATE: 20,
    SkillLevel.ADVANCED: 15,
    SkillLevel.EXPERT: 15,
}

# How far an item's size may be from the recommended size and still fit.
SIZE_TOLERANCE = {
    SizeUnit.CM: Decimal("5"),
    SizeUnit.MONDOPOINT: Decimal("0.5"),
}


@dataclass(frozen=True)
class Recommendation:
    """A suggestion only: staff can rent any item to any customer."""

    range: Range
    ski_length: Size
    snowboard_length: Size
    boot_size: Size

    @classmethod
    def for_customer(cls, customer: Customer) -> Recommendation:
        level = customer.skill_level
        return cls(
            range=RANGE_FOR_LEVEL[level],
            ski_length=Size.cm(customer.height_cm - SKI_OFFSET_CM[level]),
            snowboard_length=Size.cm(customer.height_cm - SNOWBOARD_OFFSET_CM[level]),
            boot_size=customer.boot_size,
        )

    def size_for(self, type: EquipmentType) -> Size | None:
        return {
            EquipmentType.SKIS: self.ski_length,
            EquipmentType.SNOWBOARD: self.snowboard_length,
            EquipmentType.BOOTS: self.boot_size,
        }.get(type)

    def fits(self, equipment: Equipment) -> bool:
        target = self.size_for(equipment.type)
        if target is None or equipment.range is not self.range:
            return False
        if equipment.size.unit is not target.unit:
            return False
        return abs(equipment.size.value - target.value) <= SIZE_TOLERANCE[target.unit]
