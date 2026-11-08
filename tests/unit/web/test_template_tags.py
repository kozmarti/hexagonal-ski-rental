from decimal import Decimal

from rental.adapters.inbound.web.templatetags.rental_tags import money, size
from rental.domain.size import Size, SizeUnit
from tests.unit.factories import eur


def test_sizes_are_shown_without_useless_decimals():
    assert size(Size(Decimal("160.0"), SizeUnit.CM)) == "160 cm"
    assert size(Size.mondopoint("26.5")) == "26.5 mondopoint"


def test_money_is_shown_with_cents_and_currency():
    assert money(eur("180")) == "180.00 EUR"
