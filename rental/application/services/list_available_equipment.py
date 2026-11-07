from rental.application.ports.inbound.list_available_equipment import (
    EquipmentView,
    ListAvailableEquipmentQuery,
)
from rental.application.ports.outbound.equipment_repository import EquipmentRepository


class ListAvailableEquipmentService:
    def __init__(self, equipment: EquipmentRepository) -> None:
        self._equipment = equipment

    def execute(self, query: ListAvailableEquipmentQuery) -> list[EquipmentView]:
        items = self._equipment.find_available(type=query.type, size=query.size, range=query.range)
        items.sort(key=lambda item: (item.type, item.size.value))
        return [EquipmentView.from_entity(item) for item in items]
