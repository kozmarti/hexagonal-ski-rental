"""The command-line adapter through the real wiring: config/cli.py,
bootstrap.py and the database."""

from io import StringIO

import pytest
from django.utils import timezone

from config.cli import USE_CASES
from rental import bootstrap
from rental.adapters.inbound.cli.app import run
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size

pytestmark = pytest.mark.django_db


def cli(argv: str) -> str:
    out, err = StringIO(), StringIO()
    assert run(argv.split(), USE_CASES, out, err) == 0, err.getvalue()
    return out.getvalue()


def test_rent_and_return_from_the_terminal():
    command = RegisterEquipmentCommand(
        type=EquipmentType.SKIS,
        brand="Atomic",
        model="Redster",
        size=Size.cm(165),
        range=Range.SPORT,
    )
    skis = bootstrap.register_equipment().execute(command)
    assert str(skis.equipment_id) in cli("available --type skis")

    customer_line = cli("customer --name Alex --height 175 --boots 26.5 --level intermediate")
    customer_id = customer_line.split()[1]
    today = timezone.localdate().isoformat()

    rent_line = cli(f"rent --customer {customer_id} --items {skis.equipment_id} --until {today}")
    assert "30.00 EUR" in rent_line
    assert "0 item(s) available." in cli("available")

    rental_id = rent_line.split()[1]
    assert "1 need a repair" in cli(f"return {rental_id} --damaged {skis.equipment_id}")
    assert bootstrap.get_dashboard().execute().in_maintenance[0].needs_repair
