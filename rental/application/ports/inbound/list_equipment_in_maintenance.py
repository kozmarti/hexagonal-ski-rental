from typing import Protocol

from rental.application.ports.inbound.list_available_equipment import EquipmentView


class ListEquipmentInMaintenance(Protocol):
    def execute(self) -> list[EquipmentView]: ...
