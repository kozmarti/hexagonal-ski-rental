from rental.application.ports.inbound.create_rental import (
    CreateRentalCommand,
    CreateRentalResult,
)
from rental.application.ports.outbound.clock import Clock
from rental.application.ports.outbound.customer_repository import CustomerRepository
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.application.ports.outbound.notifier import Notifier, RentalCreated
from rental.application.ports.outbound.price_list_repository import PriceListRepository
from rental.application.ports.outbound.rental_repository import RentalRepository
from rental.application.ports.outbound.unit_of_work import UnitOfWork
from rental.domain.rental import Rental
from rental.domain.rental_period import RentalPeriod


class CreateRentalService:
    def __init__(
        self,
        customers: CustomerRepository,
        equipment: EquipmentRepository,
        rentals: RentalRepository,
        price_list: PriceListRepository,
        clock: Clock,
        notifier: Notifier,
        uow: UnitOfWork,
    ) -> None:
        self._customers = customers
        self._equipment = equipment
        self._rentals = rentals
        self._price_list = price_list
        self._clock = clock
        self._notifier = notifier
        self._uow = uow

    def execute(self, command: CreateRentalCommand) -> CreateRentalResult:
        with self._uow:
            customer = self._customers.get(command.customer_id)
            items = self._equipment.get_many(command.equipment_ids)
            today = self._clock.today()

            rental = Rental.open(
                customer=customer,
                equipment=items,
                period=RentalPeriod(today, command.end_date),
                price_list=self._price_list.get(),
                today=today,
            )

            for item in items:
                self._equipment.save(item)
            self._rentals.save(rental)
            self._uow.commit()

        self._notifier.notify(
            RentalCreated(
                rental_id=rental.id,
                customer_id=rental.customer_id,
                equipment_ids=rental.equipment_ids,
                price=rental.price,
            )
        )
        return CreateRentalResult(
            rental_id=rental.id,
            start_date=rental.period.start,
            end_date=rental.period.end,
            price=rental.price,
        )
