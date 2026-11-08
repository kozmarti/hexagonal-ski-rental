"""The JSON API with fake use cases injected: no database, no bootstrap."""

import json
from datetime import date
from decimal import Decimal
from uuid import uuid4

from rental.adapters.inbound.api import views as api
from rental.application.ports.inbound.create_rental import CreateRentalResult
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.inbound.register_customer import RegisterCustomerResult
from rental.application.ports.inbound.return_rental import ReturnRentalResult
from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import CustomerNotFound, EquipmentNotAvailable
from rental.domain.size import SizeUnit
from rental.domain.skill_level import SkillLevel
from tests.unit.factories import eur, make_skis
from tests.unit.fakes import Recorder
from tests.unit.web.test_rental_views import recommendation

CUSTOMER = {"name": "Alex Martin", "height_cm": 175, "boot_size": 26.5, "skill_level": "expert"}
SUNDAY, FRIDAY = date(2026, 12, 20), date(2026, 12, 25)


def rental_payload(equipment_ids, end_date="2026-12-25"):
    return {"customer_id": str(uuid4()), "equipment_ids": equipment_ids, "end_date": end_date}


def call(view, request, **kwargs):
    response = view(request, **kwargs)
    return response.status_code, json.loads(response.content)


def post(rf, data):
    body = data if isinstance(data, str) else json.dumps(data)
    return rf.post("/", body, content_type="application/json")


class TestEquipment:
    def test_lists_available_items_and_passes_the_filters(self, rf):
        skis = EquipmentView.from_entity(make_skis())
        listing = Recorder([skis])
        view = api.EquipmentApi.as_view(list_available_equipment=lambda: listing)

        status, body = call(view, rf.get("/", {"type": "skis", "range": "sport"}))

        assert status == 200
        assert body["items"][0] == {
            "id": str(skis.id),
            "type": "skis",
            "brand": "Rossignol",
            "model": "Experience 80 Ti",
            "size": {"value": "160", "unit": "cm"},
            "range": "sport",
            "days_used": 0,
            "needs_repair": False,
        }
        assert listing.calls[0].type is EquipmentType.SKIS
        assert listing.calls[0].range is Range.SPORT

    def test_unknown_filter_value_is_a_bad_request(self, rf):
        view = api.EquipmentApi.as_view(list_available_equipment=lambda: Recorder([]))

        status, body = call(view, rf.get("/", {"type": "sledge"}))

        assert status == 400
        assert "type" in body["errors"]


class TestCustomers:
    def test_registers_the_customer(self, rf):
        customer_id = uuid4()
        register = Recorder(RegisterCustomerResult(customer_id))
        view = api.CustomersApi.as_view(register_customer=lambda: register)

        status, body = call(view, post(rf, CUSTOMER))

        assert (status, body) == (201, {"id": str(customer_id)})
        command = register.calls[0]
        assert command.boot_size.value == Decimal("26.5")
        assert command.boot_size.unit is SizeUnit.MONDOPOINT
        assert command.skill_level is SkillLevel.EXPERT

    def test_every_invalid_field_is_reported_and_nothing_is_registered(self, rf):
        register = Recorder()
        view = api.CustomersApi.as_view(register_customer=lambda: register)
        wrong = {"name": "", "height_cm": "tall", "boot_size": "NaN", "skill_level": "pro"}

        status, body = call(view, post(rf, wrong))

        assert status == 400
        assert set(body["errors"]) == {"name", "height_cm", "boot_size", "skill_level"}
        assert register.calls == []

    def test_malformed_json_is_a_bad_request(self, rf):
        view = api.CustomersApi.as_view(register_customer=lambda: Recorder())

        status, body = call(view, post(rf, "{not json"))

        assert (status, body) == (400, {"errors": {"body": "Invalid JSON."}})

    def test_wrong_method_is_refused_as_json(self, rf):
        view = api.CustomersApi.as_view(register_customer=lambda: Recorder())

        status, body = call(view, rf.get("/"))

        assert (status, body) == (405, {"error": "Method not allowed."})


class TestRecommendation:
    def test_returns_the_recommendation(self, rf):
        view = api.RecommendationApi.as_view(recommend_equipment=lambda: Recorder(recommendation()))

        status, body = call(view, rf.get("/"), customer_id=uuid4())

        assert status == 200
        assert body["range"] == "sport"
        assert body["ski_length"] == {"value": "165", "unit": "cm"}
        assert len(body["skis"]) == 1

    def test_unknown_customer_is_a_404(self, rf):
        error = CustomerNotFound("Customer not found.")
        view = api.RecommendationApi.as_view(recommend_equipment=lambda: Recorder(error=error))

        status, body = call(view, rf.get("/"), customer_id=uuid4())

        assert (status, body) == (404, {"error": "Customer not found."})


class TestRentals:
    def test_creates_the_rental(self, rf):
        rental_id, skis_id = uuid4(), uuid4()
        create = Recorder(CreateRentalResult(rental_id, SUNDAY, FRIDAY, eur("180")))
        view = api.RentalsApi.as_view(create_rental=lambda: create)

        status, body = call(view, post(rf, rental_payload([str(skis_id)])))

        assert status == 201
        assert body == {
            "id": str(rental_id),
            "start_date": "2026-12-20",
            "end_date": "2026-12-25",
            "price": {"amount": "180.00", "currency": "EUR"},
        }
        assert create.calls[0].equipment_ids == (skis_id,)

    def test_business_rule_refusal_is_a_conflict(self, rf):
        create = Recorder(error=EquipmentNotAvailable("Not available."))
        view = api.RentalsApi.as_view(create_rental=lambda: create)

        status, body = call(view, post(rf, rental_payload([str(uuid4())])))

        assert (status, body) == (409, {"error": "Not available."})

    def test_a_rental_needs_items(self, rf):
        view = api.RentalsApi.as_view(create_rental=lambda: Recorder())

        status, body = call(view, post(rf, rental_payload([], end_date="tomorrow")))

        assert status == 400
        assert set(body["errors"]) == {"equipment_ids", "end_date"}

    def test_return_lists_the_items_needing_a_repair(self, rf):
        rental_id, skis_id = uuid4(), uuid4()
        returning = Recorder(ReturnRentalResult(rental_id, FRIDAY, frozenset({skis_id})))
        view = api.ReturnRentalApi.as_view(return_rental=lambda: returning)
        request = post(rf, {"damaged_equipment_ids": [str(skis_id)]})

        status, body = call(view, request, rental_id=rental_id)

        assert status == 200
        assert body["needs_repair_ids"] == [str(skis_id)]
        assert returning.calls[0].damaged_equipment_ids == {skis_id}
