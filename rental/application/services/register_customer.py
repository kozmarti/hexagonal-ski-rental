from rental.application.ports.inbound.register_customer import (
    RegisterCustomerCommand,
    RegisterCustomerResult,
)
from rental.application.ports.outbound.customer_repository import CustomerRepository
from rental.application.ports.outbound.unit_of_work import UnitOfWork
from rental.domain.customer import Customer


class RegisterCustomerService:
    def __init__(self, customers: CustomerRepository, uow: UnitOfWork) -> None:
        self._customers = customers
        self._uow = uow

    def execute(self, command: RegisterCustomerCommand) -> RegisterCustomerResult:
        with self._uow:
            customer = Customer.register(
                name=command.name,
                height_cm=command.height_cm,
                boot_size=command.boot_size,
                skill_level=command.skill_level,
            )
            self._customers.save(customer)
            self._uow.commit()
        return RegisterCustomerResult(customer_id=customer.id)
