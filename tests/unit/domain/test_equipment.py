import pytest

from rental.domain.equipment import Equipment, EquipmentStatus, EquipmentType, Range
from rental.domain.exceptions import (
    EquipmentNotAvailable,
    InvalidEquipment,
    InvalidStatusTransition,
)
from rental.domain.size import Size
from tests.unit.factories import make_helmet, make_skis


def test_registered_equipment_is_available_with_its_own_id():
    first, second = make_skis(), make_skis()

    assert first.status is EquipmentStatus.AVAILABLE
    assert first.days_used == 0
    assert first != second


def test_boots_size_must_be_mondopoint():
    with pytest.raises(InvalidEquipment):
        Equipment.register(EquipmentType.BOOTS, "Salomon", "S/Pro", Size.cm(27), Range.SPORT)


def test_skis_size_must_be_cm():
    with pytest.raises(InvalidEquipment):
        Equipment.register(
            EquipmentType.SKIS, "Atomic", "Redster", Size.mondopoint(27), Range.SPORT
        )


def test_skis_must_have_a_range():
    with pytest.raises(InvalidEquipment):
        Equipment.register(EquipmentType.SKIS, "Atomic", "Redster", Size.cm(160))


def test_helmet_cannot_have_a_range():
    with pytest.raises(InvalidEquipment):
        Equipment.register(EquipmentType.HELMET, "Giro", "Ledge", Size.cm(58), Range.PREMIUM)


def test_brand_is_required():
    with pytest.raises(InvalidEquipment):
        Equipment.register(EquipmentType.HELMET, " ", "Ledge", Size.cm(58))


def test_rented_item_cannot_be_rented_again():
    skis = make_skis()
    skis.rent()

    assert skis.status is EquipmentStatus.RENTED
    with pytest.raises(EquipmentNotAvailable):
        skis.rent()


def test_returned_item_always_goes_to_maintenance_and_counts_days_used():
    skis = make_skis()
    skis.rent()

    skis.mark_returned(days=6, damaged=False)

    assert skis.status is EquipmentStatus.MAINTENANCE
    assert not skis.needs_repair
    assert skis.days_used == 6


def test_damaged_item_is_flagged_for_repair():
    skis = make_skis()
    skis.rent()

    skis.mark_returned(days=2, damaged=True)

    assert skis.status is EquipmentStatus.MAINTENANCE
    assert skis.needs_repair


def test_completed_maintenance_makes_item_available_again():
    skis = make_skis()
    skis.rent()
    skis.mark_returned(days=2, damaged=True)

    skis.complete_maintenance()

    assert skis.status is EquipmentStatus.AVAILABLE
    assert not skis.needs_repair


def test_item_in_maintenance_cannot_be_rented():
    skis = make_skis()
    skis.rent()
    skis.mark_returned(days=1, damaged=False)

    with pytest.raises(EquipmentNotAvailable):
        skis.rent()


def test_only_rented_items_can_be_returned():
    with pytest.raises(InvalidStatusTransition):
        make_skis().mark_returned(days=1, damaged=False)


def test_only_items_in_maintenance_can_complete_maintenance():
    with pytest.raises(InvalidStatusTransition):
        make_helmet().complete_maintenance()


def test_any_item_can_be_retired_once():
    skis = make_skis()
    skis.rent()

    skis.retire()

    assert skis.status is EquipmentStatus.RETIRED
    with pytest.raises(InvalidStatusTransition):
        skis.retire()
