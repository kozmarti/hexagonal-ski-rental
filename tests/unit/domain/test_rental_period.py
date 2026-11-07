from datetime import date

import pytest

from rental.domain.exceptions import InvalidRentalPeriod
from rental.domain.rental_period import RentalPeriod

SUNDAY = date(2026, 12, 20)
FRIDAY = date(2026, 12, 25)


def test_start_and_end_days_are_included():
    assert RentalPeriod(SUNDAY, SUNDAY).days == 1
    assert RentalPeriod(SUNDAY, FRIDAY).days == 6


def test_end_before_start_is_rejected():
    with pytest.raises(InvalidRentalPeriod):
        RentalPeriod(FRIDAY, SUNDAY)


def test_overlapping_periods():
    week = RentalPeriod(SUNDAY, FRIDAY)

    assert week.overlaps(RentalPeriod(FRIDAY, date(2026, 12, 27)))
    assert not week.overlaps(RentalPeriod(date(2026, 12, 26), date(2026, 12, 27)))
