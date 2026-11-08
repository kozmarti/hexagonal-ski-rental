"""The counter screens through the real wiring: config/urls.py, bootstrap.py and the database."""

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_rent_and_return_at_the_counter(client):
    client.post(
        "/inventory/",
        {"type": "skis", "brand": "Atomic", "model": "Redster", "size": "165", "range": "sport"},
    )
    response = client.post(
        "/rentals/new/",
        {
            "name": "Alex Martin",
            "height_cm": "175",
            "boot_size": "26.5",
            "skill_level": "intermediate",
        },
    )
    choose_url = response.url

    choose_page = client.get(choose_url).content.decode()
    assert "Recommended skis" in choose_page
    assert "Atomic Redster" in choose_page
    skis_id = choose_page.split('name="equipment" value="')[1].split('"')[0]

    response = client.post(
        choose_url, {"equipment": [skis_id], "end_date": timezone.localdate().isoformat()}
    )
    rentals_page = client.get(response.url).content.decode()
    assert "Alex Martin" in rentals_page
    assert "30.00 EUR" in rentals_page

    rental_id = response.url.split("created=")[1]
    response = client.post(f"/rentals/{rental_id}/return/", {"damaged": [skis_id]})
    assert response.status_code == 302
    assert "No active rentals." in client.get("/rentals/").content.decode()
