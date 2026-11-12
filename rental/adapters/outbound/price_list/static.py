from decimal import Decimal

from rental.domain.equipment import EquipmentType, Range
from rental.domain.money import Money
from rental.domain.pricing import PriceList, Rate


def _rate(day: str, week: str) -> Rate:
    return Rate(day=Money(Decimal(day)), week=Money(Decimal(week)))


PRICES = {
    (EquipmentType.SKIS, Range.DISCOVERY): _rate("22", "115"),
    (EquipmentType.SKIS, Range.SPORT): _rate("30", "140"),
    (EquipmentType.SKIS, Range.PREMIUM): _rate("40", "190"),
    (EquipmentType.SNOWBOARD, Range.DISCOVERY): _rate("22", "115"),
    (EquipmentType.SNOWBOARD, Range.SPORT): _rate("30", "140"),
    (EquipmentType.SNOWBOARD, Range.PREMIUM): _rate("38", "180"),
    (EquipmentType.BOOTS, Range.DISCOVERY): _rate("10", "50"),
    (EquipmentType.BOOTS, Range.SPORT): _rate("14", "70"),
    (EquipmentType.BOOTS, Range.PREMIUM): _rate("18", "90"),
    (EquipmentType.HELMET, None): _rate("6", "30"),
    (EquipmentType.POLES, None): _rate("4", "20"),
}


class StaticPriceList:
    """The shop's starting prices. The database price lists use them until prices are first
    saved; StaticPriceList itself cannot be edited."""

    def get(self) -> PriceList:
        return PriceList(PRICES)
