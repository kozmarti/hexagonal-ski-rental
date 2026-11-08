"""The group import with the real services, plugged into the in-memory adapters."""

from datetime import date

import pytest

from rental.adapters.inbound.csv_import.importer import GroupUseCases, import_group, parse
from rental.application.services.create_rental import CreateRentalService
from rental.application.services.list_available_equipment import ListAvailableEquipmentService
from rental.application.services.recommend_equipment import RecommendEquipmentService
from rental.application.services.register_customer import RegisterCustomerService
from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.size import Size
from tests.unit.application.conftest import Shop
from tests.unit.factories import make_helmet

FRIDAY = date(2026, 12, 25)
HEADER = "name,height_cm,boot_size,level,board,helmet"


def wired(shop: Shop) -> GroupUseCases:
    return GroupUseCases(
        register_customer=lambda: RegisterCustomerService(shop.customers, shop.uow),
        recommend_equipment=lambda: RecommendEquipmentService(shop.customers, shop.equipment),
        list_available_equipment=lambda: ListAvailableEquipmentService(shop.equipment),
        create_rental=lambda: CreateRentalService(
            shop.customers,
            shop.equipment,
            shop.rentals,
            shop.price_list,
            shop.clock,
            shop.notifier,
            shop.uow,
        ),
    )


def skis(length: int) -> Equipment:
    return Equipment.register(EquipmentType.SKIS, "Atomic", "Redster", Size.cm(length), Range.SPORT)


def boots() -> Equipment:
    return Equipment.register(
        EquipmentType.BOOTS, "Salomon", "S/Pro", Size.mondopoint("26.5"), Range.SPORT
    )


@pytest.fixture
def shop() -> Shop:
    return Shop()


def import_csv(shop: Shop, *lines: str):
    return import_group(parse("\n".join([HEADER, *lines])), FRIDAY, wired(shop))


def test_each_child_gets_their_own_closest_fitting_equipment(shop):
    long_skis, short_skis, helmet = skis(165), skis(160), make_helmet()
    shop.add(long_skis, short_skis, boots(), boots(), helmet)

    first, second = import_csv(
        shop,
        "Emma,175,26.5,intermediate,skis,yes",
        "Lucas,175,26.5,intermediate,skis,no",
    )

    assert [item.id for item in first.items][0::2] == [long_skis.id, helmet.id]
    assert second.items[0].id == short_skis.id
    assert first.price and second.price
    assert len(shop.rentals.find_active()) == 2


def test_a_child_who_cannot_be_equipped_does_not_stop_the_others(shop):
    shop.add(skis(165), boots())

    small, emma = import_csv(
        shop,
        "Inès,150,23,intermediate,skis,no",
        "Emma,175,26.5,intermediate,skis,no",
    )

    assert small.rental_id is None
    assert small.error == "No available skis in a fitting size and range."
    assert small.customer_id is not None
    assert emma.rental_id is not None


def test_a_missing_helmet_is_reported(shop):
    shop.add(skis(165), boots())

    (line,) = import_csv(shop, "Emma,175,26.5,intermediate,skis,yes")

    assert line.error == "No helmet available."
    assert shop.rentals.find_active() == []


def test_business_errors_from_the_core_are_reported_per_child(shop):
    shop.add(skis(165), boots())
    members = parse(f"{HEADER}\nEmma,175,26.5,intermediate,skis,no")

    (line,) = import_group(members, date(2026, 12, 1), wired(shop))

    assert line.rental_id is None
    assert "end date" in line.error
