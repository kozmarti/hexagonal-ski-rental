from rental.application.ports.inbound.remove_customer import (
    RemoveCustomerCommand,
    RemoveCustomerResult,
)
from rental.application.ports.outbound.customer_repository import CustomerRepository
from rental.application.ports.outbound.rental_repository import RentalRepository
from rental.application.ports.outbound.unit_of_work import UnitOfWork


class RemoveCustomerService:
    def __init__(
        self,
        customers: CustomerRepository,
        rentals: RentalRepository,
        uow: UnitOfWork,
    ) -> None:
        self._customers = customers
        self._rentals = rentals
        self._uow = uow

    def execute(self, command: RemoveCustomerCommand) -> RemoveCustomerResult:
        with self._uow:
            customer = self._customers.get(command.customer_id)
            customer.ensure_can_be_removed(self._rentals.has_rentals_for(customer.id))
            self._customers.delete(customer.id)
            self._uow.commit()
        return RemoveCustomerResult(customer_id=customer.id)
