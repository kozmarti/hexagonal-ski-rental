from datetime import date

from rental.adapters.outbound.memory.clock import FixedClock
from rental.application.services.get_dashboard import GetDashboardService
from rental.domain.rental import Rental
from rental.domain.rental_period import RentalPeriod
from tests.unit.application.conftest import SUNDAY
from tests.unit.factories import (
    eur,
    make_boots,
    make_customer,
    make_helmet,
    make_price_list,
    make_skis,
)

MONDAY = date(2026, 12, 21)
WEDNESDAY = date(2026, 12, 23)
FRIDAY = date(2026, 12, 25)


def open_rental(shop, customer, items, end):
    rental = Rental.open(customer, items, RentalPeriod(SUNDAY, end), make_price_list(), SUNDAY)
    shop.add(*items)
    shop.rentals.save(rental)
    return rental


def dashboard(shop):
    return GetDashboardService(shop.rentals, shop.customers, shop.equipment, shop.clock).execute()


def test_dashboard_is_for_today(shop):
    assert dashboard(shop).today == SUNDAY


def test_active_rentals_are_listed_soonest_return_first(shop):
    customer = make_customer()
    shop.add(customer)
    skis, boots = make_skis(), make_boots()
    week = open_rental(shop, customer, [skis, boots], FRIDAY)
    one_day = open_rental(shop, customer, [make_skis()], SUNDAY)

    rentals = dashboard(shop).active_rentals

    assert [view.id for view in rentals] == [one_day.id, week.id]
    week_view = rentals[1]
    assert week_view.customer_name == "Alex Martin"
    assert [item.id for item in week_view.equipment] == [skis.id, boots.id]
    assert week_view.start_date == SUNDAY
    assert week_view.end_date == FRIDAY
    assert week_view.price == eur("180")


def test_due_back_today_only_lists_rentals_ending_today(shop):
    customer = make_customer()
    shop.add(customer)
    open_rental(shop, customer, [make_skis()], FRIDAY)
    one_day = open_rental(shop, customer, [make_skis()], SUNDAY)

    assert [view.id for view in dashboard(shop).due_back_today] == [one_day.id]


def test_overdue_rentals_are_listed_oldest_first(shop):
    customer = make_customer()
    shop.add(customer)
    one_day = open_rental(shop, customer, [make_skis()], SUNDAY)
    two_days = open_rental(shop, customer, [make_skis()], MONDAY)
    open_rental(shop, customer, [make_skis()], FRIDAY)
    shop.clock = FixedClock(WEDNESDAY)

    result = dashboard(shop)

    assert [view.id for view in result.overdue] == [one_day.id, two_days.id]
    assert len(result.active_rentals) == 3
    assert result.due_back_today == []


def test_returned_rentals_are_not_listed(shop):
    customer, skis = make_customer(), make_skis()
    shop.add(customer)
    rental = open_rental(shop, customer, [skis], SUNDAY)
    rental.close([skis], today=SUNDAY)
    shop.rentals.save(rental)

    result = dashboard(shop)

    assert result.active_rentals == []
    assert result.due_back_today == []
    assert result.overdue == []


def test_items_in_maintenance_are_listed_repairs_first(shop):
    serviced, damaged = make_boots(), make_helmet()
    for item, is_damaged in [(serviced, False), (damaged, True)]:
        item.rent()
        item.mark_returned(days=1, damaged=is_damaged)
    shop.add(serviced, damaged, make_skis())

    in_maintenance = dashboard(shop).in_maintenance

    assert [view.id for view in in_maintenance] == [damaged.id, serviced.id]
