"""The command-line adapter with fake use cases injected: no database, no bootstrap, no Django."""

from datetime import date
from decimal import Decimal
from io import StringIO
from uuid import uuid4

import pytest

from rental.adapters.inbound.cli.app import UseCases, run
from rental.application.ports.inbound.create_rental import CreateRentalResult
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.inbound.register_customer import RegisterCustomerResult
from rental.application.ports.inbound.return_rental import ReturnRentalResult
from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import EquipmentNotAvailable
from rental.domain.size import SizeUnit
from rental.domain.skill_level import SkillLevel
from tests.unit.factories import eur, make_helmet, make_skis
from tests.unit.fakes import Recorder

SUNDAY, FRIDAY = date(2026, 12, 20), date(2026, 12, 25)


def use_cases(**fakes) -> UseCases:
    defaults = {name: Recorder() for name in UseCases.__dataclass_fields__}
    recorders = {**defaults, **fakes}
    return UseCases(**{name: (lambda r=recorder: r) for name, recorder in recorders.items()})


def cli(argv: str, cases: UseCases) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = run(argv.split(), cases, out, err)
    return code, out.getvalue(), err.getvalue()


def test_available_lists_items_with_their_ids_and_passes_the_filters():
    skis = EquipmentView.from_entity(make_skis())
    listing = Recorder([skis, EquipmentView.from_entity(make_helmet())])
    cases = use_cases(list_available_equipment=listing)

    code, out, _ = cli("available --type skis --range sport", cases)

    assert code == 0
    assert f"{skis.id}  skis       Rossignol Experience 80 Ti  160 cm  Sport" in out
    assert "58 cm  -" in out
    assert "2 item(s) available." in out
    assert listing.calls[0].type is EquipmentType.SKIS
    assert listing.calls[0].range is Range.SPORT


def test_customer_is_registered_with_a_mondopoint_boot_size():
    customer_id = uuid4()
    register = Recorder(RegisterCustomerResult(customer_id))
    argv = "customer --name Alex --height 175 --boots 26.5 --level intermediate"

    code, out, _ = cli(argv, use_cases(register_customer=register))

    assert code == 0
    assert f"Customer {customer_id} registered." in out
    command = register.calls[0]
    assert command.boot_size.value == Decimal("26.5")
    assert command.boot_size.unit is SizeUnit.MONDOPOINT
    assert command.skill_level is SkillLevel.INTERMEDIATE


def test_rent_creates_the_rental_and_prints_its_price():
    rental_id, customer_id, skis_id, boots_id = uuid4(), uuid4(), uuid4(), uuid4()
    create = Recorder(CreateRentalResult(rental_id, SUNDAY, FRIDAY, eur("180")))
    argv = f"rent --customer {customer_id} --items {skis_id} {boots_id} --until 2026-12-25"

    code, out, _ = cli(argv, use_cases(create_rental=create))

    assert code == 0
    assert f"Rental {rental_id} created: 2026-12-20 to 2026-12-25, 180.00 EUR." in out
    command = create.calls[0]
    assert command.customer_id == customer_id
    assert command.equipment_ids == (skis_id, boots_id)
    assert command.end_date == FRIDAY


def test_return_flags_the_damaged_items():
    rental_id, skis_id = uuid4(), uuid4()
    returning = Recorder(ReturnRentalResult(rental_id, FRIDAY, frozenset({skis_id})))

    cases = use_cases(return_rental=returning)

    code, out, _ = cli(f"return {rental_id} --damaged {skis_id}", cases)

    assert code == 0
    assert "All items are in maintenance, 1 need a repair." in out
    assert returning.calls[0].damaged_equipment_ids == {skis_id}


def test_business_error_is_printed_with_exit_code_1():
    create = Recorder(error=EquipmentNotAvailable("Not available: skis."))
    argv = f"rent --customer {uuid4()} --items {uuid4()} --until 2026-12-25"

    code, out, err = cli(argv, use_cases(create_rental=create))

    assert code == 1
    assert out == ""
    assert "Error: Not available: skis." in err


def test_invalid_arguments_never_reach_the_use_case():
    create = Recorder()
    cases = use_cases(create_rental=create)

    with pytest.raises(SystemExit):
        cli("rent --customer not-an-id --items x --until tomorrow", cases)

    assert create.calls == []
