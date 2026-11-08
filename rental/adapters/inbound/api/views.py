"""JSON API inbound adapter, e.g. for a self-service tablet in the shop.

Like the web views, each endpoint only knows inbound ports: the use cases are injected
through as_view() in config/urls.py.

No CSRF token: CSRF protects cookie-based sessions, and this API uses none. There is no
authentication yet either (staff authentication is a later business change), so the API is
meant for the shop's own network only.
"""

from collections.abc import Callable
from uuid import UUID

from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from rental.adapters.inbound.api import serialization
from rental.adapters.inbound.api.parsing import (
    InvalidRequest,
    create_rental_command,
    equipment_query,
    json_body,
    register_customer_command,
    return_rental_command,
)
from rental.application.ports.inbound.create_rental import CreateRental
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipment
from rental.application.ports.inbound.recommend_equipment import (
    RecommendEquipment,
    RecommendEquipmentQuery,
)
from rental.application.ports.inbound.register_customer import RegisterCustomer
from rental.application.ports.inbound.return_rental import ReturnRental
from rental.domain.exceptions import (
    CustomerNotFound,
    DomainError,
    EquipmentNotFound,
    RentalNotFound,
)

NOT_FOUND = (CustomerNotFound, EquipmentNotFound, RentalNotFound)


@method_decorator(csrf_exempt, name="dispatch")
class ApiView(View):
    """Maps errors to HTTP statuses: 400 bad request, 404 not found, 409 business rule."""

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except InvalidRequest as error:
            return JsonResponse({"errors": error.errors}, status=400)
        except NOT_FOUND as error:
            return JsonResponse({"error": str(error)}, status=404)
        except DomainError as error:
            return JsonResponse({"error": str(error)}, status=409)

    def http_method_not_allowed(self, request, *args, **kwargs):
        return JsonResponse({"error": "Method not allowed."}, status=405)


class EquipmentApi(ApiView):
    list_available_equipment: Callable[[], ListAvailableEquipment] | None = None

    def get(self, request: HttpRequest) -> JsonResponse:
        items = self.list_available_equipment().execute(equipment_query(request.GET))
        return JsonResponse({"items": [serialization.equipment(item) for item in items]})


class CustomersApi(ApiView):
    register_customer: Callable[[], RegisterCustomer] | None = None

    def post(self, request: HttpRequest) -> JsonResponse:
        command = register_customer_command(json_body(request.body))
        result = self.register_customer().execute(command)
        return JsonResponse({"id": str(result.customer_id)}, status=201)


class RecommendationApi(ApiView):
    recommend_equipment: Callable[[], RecommendEquipment] | None = None

    def get(self, request: HttpRequest, customer_id: UUID) -> JsonResponse:
        result = self.recommend_equipment().execute(RecommendEquipmentQuery(customer_id))
        return JsonResponse(serialization.recommendation(result))


class RentalsApi(ApiView):
    create_rental: Callable[[], CreateRental] | None = None

    def post(self, request: HttpRequest) -> JsonResponse:
        command = create_rental_command(json_body(request.body))
        result = self.create_rental().execute(command)
        return JsonResponse(serialization.rental_created(result), status=201)


class ReturnRentalApi(ApiView):
    return_rental: Callable[[], ReturnRental] | None = None

    def post(self, request: HttpRequest, rental_id: UUID) -> JsonResponse:
        command = return_rental_command(rental_id, json_body(request.body))
        result = self.return_rental().execute(command)
        return JsonResponse(serialization.rental_returned(result))
