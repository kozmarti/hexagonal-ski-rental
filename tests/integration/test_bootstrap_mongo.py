"""The whole app on MongoDB: REPOSITORY_BACKEND=mongo makes bootstrap.py wire the Mongo
adapters; nothing else changes."""

import pytest
from django.utils import timezone

from rental import bootstrap
from rental.adapters.outbound.mongo.repositories import MongoEquipmentRepository
from rental.adapters.outbound.orm.repositories import DjangoEquipmentRepository
from rental.application.ports.inbound.create_rental import CreateRentalCommand
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipmentQuery
from rental.application.ports.inbound.register_customer import RegisterCustomerCommand
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.application.ports.inbound.return_rental import ReturnRentalCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel


@pytest.fixture
def on_mongo(settings, mongo_context):
    settings.REPOSITORY_BACKEND = "mongo"
    settings.MONGO_DB = mongo_context.database.name
    return mongo_context


def test_bootstrap_chooses_the_mongo_adapters(on_mongo):
    assert isinstance(bootstrap.storage().equipment, MongoEquipmentRepository)


def test_tests_use_the_orm_whatever_the_developers_env_says():
    # Bug: with REPOSITORY_BACKEND=mongo in .env, integration tests ran on the developer's own
    # MongoDB data (seed_demo refused, 45 labels instead of 1...). tests/conftest.py prevents it.
    assert isinstance(bootstrap.storage().equipment, DjangoEquipmentRepository)


def test_rent_and_return_on_mongodb(on_mongo):
    skis_command = RegisterEquipmentCommand(
        type=EquipmentType.SKIS,
        brand="Atomic",
        model="Redster",
        size=Size.cm(165),
        range=Range.SPORT,
    )
    customer_command = RegisterCustomerCommand(
        name="Alex Martin",
        height_cm=175,
        boot_size=Size.mondopoint("26.5"),
        skill_level=SkillLevel.INTERMEDIATE,
    )
    skis_id = bootstrap.register_equipment().execute(skis_command).equipment_id
    customer_id = bootstrap.register_customer().execute(customer_command).customer_id
    today = timezone.localdate()

    rental = bootstrap.create_rental().execute(CreateRentalCommand(customer_id, (skis_id,), today))

    assert rental.price.amount == 30
    assert bootstrap.list_available_equipment().execute(ListAvailableEquipmentQuery()) == []
    due_back = bootstrap.get_dashboard().execute().due_back_today
    assert [view.id for view in due_back] == [rental.rental_id]

    bootstrap.return_rental().execute(ReturnRentalCommand(rental.rental_id))

    in_maintenance = bootstrap.get_dashboard().execute().in_maintenance
    assert [item.id for item in in_maintenance] == [skis_id]
    assert on_mongo.database["rentals"].count_documents({}) == 1
