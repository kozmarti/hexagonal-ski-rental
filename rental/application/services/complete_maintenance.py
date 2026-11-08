from rental.application.ports.inbound.complete_maintenance import (
    CompleteMaintenanceCommand,
    CompleteMaintenanceResult,
)
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.application.ports.outbound.notifier import MaintenanceCompleted, Notifier
from rental.application.ports.outbound.unit_of_work import UnitOfWork


class CompleteMaintenanceService:
    def __init__(
        self,
        equipment: EquipmentRepository,
        notifier: Notifier,
        uow: UnitOfWork,
    ) -> None:
        self._equipment = equipment
        self._notifier = notifier
        self._uow = uow

    def execute(self, command: CompleteMaintenanceCommand) -> CompleteMaintenanceResult:
        with self._uow:
            item = self._equipment.get(command.equipment_id)
            item.complete_maintenance()
            self._equipment.save(item)
            self._uow.commit()

        self._notifier.notify(MaintenanceCompleted(equipment_id=item.id))
        return CompleteMaintenanceResult(equipment_id=item.id)
