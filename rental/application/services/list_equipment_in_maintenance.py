from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.domain.equipment import Equipment


def maintenance_order(item: Equipment) -> tuple:
    """Items needing a repair first, then by type and size."""
    return (not item.needs_repair, item.type, item.size.value)


class ListEquipmentInMaintenanceService:
    def __init__(self, equipment: EquipmentRepository) -> None:
        self._equipment = equipment

    def execute(self) -> list[EquipmentView]:
        items = sorted(self._equipment.find_in_maintenance(), key=maintenance_order)
        return [EquipmentView.from_entity(item) for item in items]
