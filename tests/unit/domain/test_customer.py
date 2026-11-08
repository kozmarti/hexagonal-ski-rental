import pytest

from rental.domain.customer import Customer
from rental.domain.exceptions import CustomerHasRentals, InvalidCustomer
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel


def test_registered_customer_gets_an_id():
    customer = Customer.register("Alex Martin", 175, Size.mondopoint(27), SkillLevel.EXPERT)

    assert customer.id is not None
    assert customer.skill_level is SkillLevel.EXPERT


def test_name_is_required():
    with pytest.raises(InvalidCustomer):
        Customer.register("", 175, Size.mondopoint(27), SkillLevel.BEGINNER)


def test_height_must_be_positive():
    with pytest.raises(InvalidCustomer):
        Customer.register("Alex Martin", 0, Size.mondopoint(27), SkillLevel.BEGINNER)


def test_customer_who_never_rented_can_be_removed():
    customer = Customer.register("Alex Martin", 175, Size.mondopoint(27), SkillLevel.EXPERT)

    customer.ensure_can_be_removed(has_rented=False)


def test_customer_who_rented_cannot_be_removed():
    customer = Customer.register("Alex Martin", 175, Size.mondopoint(27), SkillLevel.EXPERT)

    with pytest.raises(CustomerHasRentals, match="Alex Martin has rentals"):
        customer.ensure_can_be_removed(has_rented=True)


def test_boot_size_must_be_mondopoint():
    with pytest.raises(InvalidCustomer):
        Customer.register("Alex Martin", 175, Size.cm(27), SkillLevel.BEGINNER)
