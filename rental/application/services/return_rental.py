from rental.application.ports.inbound.return_rental import (
    ReturnRentalCommand,
    ReturnRentalResult,
)
from rental.application.ports.outbound.clock import Clock
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.application.ports.outbound.notifier import (
    EquipmentSentToMaintenance,
    Notifier,
    RentalReturned,
)
from rental.application.ports.outbound.rental_repository import RentalRepository
from rental.application.ports.outbound.unit_of_work import UnitOfWork


class ReturnRentalService:
    def __init__(
        self,
        rentals: RentalRepository,
        equipment: EquipmentRepository,
        clock: Clock,
        notifier: Notifier,
        uow: UnitOfWork,
    ) -> None:
        self._rentals = rentals
        self._equipment = equipment
        self._clock = clock
        self._notifier = notifier
        self._uow = uow

    def execute(self, command: ReturnRentalCommand) -> ReturnRentalResult:
        with self._uow:
            rental = self._rentals.get(command.rental_id)
            items = self._equipment.get_many(rental.equipment_ids)
            today = self._clock.today()

            rental.close(items, today=today, damaged_ids=command.damaged_equipment_ids)

            for item in items:
                self._equipment.save(item)
            self._rentals.save(rental)
            self._uow.commit()

        self._notifier.notify(RentalReturned(rental_id=rental.id, returned_on=today))
        for item in items:
            self._notifier.notify(
                EquipmentSentToMaintenance(equipment_id=item.id, needs_repair=item.needs_repair)
            )
        return ReturnRentalResult(
            rental_id=rental.id,
            returned_on=today,
            needs_repair_ids=frozenset(item.id for item in items if item.needs_repair),
        )
