from decimal import Decimal

import pytest

from rental.domain.exceptions import CurrencyMismatch, InvalidMoney
from rental.domain.money import Money


def test_amount_is_rounded_to_cents():
    assert Money(Decimal("10.005")).amount == Decimal("10.01")


def test_negative_amount_is_rejected():
    with pytest.raises(InvalidMoney):
        Money(Decimal("-1"))


def test_float_amount_is_rejected():
    with pytest.raises(InvalidMoney):
        Money(10.5)


def test_add_and_multiply():
    assert Money(Decimal("12.50")) + Money(Decimal("7.50")) == Money(Decimal("20"))
    assert Money(Decimal("12.50")) * 3 == Money(Decimal("37.50"))


def test_cannot_combine_different_currencies():
    with pytest.raises(CurrencyMismatch):
        _ = Money(Decimal("1"), "EUR") + Money(Decimal("1"), "CHF")
