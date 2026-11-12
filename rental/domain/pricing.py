from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.exceptions import InvalidPriceList, PriceNotFound
from rental.domain.money import Money
from rental.domain.rental_period import RentalPeriod

# A ski week is Sunday to Friday.
WEEK_DAYS = 6
PACKAGE_DISCOUNT = Decimal("0.10")
RIDE_TYPES = frozenset({EquipmentType.SKIS, EquipmentType.SNOWBOARD})


@dataclass(frozen=True)
class Rate:
    day: Money
    week: Money

    def __post_init__(self) -> None:
        if not self.week < self.day * WEEK_DAYS:
            raise InvalidPriceList(f"A week must cost less than {WEEK_DAYS} days.")


@dataclass(frozen=True)
class PriceList:
    rates: Mapping[tuple[EquipmentType, Range | None], Rate]

    def rate_for(self, equipment: Equipment) -> Rate:
        try:
            return self.rates[(equipment.type, equipment.range)]
        except KeyError:
            raise PriceNotFound(
                f"No price for {equipment.type} in range {equipment.range}."
            ) from None

    def with_rates(self, changes: Mapping[tuple[EquipmentType, Range | None], Rate]) -> PriceList:
        """A new price list with some rates changed. Rates are edited, never added or removed:
        every type and range keeps a price, so a rental never fails for lack of one."""
        unknown = [key for key in changes if key not in self.rates]
        if unknown:
            raise PriceNotFound(f"No such price to change: {unknown[0][0]} {unknown[0][1]}.")
        return PriceList({**self.rates, **changes})


class PricingPolicy:
    """Computes the price of a rental. The prices themselves come from a PriceList."""

    def price_for(
        self,
        equipment: Sequence[Equipment],
        period: RentalPeriod,
        price_list: PriceList,
    ) -> Money:
        total = Money.zero()
        for item in equipment:
            total = total + self._item_price(price_list.rate_for(item), period.days)
        if self._is_package(equipment):
            total = total * (1 - PACKAGE_DISCOUNT)
        return total

    @staticmethod
    def _item_price(rate: Rate, days: int) -> Money:
        weeks, extra_days = divmod(days, WEEK_DAYS)
        return rate.week * weeks + min(rate.day * extra_days, rate.week)

    @staticmethod
    def _is_package(equipment: Sequence[Equipment]) -> bool:
        types = {item.type for item in equipment}
        return bool(types & RIDE_TYPES) and EquipmentType.BOOTS in types
