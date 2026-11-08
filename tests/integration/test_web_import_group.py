"""The group import through the real wiring, with the demo data and the example CSV file."""

from io import StringIO
from pathlib import Path
from uuid import UUID

import pytest
from django.core.management import call_command
from django.utils import timezone

from rental import bootstrap
from rental.adapters.outbound.orm.repositories import DjangoCustomerRepository
from rental.domain.exceptions import CustomerNotFound

pytestmark = pytest.mark.django_db

EXAMPLE = Path(__file__).parents[2] / "examples" / "ski_school_group.csv"
HTMX = {"HX-Request": "true"}


def test_the_example_class_is_equipped_except_the_smallest_child(client):
    call_command("seed_demo", stdout=StringIO())
    active_before = len(bootstrap.get_dashboard().execute().active_rentals)

    with EXAMPLE.open("rb") as csv_file:
        response = client.post(
            "/rentals/import/",
            {"file": csv_file, "end_date": timezone.localdate().isoformat()},
        )

    page = response.content.decode()
    assert "4 of 5 children equipped" in page
    assert "Fit by hand" in page
    assert len(bootstrap.get_dashboard().execute().active_rentals) == active_before + 4

    # Inès could not be equipped: "Not renting" removes her customer record.
    ines_id = page.split("/rentals/import/not-renting/")[1].split("/")[0]
    response = client.post(f"/rentals/import/not-renting/{ines_id}/", headers=HTMX)
    assert "Customer removed." in response.content.decode()
    with pytest.raises(CustomerNotFound):
        DjangoCustomerRepository().get(UUID(ines_id))
