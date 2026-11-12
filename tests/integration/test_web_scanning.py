"""Labels and scan pages through the real wiring: config/urls.py, bootstrap.py and the database."""

import pytest

from rental import bootstrap
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size

pytestmark = pytest.mark.django_db


def test_a_registered_item_gets_a_label_and_a_scan_page(client, settings):
    settings.LABELS_BASE_URL = "http://192.168.1.20:8000"
    command = RegisterEquipmentCommand(
        type=EquipmentType.SKIS,
        brand="Atomic",
        model="Redster",
        size=Size.cm(165),
        range=Range.SPORT,
    )
    skis_id = bootstrap.register_equipment().execute(command).equipment_id

    labels = client.get("/inventory/labels/").content.decode()
    item_page = client.get(f"/scan/{skis_id}/").content.decode()
    dialog = client.get(f"/equipment/{skis_id}/qr/").content.decode()

    assert labels.count('<div class="label">') == 1
    assert "Atomic Redster" in labels
    assert "Available." in item_page
    assert f"http://192.168.1.20:8000/scan/{skis_id}/" in dialog
    assert 'data-scan="goto"' in client.get("/scan/").content.decode()
