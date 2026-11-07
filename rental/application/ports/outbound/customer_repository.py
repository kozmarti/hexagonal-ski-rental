from typing import Protocol
from uuid import UUID

from rental.domain.customer import Customer


class CustomerRepository(Protocol):
    def get(self, customer_id: UUID) -> Customer:
        """Raises CustomerNotFound."""
        ...

    def save(self, customer: Customer) -> None: ...
