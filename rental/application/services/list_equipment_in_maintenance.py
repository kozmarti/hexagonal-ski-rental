from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.outbound.equipment_repository import EquipmentRepository


class ListEquipmentInMaintenanceService:
    def __init__(self, equipment: EquipmentRepository) -> None:
        self._equipment = equipment

    def execute(self) -> list[EquipmentView]:
        """Items needing a repair first, then by type and size."""
        items = self._equipment.find_in_maintenance()
        items.sort(key=lambda item: (not item.needs_repair, item.type, item.size.value))
        return [EquipmentView.from_entity(item) for item in items]
