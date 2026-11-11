"""The JSON API through the real wiring: config/urls.py, bootstrap.py and the database."""

import pytest
from django.test import Client
from django.utils import timezone

from rental import bootstrap
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size

pytestmark = pytest.mark.django_db

CUSTOMER = {"name": "Alex Martin", "height_cm": 175, "boot_size": 26.5, "skill_level": "expert"}


@pytest.fixture
def api(settings):
    # As for a real tablet: CSRF checks on (the API needs no CSRF token) and a device key.
    settings.API_KEYS = ["integration-tablet-key"]
    headers = {"Authorization": "Bearer integration-tablet-key"}
    return Client(enforce_csrf_checks=True, headers=headers)


def test_the_api_refuses_requests_without_the_device_key(api):
    response = Client().get("/api/equipment/")

    assert response.status_code == 401
    assert api.get("/api/equipment/").status_code == 200


def post(api, url, data):
    return api.post(url, data, content_type="application/json")


def register_skis() -> str:
    command = RegisterEquipmentCommand(
        type=EquipmentType.SKIS,
        brand="Atomic",
        model="Redster",
        size=Size.cm(170),
        range=Range.PREMIUM,
    )
    return str(bootstrap.register_equipment().execute(command).equipment_id)


def rent(api, customer_id, skis_id):
    today = timezone.localdate().isoformat()
    data = {"customer_id": customer_id, "equipment_ids": [skis_id], "end_date": today}
    return post(api, "/api/rentals/", data)


def test_rent_and_return_through_the_api(api):
    skis_id = register_skis()
    response = post(api, "/api/customers/", CUSTOMER)
    assert response.status_code == 201
    customer_id = response.json()["id"]

    recommended = api.get(f"/api/customers/{customer_id}/recommendation/").json()
    assert [item["id"] for item in recommended["skis"]] == [skis_id]

    response = rent(api, customer_id, skis_id)
    assert response.status_code == 201
    assert response.json()["price"] == {"amount": "40.00", "currency": "EUR"}
    assert api.get("/api/equipment/").json() == {"items": []}

    rental_id = response.json()["id"]
    response = post(api, f"/api/rentals/{rental_id}/return/", {"damaged_equipment_ids": [skis_id]})
    assert response.status_code == 200
    assert response.json()["needs_repair_ids"] == [skis_id]


def test_renting_skis_that_are_already_out_is_a_conflict(api):
    skis_id = register_skis()
    customer_id = post(api, "/api/customers/", CUSTOMER).json()["id"]
    rent(api, customer_id, skis_id)

    response = rent(api, customer_id, skis_id)

    assert response.status_code == 409
    assert "Not available" in response.json()["error"]
