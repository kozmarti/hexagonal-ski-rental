from datetime import date

import pytest

from rental.domain.equipment import EquipmentStatus
from rental.domain.exceptions import EquipmentNotAvailable, InvalidRental, RentalAlreadyReturned
from rental.domain.rental import Rental, RentalStatus
from rental.domain.rental_period import RentalPeriod
from tests.unit.factories import eur, make_boots, make_customer, make_price_list, make_skis

SUNDAY = date(2026, 12, 20)
TUESDAY = date(2026, 12, 22)
FRIDAY = date(2026, 12, 25)
WEEK = RentalPeriod(SUNDAY, FRIDAY)


def open_rental(equipment, period=WEEK, today=SUNDAY):
    return Rental.open(make_customer(), equipment, period, make_price_list(), today)


def test_opening_a_rental_rents_the_items_and_computes_the_price():
    skis, boots = make_skis(), make_boots()

    rental = open_rental([skis, boots])

    assert rental.status is RentalStatus.ACTIVE
    assert rental.equipment_ids == (skis.id, boots.id)
    assert rental.price == eur("180")
    assert skis.status is EquipmentStatus.RENTED
    assert boots.status is EquipmentStatus.RENTED


def test_rental_must_start_today():
    with pytest.raises(InvalidRental):
        open_rental([make_skis()], today=TUESDAY)


def test_rental_needs_at_least_one_item():
    with pytest.raises(InvalidRental):
        open_rental([])


def test_same_item_cannot_be_added_twice():
    skis = make_skis()

    with pytest.raises(InvalidRental):
        open_rental([skis, skis])


def test_unavailable_item_leaves_all_items_untouched():
    skis, boots = make_skis(), make_boots()
    boots.rent()

    with pytest.raises(EquipmentNotAvailable):
        open_rental([skis, boots])

    assert skis.status is EquipmentStatus.AVAILABLE


def test_closing_a_rental_sends_every_item_to_maintenance():
    skis, boots = make_skis(), make_boots()
    rental = open_rental([skis, boots])

    rental.close([skis, boots], today=TUESDAY, damaged_ids={boots.id})

    assert rental.status is RentalStatus.RETURNED
    assert rental.returned_on == TUESDAY
    assert skis.status is EquipmentStatus.MAINTENANCE
    assert boots.status is EquipmentStatus.MAINTENANCE
    assert not skis.needs_repair
    assert boots.needs_repair
    assert skis.days_used == 3


def test_rental_is_overdue_only_after_its_last_day():
    rental = open_rental([make_skis()])

    assert not rental.is_overdue(today=FRIDAY)
    assert rental.is_overdue(today=date(2026, 12, 26))


def test_returned_rental_is_never_overdue():
    skis = make_skis()
    rental = open_rental([skis])
    rental.close([skis], today=FRIDAY)

    assert not rental.is_overdue(today=date(2026, 12, 30))


def test_rental_cannot_be_closed_twice():
    skis = make_skis()
    rental = open_rental([skis])
    rental.close([skis], today=FRIDAY)

    with pytest.raises(RentalAlreadyReturned):
        rental.close([skis], today=FRIDAY)


def test_returned_items_must_match_the_rental():
    skis = make_skis()
    rental = open_rental([skis])

    with pytest.raises(InvalidRental):
        rental.close([make_skis()], today=FRIDAY)


def test_damaged_items_must_belong_to_the_rental():
    skis = make_skis()
    rental = open_rental([skis])

    with pytest.raises(InvalidRental):
        rental.close([skis], today=FRIDAY, damaged_ids={make_boots().id})
