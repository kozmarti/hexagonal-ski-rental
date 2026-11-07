import pytest

from rental.adapters.outbound.memory.repositories import InMemoryCustomerRepository
from rental.adapters.outbound.memory.unit_of_work import InMemoryUnitOfWork
from rental.application.ports.inbound.register_customer import RegisterCustomerCommand
from rental.application.services.register_customer import RegisterCustomerService
from rental.domain.exceptions import InvalidCustomer
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel


def command(name="Alex Martin"):
    return RegisterCustomerCommand(
        name=name,
        height_cm=175,
        boot_size=Size.mondopoint("26.5"),
        skill_level=SkillLevel.INTERMEDIATE,
    )


def test_registered_customer_is_saved():
    customers, uow = InMemoryCustomerRepository(), InMemoryUnitOfWork()

    result = RegisterCustomerService(customers, uow).execute(command())

    saved = customers.get(result.customer_id)
    assert saved.name == "Alex Martin"
    assert saved.skill_level is SkillLevel.INTERMEDIATE
    assert uow.committed


def test_invalid_customer_is_not_saved():
    customers, uow = InMemoryCustomerRepository(), InMemoryUnitOfWork()

    with pytest.raises(InvalidCustomer):
        RegisterCustomerService(customers, uow).execute(command(name=""))

    assert not uow.committed
