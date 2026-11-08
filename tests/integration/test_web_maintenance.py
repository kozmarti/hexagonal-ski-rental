"""The maintenance screen through the real wiring: config/urls.py, bootstrap.py and the database."""

import pytest

from rental.adapters.outbound.orm.repositories import DjangoEquipmentRepository
from tests.unit.factories import make_skis

pytestmark = pytest.mark.django_db


def test_returned_item_is_serviced_and_available_again(client):
    skis = make_skis()
    skis.rent()
    skis.mark_returned(days=3, damaged=True)
    DjangoEquipmentRepository().save(skis)

    assert "🔧 Repair" in client.get("/maintenance/").content.decode()

    response = client.post(f"/maintenance/{skis.id}/done/")

    assert response.status_code == 302
    assert "Nothing to service." in client.get(response.url).content.decode()
    assert "Rossignol" in client.get("/inventory/").content.decode()
