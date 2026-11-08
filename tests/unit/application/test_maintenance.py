from uuid import uuid4

import pytest

from rental.application.ports.inbound.complete_maintenance import CompleteMaintenanceCommand
from rental.application.ports.outbound.notifier import MaintenanceCompleted
from rental.application.services.complete_maintenance import CompleteMaintenanceService
from rental.application.services.list_equipment_in_maintenance import (
    ListEquipmentInMaintenanceService,
)
from rental.domain.equipment import EquipmentStatus
from rental.domain.exceptions import EquipmentNotFound, InvalidStatusTransition
from tests.unit.factories import make_boots, make_helmet, make_skis


def returned(item, damaged=False):
    item.rent()
    item.mark_returned(days=1, damaged=damaged)
    return item


def complete(shop, equipment_id):
    service = CompleteMaintenanceService(shop.equipment, shop.notifier, shop.uow)
    return service.execute(CompleteMaintenanceCommand(equipment_id))


def test_lists_items_in_maintenance_repairs_first(shop):
    serviced, damaged = returned(make_skis()), returned(make_boots(), damaged=True)
    shop.add(serviced, damaged, make_helmet())

    views = ListEquipmentInMaintenanceService(shop.equipment).execute()

    assert [view.id for view in views] == [damaged.id, serviced.id]
    assert [view.needs_repair for view in views] == [True, False]


def test_completed_item_is_available_again_and_notified(shop):
    skis = returned(make_skis(), damaged=True)
    shop.add(skis)

    result = complete(shop, skis.id)

    saved = shop.equipment.get(result.equipment_id)
    assert saved.status is EquipmentStatus.AVAILABLE
    assert not saved.needs_repair
    assert shop.uow.committed
    assert shop.notifier.sent == [MaintenanceCompleted(skis.id)]


def test_item_not_in_maintenance_is_rejected(shop):
    skis = make_skis()
    shop.add(skis)

    with pytest.raises(InvalidStatusTransition):
        complete(shop, skis.id)

    assert not shop.uow.committed
    assert shop.notifier.sent == []


def test_unknown_item_is_not_found(shop):
    with pytest.raises(EquipmentNotFound):
        complete(shop, uuid4())
