"""The counter screens with fake use cases injected: no database, no bootstrap."""

from datetime import date
from uuid import uuid4

import pytest
from django.http import Http404

from rental.adapters.inbound.web.views import (
    ChooseEquipmentView,
    NewRentalView,
    RentalsView,
    ReturnRentalView,
)
from rental.application.ports.inbound.create_rental import CreateRentalResult
from rental.application.ports.inbound.get_dashboard import Dashboard, RentalView
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.inbound.recommend_equipment import RecommendEquipmentResult
from rental.application.ports.inbound.register_customer import RegisterCustomerResult
from rental.application.ports.inbound.return_rental import ReturnRentalResult
from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import (
    CustomerNotFound,
    EquipmentNotAvailable,
    RentalAlreadyReturned,
    RentalNotFound,
)
from rental.domain.size import Size, SizeUnit
from rental.domain.skill_level import SkillLevel
from tests.unit.factories import eur, make_boots, make_helmet, make_skis
from tests.unit.web.fakes import HTMX, Recorder, html

FRIDAY = date(2026, 12, 25)

SKIS = EquipmentView.from_entity(make_skis())
BOOTS = EquipmentView.from_entity(make_boots())
HELMET = EquipmentView.from_entity(make_helmet())
PREMIUM_SKIS = EquipmentView.from_entity(make_skis(Range.PREMIUM))


class FakeListAvailableEquipment:
    def execute(self, query):
        by_type = {EquipmentType.HELMET: [HELMET], EquipmentType.POLES: []}
        if query.type is None:
            return [SKIS, BOOTS, HELMET, PREMIUM_SKIS]
        return by_type.get(query.type, [])


def recommendation() -> RecommendEquipmentResult:
    return RecommendEquipmentResult(
        range=Range.SPORT,
        ski_length=Size.cm(165),
        snowboard_length=Size.cm(155),
        boot_size=Size.mondopoint("26.5"),
        skis=[SKIS],
        snowboards=[],
        boots=[BOOTS],
    )


def choose_view(create=None, recommend=None):
    create = create or Recorder(CreateRentalResult(uuid4(), date.today(), FRIDAY, eur("180")))
    recommend = recommend or Recorder(recommendation())
    view = ChooseEquipmentView.as_view(
        recommend_equipment=lambda: recommend,
        list_available_equipment=FakeListAvailableEquipment,
        create_rental=lambda: create,
    )
    return view, create


class TestNewRental:
    CUSTOMER_FORM = {
        "name": "Alex Martin",
        "height_cm": "175",
        "boot_size": "26.5",
        "skill_level": "intermediate",
    }

    def test_valid_customer_goes_to_the_equipment_step(self, rf):
        customer_id = uuid4()
        register = Recorder(RegisterCustomerResult(customer_id))
        view = NewRentalView.as_view(register_customer=lambda: register)

        response = view(rf.post("/rentals/new/", self.CUSTOMER_FORM))

        assert response.status_code == 302
        assert response.url == f"/rentals/new/{customer_id}/"
        command = register.calls[0]
        assert command.boot_size.unit is SizeUnit.MONDOPOINT
        assert command.skill_level is SkillLevel.INTERMEDIATE

    def test_invalid_customer_never_reaches_the_use_case(self, rf):
        register = Recorder(RegisterCustomerResult(uuid4()))
        view = NewRentalView.as_view(register_customer=lambda: register)

        response = view(rf.post("/rentals/new/", {**self.CUSTOMER_FORM, "height_cm": "10"}))

        assert response.status_code == 200
        assert register.calls == []


class TestChooseEquipment:
    def test_page_shows_the_recommendation_and_every_available_item_once(self, rf):
        view, _ = choose_view()

        page = html(view(rf.get("/"), customer_id=uuid4()))

        assert "165 cm" in page
        assert "26.5 mondopoint" in page
        assert page.count(f'value="{SKIS.id}"') == 1
        assert page.count(f'value="{HELMET.id}"') == 1
        assert page.count(f'value="{PREMIUM_SKIS.id}"') == 1
        assert "Other available equipment (1)" in page

    def test_unknown_customer_is_a_404(self, rf):
        view, _ = choose_view(recommend=Recorder(error=CustomerNotFound("unknown")))

        with pytest.raises(Http404):
            view(rf.get("/"), customer_id=uuid4())

    def test_valid_choice_creates_the_rental_and_shows_it(self, rf):
        view, create = choose_view()
        customer_id = uuid4()
        form = {"equipment": [str(SKIS.id), str(BOOTS.id)], "end_date": "2026-12-25"}

        response = view(rf.post("/", form), customer_id=customer_id)

        assert response.status_code == 302
        assert response.url == f"/rentals/?created={create.result.rental_id}"
        command = create.calls[0]
        assert command.customer_id == customer_id
        assert command.equipment_ids == (SKIS.id, BOOTS.id)
        assert command.end_date == FRIDAY

    def test_at_least_one_item_is_required(self, rf):
        view, create = choose_view()

        page = html(view(rf.post("/", {"end_date": "2026-12-25"}), customer_id=uuid4()))

        assert "Choose at least one item." in page
        assert create.calls == []

    def test_domain_error_is_shown_and_the_choice_is_kept(self, rf):
        view, _ = choose_view(create=Recorder(error=EquipmentNotAvailable("Not available.")))
        form = {"equipment": [str(SKIS.id)], "end_date": "2026-12-25"}

        page = html(view(rf.post("/", form), customer_id=uuid4()))

        assert "Not available." in page
        assert f'value="{SKIS.id}" checked' in page


class TestRentals:
    def test_active_rentals_are_listed_with_the_new_one_highlighted(self, rf):
        rental = RentalView(
            uuid4(), uuid4(), "Alex Martin", [SKIS], date.today(), FRIDAY, eur("180")
        )
        dashboard = Dashboard(date.today(), [rental], [], [], [])
        view = RentalsView.as_view(get_dashboard=lambda: Recorder(dashboard))

        page = html(view(rf.get("/rentals/", {"created": str(rental.id)})))

        assert "Alex Martin" in page
        assert "180.00 EUR" in page
        assert "<ins>New</ins>" in page
        assert f'name="damaged" value="{SKIS.id}"' in page


class TestReturnRental:
    def result(self, rental_id, repaired=()):
        return ReturnRentalResult(rental_id, date.today(), frozenset(repaired))

    def test_htmx_return_replaces_the_rental_block(self, rf):
        rental_id = uuid4()
        returning = Recorder(self.result(rental_id, [SKIS.id]))
        view = ReturnRentalView.as_view(return_rental=lambda: returning)

        response = view(
            rf.post("/", {"damaged": [str(SKIS.id)]}, headers=HTMX), rental_id=rental_id
        )

        assert "Rental returned" in html(response)
        assert "1 of them flagged for repair" in html(response)
        assert returning.calls[0].rental_id == rental_id
        assert returning.calls[0].damaged_equipment_ids == {SKIS.id}

    def test_return_without_javascript_redirects_to_the_list(self, rf):
        rental_id = uuid4()
        view = ReturnRentalView.as_view(return_rental=lambda: Recorder(self.result(rental_id)))

        response = view(rf.post("/"), rental_id=rental_id)

        assert response.status_code == 302
        assert response.url == f"/rentals/?returned={rental_id}"

    def test_invalid_damaged_id_is_a_bad_request(self, rf):
        view = ReturnRentalView.as_view(return_rental=lambda: Recorder())

        response = view(rf.post("/", {"damaged": ["not-an-id"]}), rental_id=uuid4())

        assert response.status_code == 400

    def test_already_returned_rental_shows_the_error(self, rf):
        error = RentalAlreadyReturned("Rental is already returned.")
        view = ReturnRentalView.as_view(return_rental=lambda: Recorder(error=error))

        response = view(rf.post("/", headers=HTMX), rental_id=uuid4())

        assert "Rental is already returned." in html(response)

    def test_unknown_rental_is_a_404(self, rf):
        view = ReturnRentalView.as_view(
            return_rental=lambda: Recorder(error=RentalNotFound("unknown"))
        )

        with pytest.raises(Http404):
            view(rf.post("/"), rental_id=uuid4())
