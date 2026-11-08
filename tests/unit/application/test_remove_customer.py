from uuid import uuid4

import pytest

from rental.application.ports.inbound.remove_customer import RemoveCustomerCommand
from rental.application.services.remove_customer import RemoveCustomerService
from rental.domain.exceptions import CustomerHasRentals, CustomerNotFound
from rental.domain.rental import Rental
from rental.domain.rental_period import RentalPeriod
from tests.unit.application.conftest import SUNDAY
from tests.unit.factories import make_customer, make_price_list, make_skis


def remove(shop, customer_id):
    service = RemoveCustomerService(shop.customers, shop.rentals, shop.uow)
    return service.execute(RemoveCustomerCommand(customer_id))


def test_customer_who_never_rented_is_removed(shop):
    customer = make_customer()
    shop.add(customer)

    remove(shop, customer.id)

    with pytest.raises(CustomerNotFound):
        shop.customers.get(customer.id)
    assert shop.uow.committed


def test_customer_who_rented_is_kept(shop):
    customer, skis = make_customer(), make_skis()
    rental = Rental.open(customer, [skis], RentalPeriod(SUNDAY, SUNDAY), make_price_list(), SUNDAY)
    shop.add(customer, skis)
    shop.rentals.save(rental)

    with pytest.raises(CustomerHasRentals):
        remove(shop, customer.id)

    assert shop.customers.get(customer.id) == customer
    assert not shop.uow.committed


def test_unknown_customer_is_not_found(shop):
    with pytest.raises(CustomerNotFound):
        remove(shop, uuid4())
