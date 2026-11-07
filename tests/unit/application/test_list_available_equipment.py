from rental.adapters.outbound.memory.repositories import InMemoryEquipmentRepository
from rental.application.ports.inbound.list_available_equipment import (
    EquipmentView,
    ListAvailableEquipmentQuery,
)
from rental.application.services.list_available_equipment import ListAvailableEquipmentService
from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.size import Size
from tests.unit.factories import make_boots, make_skis


def repository_with(*items):
    repository = InMemoryEquipmentRepository()
    for item in items:
        repository.save(item)
    return repository


def test_lists_available_items_as_views():
    skis = make_skis()
    service = ListAvailableEquipmentService(repository_with(skis))

    views = service.execute(ListAvailableEquipmentQuery())

    assert views == [EquipmentView.from_entity(skis)]


def test_rented_items_are_not_listed():
    skis = make_skis()
    skis.rent()
    service = ListAvailableEquipmentService(repository_with(skis))

    assert service.execute(ListAvailableEquipmentQuery()) == []


def test_filters_are_passed_to_the_repository():
    sport, premium, boots = make_skis(Range.SPORT), make_skis(Range.PREMIUM), make_boots()
    service = ListAvailableEquipmentService(repository_with(sport, premium, boots))

    by_type = service.execute(ListAvailableEquipmentQuery(type=EquipmentType.BOOTS))
    by_range = service.execute(ListAvailableEquipmentQuery(range=Range.PREMIUM))
    by_size = service.execute(ListAvailableEquipmentQuery(size=Size.mondopoint("26.5")))

    assert [view.id for view in by_type] == [boots.id]
    assert [view.id for view in by_range] == [premium.id]
    assert [view.id for view in by_size] == [boots.id]


def test_items_are_sorted_by_type_then_size():
    long_skis = Equipment.register(
        EquipmentType.SKIS, "Atomic", "Redster", Size.cm(170), Range.SPORT
    )
    short_skis = make_skis()
    boots = make_boots()
    service = ListAvailableEquipmentService(repository_with(long_skis, boots, short_skis))

    views = service.execute(ListAvailableEquipmentQuery())

    assert [view.id for view in views] == [boots.id, short_skis.id, long_skis.id]
