"""The same tests run against every adapter of the PriceListRepository port:
in-memory, Django ORM (PostgreSQL) and MongoDB."""

import pytest

from rental.adapters.outbound.memory.price_list import InMemoryPriceList
from rental.adapters.outbound.mongo.price_list import MongoPriceListRepository
from rental.adapters.outbound.orm.price_list import DjangoPriceListRepository
from rental.adapters.outbound.price_list.static import StaticPriceList
from rental.domain.equipment import EquipmentType, Range
from rental.domain.pricing import Rate
from tests.unit.factories import eur

STARTING_PRICES = StaticPriceList().get()
SPORT_SKIS, HELMETS = (EquipmentType.SKIS, Range.SPORT), (EquipmentType.HELMET, None)


@pytest.fixture(params=["memory", pytest.param("orm", marks=pytest.mark.django_db), "mongo"])
def prices(request):
    if request.param == "memory":
        return InMemoryPriceList(STARTING_PRICES)
    if request.param == "mongo":
        return MongoPriceListRepository(request.getfixturevalue("mongo_context"), STARTING_PRICES)
    return DjangoPriceListRepository(STARTING_PRICES)


def test_the_starting_prices_are_used_until_prices_are_saved(prices):
    assert prices.get() == STARTING_PRICES


def test_saved_prices_are_read_back_with_every_rate(prices):
    changed = STARTING_PRICES.with_rates({SPORT_SKIS: Rate(day=eur("35"), week=eur("160"))})

    prices.save(changed)

    assert prices.get() == changed
    assert prices.get().rates[HELMETS] == STARTING_PRICES.rates[HELMETS]


def test_saving_again_replaces_the_previous_prices(prices):
    prices.save(STARTING_PRICES.with_rates({SPORT_SKIS: Rate(day=eur("35"), week=eur("160"))}))
    latest = STARTING_PRICES.with_rates({SPORT_SKIS: Rate(day=eur("33"), week=eur("150"))})

    prices.save(latest)

    assert prices.get() == latest
