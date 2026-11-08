"""The inventory screen through the real wiring: config/urls.py, bootstrap.py and the database."""

import pytest

pytestmark = pytest.mark.django_db


def test_registered_equipment_appears_in_the_inventory(client):
    response = client.post(
        "/inventory/",
        {"type": "skis", "brand": "Atomic", "model": "Redster", "size": "170", "range": "premium"},
    )
    assert response.status_code == 302

    page = client.get("/inventory/").content.decode()

    assert "Atomic" in page
    assert "170 cm" in page
