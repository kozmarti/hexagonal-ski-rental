from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.size import Size


class EquipmentRepository(Protocol):
    def get(self, equipment_id: UUID) -> Equipment:
        """Raises EquipmentNotFound."""
        ...

    def get_many(self, equipment_ids: Sequence[UUID]) -> list[Equipment]:
        """Returns the items in the given order. Raises EquipmentNotFound."""
        ...

    def save(self, equipment: Equipment) -> None: ...

    def find_available(
        self,
        type: EquipmentType | None = None,
        size: Size | None = None,
        range: Range | None = None,
    ) -> list[Equipment]: ...

    def find_in_maintenance(self) -> list[Equipment]: ...
