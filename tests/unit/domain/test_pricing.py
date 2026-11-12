from datetime import date, timedelta

import pytest

from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import InvalidPriceList, PriceNotFound
from rental.domain.pricing import PricingPolicy, Rate
from rental.domain.rental_period import RentalPeriod
from tests.unit.factories import eur, make_boots, make_helmet, make_price_list, make_skis

SUNDAY = date(2026, 12, 20)


def days(count: int) -> RentalPeriod:
    return RentalPeriod(SUNDAY, SUNDAY + timedelta(days=count - 1))


def price(equipment, period):
    return PricingPolicy().price_for(equipment, period, make_price_list())


# Skis: 30 per day, 140 per week.
@pytest.mark.parametrize(
    ("day_count", "expected"),
    [
        (1, "30"),
        (4, "120"),
        (5, "140"),  # 5 days would be 150: capped at the week rate
        (6, "140"),  # Sunday to Friday: one week
        (8, "200"),  # one week + two days
        (12, "280"),  # two weeks
    ],
)
def test_item_price_uses_week_rate_and_capped_days(day_count, expected):
    assert price([make_skis()], days(day_count)) == eur(expected)


def test_skis_and_boots_get_the_package_discount():
    # (140 + 60) - 10%
    assert price([make_skis(), make_boots()], days(6)) == eur("180")


def test_skis_and_helmet_are_not_a_package():
    assert price([make_skis(), make_helmet()], days(6)) == eur("165")


def test_week_rate_must_be_less_than_six_day_rates():
    with pytest.raises(InvalidPriceList):
        Rate(day=eur("30"), week=eur("180"))


def test_missing_price_is_reported():
    with pytest.raises(PriceNotFound):
        price([make_skis(Range.PREMIUM)], days(1))


def test_rates_can_be_changed_and_the_other_rates_stay():
    sport_skis, helmets = (EquipmentType.SKIS, Range.SPORT), (EquipmentType.HELMET, None)
    price_list = make_price_list()

    changed = price_list.with_rates({sport_skis: Rate(day=eur("35"), week=eur("160"))})

    assert changed.rates[sport_skis] == Rate(day=eur("35"), week=eur("160"))
    assert changed.rates[helmets] == price_list.rates[helmets]
    assert price_list.rates[sport_skis].day == eur("30")


def test_a_rate_can_never_be_added():
    # Rates are edited, never added or removed: every type and range keeps a price.
    premium_skis = (EquipmentType.SKIS, Range.PREMIUM)

    with pytest.raises(PriceNotFound):
        make_price_list().with_rates({premium_skis: Rate(eur("40"), eur("190"))})
