import pytest

from rental.adapters.outbound.memory.repositories import InMemoryEquipmentRepository
from rental.adapters.outbound.memory.unit_of_work import InMemoryUnitOfWork
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.application.services.register_equipment import RegisterEquipmentService
from rental.domain.equipment import EquipmentStatus, EquipmentType, Range
from rental.domain.exceptions import InvalidEquipment
from rental.domain.size import Size

SKIS = RegisterEquipmentCommand(
    type=EquipmentType.SKIS,
    brand="Rossignol",
    model="Experience 80 Ti",
    size=Size.cm(160),
    range=Range.SPORT,
)


@pytest.fixture
def equipment():
    return InMemoryEquipmentRepository()


@pytest.fixture
def uow():
    return InMemoryUnitOfWork()


def test_registered_equipment_is_saved_as_available(equipment, uow):
    result = RegisterEquipmentService(equipment, uow).execute(SKIS)

    saved = equipment.get(result.equipment_id)
    assert saved.type is EquipmentType.SKIS
    assert saved.range is Range.SPORT
    assert saved.status is EquipmentStatus.AVAILABLE
    assert uow.committed


def test_invalid_equipment_is_not_saved(equipment, uow):
    helmet_with_range = RegisterEquipmentCommand(
        type=EquipmentType.HELMET,
        brand="Giro",
        model="Ledge",
        size=Size.cm(58),
        range=Range.PREMIUM,
    )

    with pytest.raises(InvalidEquipment):
        RegisterEquipmentService(equipment, uow).execute(helmet_with_range)

    assert equipment.find_available() == []
    assert not uow.committed
