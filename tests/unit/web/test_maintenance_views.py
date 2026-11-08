"""The maintenance screen with fake use cases injected: no database, no bootstrap."""

from uuid import uuid4

import pytest
from django.http import Http404

from rental.adapters.inbound.web.views import CompleteMaintenanceView, MaintenanceView
from rental.application.ports.inbound.complete_maintenance import CompleteMaintenanceResult
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.domain.exceptions import EquipmentNotFound, InvalidStatusTransition
from tests.unit.factories import make_boots, make_skis
from tests.unit.web.fakes import HTMX, Recorder, html


def in_maintenance(item, damaged):
    item.rent()
    item.mark_returned(days=2, damaged=damaged)
    return EquipmentView.from_entity(item)


def list_view(items):
    return MaintenanceView.as_view(list_equipment_in_maintenance=lambda: Recorder(items))


def done_view(recorder):
    return CompleteMaintenanceView.as_view(complete_maintenance=lambda: recorder)


def test_items_are_listed_with_the_work_to_do_repairs_first(rf):
    repair, service = in_maintenance(make_skis(), True), in_maintenance(make_boots(), False)

    page = html(list_view([repair, service])(rf.get("/maintenance/")))

    assert "🔧 Repair" in page
    assert "Service" in page
    assert page.index(f"item-{repair.id}") < page.index(f"item-{service.id}")


def test_empty_maintenance_says_so(rf):
    assert "Nothing to service." in html(list_view([])(rf.get("/maintenance/")))


def test_htmx_done_replaces_the_row(rf):
    equipment_id = uuid4()
    recorder = Recorder(CompleteMaintenanceResult(equipment_id))

    response = done_view(recorder)(rf.post("/", headers=HTMX), equipment_id=equipment_id)

    assert "available again" in html(response)
    assert recorder.calls[0].equipment_id == equipment_id


def test_done_without_javascript_redirects_to_the_list(rf):
    equipment_id = uuid4()
    view = done_view(Recorder(CompleteMaintenanceResult(equipment_id)))

    response = view(rf.post("/"), equipment_id=equipment_id)

    assert response.status_code == 302
    assert response.url == f"/maintenance/?done={equipment_id}"


def test_item_not_in_maintenance_shows_the_error(rf):
    recorder = Recorder(error=InvalidStatusTransition("Equipment is available."))

    response = done_view(recorder)(rf.post("/", headers=HTMX), equipment_id=uuid4())

    assert "Equipment is available." in html(response)


def test_unknown_item_is_a_404(rf):
    view = done_view(Recorder(error=EquipmentNotFound("unknown")))

    with pytest.raises(Http404):
        view(rf.post("/"), equipment_id=uuid4())
