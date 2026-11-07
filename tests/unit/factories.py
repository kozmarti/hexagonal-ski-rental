from decimal import Decimal

from rental.domain.customer import Customer
from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.money import Money
from rental.domain.pricing import PriceList, Rate
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel


def eur(amount: str) -> Money:
    return Money(Decimal(amount))


def make_skis(range: Range = Range.SPORT) -> Equipment:
    return Equipment.register(
        EquipmentType.SKIS, "Rossignol", "Experience 80 Ti", Size.cm(160), range
    )


def make_boots(range: Range = Range.SPORT) -> Equipment:
    return Equipment.register(
        EquipmentType.BOOTS, "Salomon", "S/Pro", Size.mondopoint("26.5"), range
    )


def make_helmet() -> Equipment:
    return Equipment.register(EquipmentType.HELMET, "Giro", "Ledge", Size.cm(58))


def make_customer() -> Customer:
    return Customer.register("Alex Martin", 175, Size.mondopoint("26.5"), SkillLevel.INTERMEDIATE)


def make_price_list() -> PriceList:
    return PriceList(
        {
            (EquipmentType.SKIS, Range.SPORT): Rate(day=eur("30"), week=eur("140")),
            (EquipmentType.BOOTS, Range.SPORT): Rate(day=eur("12"), week=eur("60")),
            (EquipmentType.HELMET, None): Rate(day=eur("5"), week=eur("25")),
        }
    )
