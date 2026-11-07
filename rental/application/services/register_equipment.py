from rental.application.ports.inbound.register_equipment import (
    RegisterEquipmentCommand,
    RegisterEquipmentResult,
)
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.application.ports.outbound.unit_of_work import UnitOfWork
from rental.domain.equipment import Equipment


class RegisterEquipmentService:
    def __init__(self, equipment: EquipmentRepository, uow: UnitOfWork) -> None:
        self._equipment = equipment
        self._uow = uow

    def execute(self, command: RegisterEquipmentCommand) -> RegisterEquipmentResult:
        with self._uow:
            item = Equipment.register(
                type=command.type,
                brand=command.brand,
                model=command.model,
                size=command.size,
                range=command.range,
            )
            self._equipment.save(item)
            self._uow.commit()
        return RegisterEquipmentResult(equipment_id=item.id)
