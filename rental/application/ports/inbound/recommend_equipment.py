from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.domain.equipment import Range
from rental.domain.size import Size


@dataclass(frozen=True)
class RecommendEquipmentQuery:
    customer_id: UUID


@dataclass(frozen=True)
class RecommendEquipmentResult:
    range: Range
    ski_length: Size
    snowboard_length: Size
    boot_size: Size
    skis: list[EquipmentView]
    snowboards: list[EquipmentView]
    boots: list[EquipmentView]


class RecommendEquipment(Protocol):
    def execute(self, query: RecommendEquipmentQuery) -> RecommendEquipmentResult: ...
