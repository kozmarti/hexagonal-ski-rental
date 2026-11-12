"""The Pricing page through the real wiring: a new price is used by the next rental."""

import pytest
from django.utils import timezone

from rental import bootstrap
from rental.application.ports.inbound.create_rental import CreateRentalCommand
from rental.application.ports.inbound.register_customer import RegisterCustomerCommand
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel

pytestmark = pytest.mark.django_db


def set_sport_skis_day_price(client, amount: str) -> None:
    form = {}
    for rate in bootstrap.get_price_list().execute():
        key = f"{rate.type}-{rate.range or 'none'}"
        form[f"day-{key}"], form[f"week-{key}"] = str(rate.day.amount), str(rate.week.amount)
    form["day-skis-sport"] = amount

    assert client.post("/pricing/", form).url == "/pricing/?saved=1"


def rent_sport_skis():
    skis = RegisterEquipmentCommand(
        EquipmentType.SKIS, "Atomic", "Redster", Size.cm(165), Range.SPORT
    )
    customer = RegisterCustomerCommand(
        "Alex Martin", 175, Size.mondopoint("26.5"), SkillLevel.INTERMEDIATE
    )
    skis_id = bootstrap.register_equipment().execute(skis).equipment_id
    customer_id = bootstrap.register_customer().execute(customer).customer_id
    command = CreateRentalCommand(customer_id, (skis_id,), timezone.localdate())
    return bootstrap.create_rental().execute(command)


def test_a_new_price_is_used_by_the_next_rental(client):
    set_sport_skis_day_price(client, "35")

    assert rent_sport_skis().price.amount == 35


def test_a_rental_already_out_keeps_the_price_it_was_created_with(client):
    rental = rent_sport_skis()
    assert rental.price.amount == 30

    set_sport_skis_day_price(client, "35")

    (still_out,) = bootstrap.get_dashboard().execute().active_rentals
    assert still_out.id == rental.rental_id
    assert still_out.price.amount == 30
