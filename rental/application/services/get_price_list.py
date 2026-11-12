from rental.application.ports.inbound.get_price_list import RateView
from rental.application.ports.outbound.price_list_repository import PriceListRepository
from rental.domain.equipment import EquipmentType, Range


def _order(key: tuple[EquipmentType, Range | None]) -> tuple[int, int]:
    """In the order of the enums: skis, snowboard, boots, helmet, poles; discovery to premium."""
    equipment_type, range = key
    ranges = list(Range)
    return list(EquipmentType).index(equipment_type), ranges.index(range) if range else -1


class GetPriceListService:
    def __init__(self, price_list: PriceListRepository) -> None:
        self._price_list = price_list

    def execute(self) -> list[RateView]:
        rates = self._price_list.get().rates
        return [
            RateView(type=key[0], range=key[1], day=rates[key].day, week=rates[key].week)
            for key in sorted(rates, key=_order)
        ]
