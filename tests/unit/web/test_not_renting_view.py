"""'Not renting' after a group import, with a fake use case: no database."""

from uuid import uuid4

import pytest
from django.http import Http404

from rental.adapters.inbound.web.views import NotRentingView
from rental.application.ports.inbound.remove_customer import RemoveCustomerResult
from rental.domain.exceptions import CustomerHasRentals, CustomerNotFound
from tests.unit.fakes import HTMX, Recorder, html


def not_renting(rf, recorder, customer_id):
    view = NotRentingView.as_view(remove_customer=lambda: recorder)
    return view(rf.post("/", headers=HTMX), customer_id=customer_id)


def test_customer_is_removed_and_the_cell_says_so(rf):
    customer_id = uuid4()
    recorder = Recorder(RemoveCustomerResult(customer_id))

    response = not_renting(rf, recorder, customer_id)

    assert html(response).strip() == "Not renting. Customer removed."
    assert recorder.calls[0].customer_id == customer_id


def test_customer_with_rentals_is_refused_without_changing_the_row(rf):
    recorder = Recorder(error=CustomerHasRentals("Inès has rentals and cannot be removed."))

    response = not_renting(rf, recorder, uuid4())

    assert response.status_code == 409
    assert html(response) == "Inès has rentals and cannot be removed."


def test_unknown_customer_is_a_404(rf):
    with pytest.raises(Http404):
        not_renting(rf, Recorder(error=CustomerNotFound("unknown")), uuid4())
