"""'Fit by hand' in a dialog after a group import, with fake use cases: no database."""

from datetime import date
from uuid import uuid4

from rental.adapters.inbound.web.views import FitChildView
from rental.application.ports.inbound.create_rental import CreateRentalResult
from rental.domain.exceptions import EquipmentNotAvailable
from tests.unit.factories import eur
from tests.unit.fakes import HTMX, Recorder, html
from tests.unit.web.test_rental_views import BOOTS, SKIS, FakeListAvailableEquipment, recommendation

FRIDAY = date(2026, 12, 25)


def fit_view(create):
    return FitChildView.as_view(
        recommend_equipment=lambda: Recorder(recommendation()),
        list_available_equipment=FakeListAvailableEquipment,
        create_rental=lambda: create,
    )


def choose(rf, create, equipment):
    form = {
        "line": "6",
        "equipment": [str(item.id) for item in equipment],
        "end_date": "2026-12-25",
    }
    return fit_view(create)(rf.post("/", form, headers=HTMX), customer_id=uuid4())


def test_dialog_targets_the_childs_result_cell_and_keeps_the_import_last_day(rf):
    request = rf.get("/", {"line": "6", "end_date": "2026-12-25"}, headers=HTMX)

    content = html(fit_view(Recorder())(request, customer_id=uuid4()))

    assert 'hx-target="#import-result-6"' in content
    assert 'value="2026-12-25"' in content
    assert f'value="{SKIS.id}"' in content
    assert "<nav>" not in content


def test_dialog_without_a_line_number_is_a_bad_request(rf):
    response = fit_view(Recorder())(rf.get("/", headers=HTMX), customer_id=uuid4())

    assert response.status_code == 400


def test_created_rental_replaces_only_the_result_cell(rf):
    create = Recorder(CreateRentalResult(uuid4(), date(2026, 12, 20), FRIDAY, eur("180")))

    response = choose(rf, create, [SKIS, BOOTS])

    assert html(response).strip() == "✅ Skis 160 cm, Boots 26.5 mondopoint · 180.00 EUR"
    assert "HX-Retarget" not in response
    assert create.calls[0].equipment_ids == (SKIS.id, BOOTS.id)


def test_business_error_stays_in_the_dialog_with_the_choice_kept(rf):
    create = Recorder(error=EquipmentNotAvailable("Not available."))

    response = choose(rf, create, [SKIS])

    assert response["HX-Retarget"] == "#fit-dialog-content"
    assert response["HX-Reswap"] == "innerHTML"
    assert "Not available." in html(response)
    assert f'value="{SKIS.id}" checked' in html(response)
