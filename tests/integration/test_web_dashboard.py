"""The dashboard through the real wiring: config/urls.py, bootstrap.py and the database."""

import pytest

from rental.adapters.outbound.orm.repositories import DjangoEquipmentRepository
from tests.unit.factories import make_skis

pytestmark = pytest.mark.django_db


def test_dashboard_is_the_home_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Today:" in response.content.decode()


def test_items_in_maintenance_show_on_the_dashboard(client):
    skis = make_skis()
    skis.rent()
    skis.mark_returned(days=2, damaged=True)
    DjangoEquipmentRepository().save(skis)

    content = client.get("/").content.decode()

    assert "🔧 1 to repair" in content
    assert "Rossignol" in content
