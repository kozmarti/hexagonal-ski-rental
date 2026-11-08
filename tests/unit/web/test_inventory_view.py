"""The inventory view with fake use cases injected: no database, no bootstrap."""

from decimal import Decimal
from uuid import uuid4

import pytest

from rental.adapters.inbound.web.views import InventoryView
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.inbound.register_equipment import RegisterEquipmentResult
from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import InvalidEquipment
from rental.domain.size import SizeUnit
from tests.unit.factories import make_skis

HTMX = {"HX-Request": "true"}
BOOTS_FORM = {
    "type": "boots",
    "brand": "Salomon",
    "model": "S/Pro",
    "size": "26.5",
    "range": "sport",
}


class FakeListAvailableEquipment:
    def __init__(self, items=()):
        self.items = list(items)
        self.queries = []

    def execute(self, query):
        self.queries.append(query)
        return self.items


class FakeRegisterEquipment:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return RegisterEquipmentResult(equipment_id=uuid4())


@pytest.fixture
def listing():
    return FakeListAvailableEquipment([EquipmentView.from_entity(make_skis())])


@pytest.fixture
def register():
    return FakeRegisterEquipment()


@pytest.fixture
def view(listing, register):
    return InventoryView.as_view(
        list_available_equipment=lambda: listing, register_equipment=lambda: register
    )


def html(response) -> str:
    return response.content.decode()


def test_page_lists_available_equipment_and_the_form(rf, view):
    response = view(rf.get("/inventory/"))

    assert response.status_code == 200
    assert "<nav>" in html(response)
    assert "Rossignol" in html(response)
    assert "Add equipment" in html(response)


def test_htmx_filter_returns_only_the_list(rf, view, listing):
    response = view(rf.get("/inventory/", {"type": "boots", "range": ""}, headers=HTMX))

    assert 'id="equipment-list"' in html(response)
    assert "<nav>" not in html(response)
    assert listing.queries[-1].type is EquipmentType.BOOTS
    assert listing.queries[-1].range is None


def test_valid_form_registers_the_equipment_and_redirects(rf, view, register):
    response = view(rf.post("/inventory/", BOOTS_FORM))

    assert response.status_code == 302
    assert response.url == "/inventory/"
    command = register.commands[0]
    assert command.type is EquipmentType.BOOTS
    assert command.size.value == Decimal("26.5")
    assert command.size.unit is SizeUnit.MONDOPOINT
    assert command.range is Range.SPORT


def test_htmx_registration_returns_a_fresh_form_and_the_updated_list(rf, view):
    response = view(rf.post("/inventory/", BOOTS_FORM, headers=HTMX))

    assert response.status_code == 200
    assert "Equipment registered." in html(response)
    assert 'hx-swap-oob="true"' in html(response)


def test_domain_error_is_shown_on_the_form(rf, listing):
    register = FakeRegisterEquipment(error=InvalidEquipment("helmet cannot have a range."))
    view = InventoryView.as_view(
        list_available_equipment=lambda: listing, register_equipment=lambda: register
    )

    response = view(rf.post("/inventory/", BOOTS_FORM, headers=HTMX))

    assert response.status_code == 200
    assert "helmet cannot have a range." in html(response)
    assert "Equipment registered." not in html(response)


def test_invalid_input_never_reaches_the_use_case(rf, view, register):
    response = view(rf.post("/inventory/", {**BOOTS_FORM, "brand": "", "size": "abc"}))

    assert response.status_code == 200
    assert register.commands == []
    assert "This field is required." in html(response)
