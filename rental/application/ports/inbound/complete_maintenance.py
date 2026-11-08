from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CompleteMaintenanceCommand:
    equipment_id: UUID


@dataclass(frozen=True)
class CompleteMaintenanceResult:
    equipment_id: UUID


class CompleteMaintenance(Protocol):
    def execute(self, command: CompleteMaintenanceCommand) -> CompleteMaintenanceResult: ...
