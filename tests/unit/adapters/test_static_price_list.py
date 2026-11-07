import pytest

from rental.adapters.outbound.price_list.static import StaticPriceList
from rental.domain.equipment import RANGED_TYPES, Equipment, EquipmentType, Range
from rental.domain.size import Size


def item(type: EquipmentType, range: Range | None) -> Equipment:
    size = Size.mondopoint(27) if type is EquipmentType.BOOTS else Size.cm(160)
    return Equipment.register(type, "Brand", "Model", size, range)


@pytest.mark.parametrize("type", sorted(RANGED_TYPES))
@pytest.mark.parametrize("range", list(Range))
def test_every_ranged_item_has_a_price(type, range):
    StaticPriceList().get().rate_for(item(type, range))


@pytest.mark.parametrize("type", [EquipmentType.HELMET, EquipmentType.POLES])
def test_helmets_and_poles_have_a_price(type):
    StaticPriceList().get().rate_for(item(type, None))
