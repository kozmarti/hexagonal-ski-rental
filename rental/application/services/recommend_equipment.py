from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.inbound.recommend_equipment import (
    RecommendEquipmentQuery,
    RecommendEquipmentResult,
)
from rental.application.ports.outbound.customer_repository import CustomerRepository
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.domain.equipment import EquipmentType
from rental.domain.recommendation import Recommendation


class RecommendEquipmentService:
    def __init__(self, customers: CustomerRepository, equipment: EquipmentRepository) -> None:
        self._customers = customers
        self._equipment = equipment

    def execute(self, query: RecommendEquipmentQuery) -> RecommendEquipmentResult:
        recommendation = Recommendation.for_customer(self._customers.get(query.customer_id))
        return RecommendEquipmentResult(
            range=recommendation.range,
            ski_length=recommendation.ski_length,
            snowboard_length=recommendation.snowboard_length,
            boot_size=recommendation.boot_size,
            skis=self._matching(recommendation, EquipmentType.SKIS),
            snowboards=self._matching(recommendation, EquipmentType.SNOWBOARD),
            boots=self._matching(recommendation, EquipmentType.BOOTS),
        )

    def _matching(
        self, recommendation: Recommendation, equipment_type: EquipmentType
    ) -> list[EquipmentView]:
        """Available items that fit, closest size first."""
        target = recommendation.size_for(equipment_type)
        items = self._equipment.find_available(type=equipment_type, range=recommendation.range)
        fitting = [item for item in items if recommendation.fits(item)]
        fitting.sort(key=lambda item: abs(item.size.value - target.value))
        return [EquipmentView.from_entity(item) for item in fitting]
