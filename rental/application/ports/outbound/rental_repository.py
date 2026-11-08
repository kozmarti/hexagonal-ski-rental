from datetime import date
from typing import Protocol
from uuid import UUID

from rental.domain.rental import Rental


class RentalRepository(Protocol):
    def get(self, rental_id: UUID) -> Rental:
        """Raises RentalNotFound."""
        ...

    def save(self, rental: Rental) -> None: ...

    def has_rentals_for(self, customer_id: UUID) -> bool:
        """Whether the customer ever rented, active or returned."""
        ...

    def find_active(self) -> list[Rental]: ...

    def find_due_back_on(self, day: date) -> list[Rental]:
        """Active rentals whose last day is the given day."""
        ...

    def find_overdue(self, today: date) -> list[Rental]:
        """Active rentals whose last day is before today."""
        ...
