from uuid import uuid4

import pytest

from rental.application.ports.inbound.recommend_equipment import RecommendEquipmentQuery
from rental.application.services.recommend_equipment import RecommendEquipmentService
from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.exceptions import CustomerNotFound
from rental.domain.size import Size
from tests.unit.factories import make_customer


def skis(length: int, range: Range = Range.SPORT) -> Equipment:
    return Equipment.register(EquipmentType.SKIS, "Brand", "Model", Size.cm(length), range)


def boots(size: str) -> Equipment:
    return Equipment.register(
        EquipmentType.BOOTS, "Brand", "Model", Size.mondopoint(size), Range.SPORT
    )


def recommend(shop, customer_id):
    service = RecommendEquipmentService(shop.customers, shop.equipment)
    return service.execute(RecommendEquipmentQuery(customer_id))


def test_recommends_range_and_sizes_for_the_customer(shop):
    customer = make_customer()  # 175 cm, intermediate, boots 26.5
    shop.add(customer)

    result = recommend(shop, customer.id)

    assert result.range is Range.SPORT
    assert result.ski_length == Size.cm(165)
    assert result.snowboard_length == Size.cm(155)
    assert result.boot_size == Size.mondopoint("26.5")


def test_lists_available_items_that_fit_closest_first(shop):
    customer = make_customer()
    fitting_far, fitting_exact, too_long = skis(170), skis(165), skis(180)
    wrong_range, rented = skis(165, Range.PREMIUM), skis(165)
    rented.rent()
    good_boots, big_boots = boots("26.5"), boots("28")
    shop.add(customer, fitting_far, fitting_exact, too_long, wrong_range, rented)
    shop.add(good_boots, big_boots)

    result = recommend(shop, customer.id)

    assert [view.id for view in result.skis] == [fitting_exact.id, fitting_far.id]
    assert [view.id for view in result.boots] == [good_boots.id]
    assert result.snowboards == []


def test_unknown_customer_is_not_found(shop):
    with pytest.raises(CustomerNotFound):
        recommend(shop, uuid4())
