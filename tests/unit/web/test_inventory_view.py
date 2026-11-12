"""The complete inventory with fake use cases injected: no database, no bootstrap."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from rental.adapters.inbound.web.views import InventoryView
from rental.application.ports.inbound.get_dashboard import Dashboard, RentalView
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.inbound.register_equipment import RegisterEquipmentResult
from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import InvalidEquipment
from rental.domain.size import SizeUnit
from tests.unit.factories import eur, make_boots, make_helmet, make_skis
from tests.unit.fakes import HTMX, Recorder, html

BOOTS_FORM = {
    "type": "boots",
    "brand": "Salomon",
    "model": "S/Pro",
    "size": "26.5",
    "range": "sport",
}
FRIDAY = date(2026, 12, 25)


class FakeRegisterEquipment:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return RegisterEquipmentResult(equipment_id=uuid4())


def a_helmet_to_repair() -> EquipmentView:
    helmet = make_helmet()
    helmet.rent()
    helmet.mark_returned(days=1, damaged=True)
    return EquipmentView.from_entity(helmet)


def inventory(register=None, available=None):
    """Available skis, boots rented by Alex Martin, a helmet waiting for a repair."""
    boots = EquipmentView.from_entity(make_boots())
    rental = RentalView(uuid4(), uuid4(), "Alex Martin", [boots], FRIDAY, FRIDAY, eur("70"))
    dashboard = Dashboard(FRIDAY, [rental], [], [], [])
    available = available if available is not None else [EquipmentView.from_entity(make_skis())]
    return InventoryView.as_view(
        get_dashboard=lambda: Recorder(dashboard),
        list_equipment_in_maintenance=lambda: Recorder([a_helmet_to_repair()]),
        list_available_equipment=lambda: Recorder(available),
        register_equipment=lambda: register or FakeRegisterEquipment(),
    )


def test_every_item_is_listed_with_its_status_and_the_totals(rf):
    content = html(inventory()(rf.get("/inventory/")))

    assert "<strong>3 items</strong>" in content
    assert "1 available · 1 rented ·" in content
    assert "1 in maintenance (1 to repair)" in content
    assert 'class="badge badge-available"' in content
    assert 'class="badge badge-rented"' in content
    assert "Alex Martin, until Fri 25 Dec" in content
    assert 'class="badge badge-repair"' in content
    assert "Add equipment" in content


def test_htmx_filter_returns_only_the_list_for_that_type(rf):
    response = inventory()(rf.get("/inventory/", {"type": "boots"}, headers=HTMX))

    assert 'id="equipment-list"' in html(response)
    assert "<nav>" not in html(response)
    assert "<strong>1 item</strong>" in html(response)
    assert "Salomon" in html(response)
    assert "Rossignol" not in html(response)


def test_the_status_filter_narrows_the_table_but_the_totals_count_every_status(rf):
    content = html(inventory()(rf.get("/inventory/", {"status": "rented"}, headers=HTMX)))

    assert "<strong>3 items</strong>" in content
    assert content.count("<tr>") == 2  # the header and the rented boots
    assert "Alex Martin" in content


def test_a_long_inventory_is_split_into_pages_keeping_the_filters(rf):
    many_skis = [EquipmentView.from_entity(make_skis()) for _ in range(30)]
    view = inventory(available=many_skis)

    first = html(view(rf.get("/inventory/", {"type": "skis"}, headers=HTMX)))
    second = html(view(rf.get("/inventory/", {"type": "skis", "page": "2"}, headers=HTMX)))

    assert first.count('class="badge badge-available"') == 25
    assert "Page 1 of 2" in first
    assert "?type=skis&amp;page=2" in first
    assert second.count('class="badge badge-available"') == 5


def test_valid_form_registers_the_equipment_and_redirects(rf):
    register = FakeRegisterEquipment()

    response = inventory(register)(rf.post("/inventory/", BOOTS_FORM))

    assert response.status_code == 302
    assert response.url == "/inventory/"
    command = register.commands[0]
    assert command.type is EquipmentType.BOOTS
    assert command.size.value == Decimal("26.5")
    assert command.size.unit is SizeUnit.MONDOPOINT
    assert command.range is Range.SPORT


def test_htmx_registration_returns_a_fresh_form_and_the_updated_list(rf):
    response = inventory()(rf.post("/inventory/", BOOTS_FORM, headers=HTMX))

    assert response.status_code == 200
    assert "Equipment registered." in html(response)
    assert 'hx-swap-oob="true"' in html(response)


def test_domain_error_is_shown_on_the_form(rf):
    register = FakeRegisterEquipment(error=InvalidEquipment("helmet cannot have a range."))

    response = inventory(register)(rf.post("/inventory/", BOOTS_FORM, headers=HTMX))

    assert response.status_code == 200
    assert "helmet cannot have a range." in html(response)
    assert "Equipment registered." not in html(response)


@pytest.mark.parametrize("wrong", [{"brand": ""}, {"size": "abc"}])
def test_invalid_input_never_reaches_the_use_case(rf, wrong):
    register = FakeRegisterEquipment()

    response = inventory(register)(rf.post("/inventory/", {**BOOTS_FORM, **wrong}))

    assert response.status_code == 200
    assert register.commands == []
