import pytest

from rental.adapters.outbound.memory.price_list import InMemoryPriceList
from rental.adapters.outbound.memory.unit_of_work import InMemoryUnitOfWork
from rental.application.ports.inbound.update_price_list import RateChange, UpdatePriceListCommand
from rental.application.services.get_price_list import GetPriceListService
from rental.application.services.update_price_list import UpdatePriceListService
from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import InvalidPriceList, PriceNotFound
from rental.domain.pricing import Rate
from tests.unit.factories import eur, make_price_list

SPORT_SKIS = (EquipmentType.SKIS, Range.SPORT)


@pytest.fixture
def prices():
    return InMemoryPriceList(make_price_list())


def update(prices, uow, *changes):
    service = UpdatePriceListService(prices, uow)
    return service.execute(UpdatePriceListCommand(tuple(changes)))


def test_rates_are_listed_in_a_stable_order(prices):
    rates = GetPriceListService(prices).execute()

    assert [(rate.type, rate.range) for rate in rates] == [
        (EquipmentType.SKIS, Range.SPORT),
        (EquipmentType.BOOTS, Range.SPORT),
        (EquipmentType.HELMET, None),
    ]
    assert rates[0].day == eur("30")


def test_changed_rates_are_saved(prices):
    uow = InMemoryUnitOfWork()

    result = update(prices, uow, RateChange(*SPORT_SKIS, day=eur("35"), week=eur("160")))

    assert result.changed == 1
    assert prices.get().rates[SPORT_SKIS] == Rate(day=eur("35"), week=eur("160"))
    assert uow.committed


def test_a_week_costing_six_days_or_more_is_refused_and_nothing_is_saved(prices):
    uow = InMemoryUnitOfWork()
    good = RateChange(EquipmentType.HELMET, None, day=eur("6"), week=eur("30"))
    too_expensive = RateChange(*SPORT_SKIS, day=eur("30"), week=eur("180"))

    with pytest.raises(InvalidPriceList, match="Skis sport: A week must cost less than 6 days."):
        update(prices, uow, good, too_expensive)

    assert prices.get() == make_price_list()
    assert not uow.committed


def test_a_price_that_does_not_exist_cannot_be_added(prices):
    premium_skis = RateChange(EquipmentType.SKIS, Range.PREMIUM, day=eur("40"), week=eur("190"))

    with pytest.raises(PriceNotFound):
        update(prices, InMemoryUnitOfWork(), premium_skis)
