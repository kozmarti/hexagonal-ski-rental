# Views are inbound adapters. They never import bootstrap.py: each view receives the
# use cases it needs (as factories returning inbound ports) through as_view() in config/urls.py.
from collections.abc import Callable
from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from rental.adapters.inbound.web.forms import (
    CreateRentalForm,
    EquipmentFilterForm,
    RegisterCustomerForm,
    RegisterEquipmentForm,
    parse_ids,
)
from rental.application.ports.inbound.complete_maintenance import (
    CompleteMaintenance,
    CompleteMaintenanceCommand,
)
from rental.application.ports.inbound.create_rental import CreateRental
from rental.application.ports.inbound.get_dashboard import GetDashboard
from rental.application.ports.inbound.list_available_equipment import (
    ListAvailableEquipment,
    ListAvailableEquipmentQuery,
)
from rental.application.ports.inbound.list_equipment_in_maintenance import (
    ListEquipmentInMaintenance,
)
from rental.application.ports.inbound.recommend_equipment import (
    RecommendEquipment,
    RecommendEquipmentQuery,
)
from rental.application.ports.inbound.register_customer import RegisterCustomer
from rental.application.ports.inbound.register_equipment import RegisterEquipment
from rental.application.ports.inbound.return_rental import ReturnRental, ReturnRentalCommand
from rental.domain.equipment import EquipmentType
from rental.domain.exceptions import (
    CustomerNotFound,
    DomainError,
    EquipmentNotFound,
    RentalNotFound,
)


def is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


def home(request):
    return render(request, "rental/home.html")


class InventoryView(View):
    list_available_equipment: Callable[[], ListAvailableEquipment] | None = None
    register_equipment: Callable[[], RegisterEquipment] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        filters = EquipmentFilterForm(request.GET)
        items = self.list_available_equipment().execute(filters.to_query())
        if is_htmx(request):
            return render(request, "rental/inventory/_list.html", {"items": items})
        return self._page(request, filters, RegisterEquipmentForm(), items)

    def post(self, request: HttpRequest) -> HttpResponse:
        form = RegisterEquipmentForm(request.POST)
        if form.is_valid():
            try:
                self.register_equipment().execute(form.to_command())
            except DomainError as error:
                form.add_error(None, str(error))
            else:
                return self._registered(request)

        if is_htmx(request):
            return render(request, "rental/inventory/_form.html", {"form": form})
        filters = EquipmentFilterForm()
        items = self.list_available_equipment().execute(filters.to_query())
        return self._page(request, filters, form, items)

    def _registered(self, request: HttpRequest) -> HttpResponse:
        if not is_htmx(request):
            return redirect("inventory")
        items = self.list_available_equipment().execute(EquipmentFilterForm().to_query())
        context = {"form": RegisterEquipmentForm(), "items": items, "registered": True}
        return render(request, "rental/inventory/_registered.html", context)

    def _page(self, request, filters, form, items) -> HttpResponse:
        context = {"filters": filters, "form": form, "items": items}
        return render(request, "rental/inventory/page.html", context)


def _uuid_param(request: HttpRequest, name: str) -> UUID | None:
    try:
        return UUID(request.GET.get(name, ""))
    except ValueError:
        return None


class RentalsView(View):
    """Active rentals, each with a return form."""

    get_dashboard: Callable[[], GetDashboard] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {
            "rentals": self.get_dashboard().execute().active_rentals,
            "created": _uuid_param(request, "created"),
            "returned": _uuid_param(request, "returned"),
        }
        return render(request, "rental/rentals/list.html", context)


class NewRentalView(View):
    """Step 1 at the counter: register the customer."""

    register_customer: Callable[[], RegisterCustomer] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "rental/rentals/new.html", {"form": RegisterCustomerForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = RegisterCustomerForm(request.POST)
        if form.is_valid():
            try:
                result = self.register_customer().execute(form.to_command())
            except DomainError as error:
                form.add_error(None, str(error))
            else:
                return redirect("rental-equipment", customer_id=result.customer_id)
        return render(request, "rental/rentals/new.html", {"form": form})


class ChooseEquipmentView(View):
    """Step 2 at the counter: recommendation, choice of items, last day, then the rental."""

    recommend_equipment: Callable[[], RecommendEquipment] | None = None
    list_available_equipment: Callable[[], ListAvailableEquipment] | None = None
    create_rental: Callable[[], CreateRental] | None = None

    def get(self, request: HttpRequest, customer_id: UUID) -> HttpResponse:
        sections = self._sections(customer_id)
        form = CreateRentalForm(initial={"end_date": timezone.localdate()})
        return self._page(request, customer_id, sections, form)

    def post(self, request: HttpRequest, customer_id: UUID) -> HttpResponse:
        sections = self._sections(customer_id)
        form = CreateRentalForm(request.POST, item_ids=sections["item_ids"])
        if form.is_valid():
            try:
                result = self.create_rental().execute(form.to_command(customer_id))
            except DomainError as error:
                form.add_error(None, str(error))
            else:
                return redirect(f"{reverse('rentals')}?created={result.rental_id}")
        return self._page(request, customer_id, sections, form)

    def _sections(self, customer_id: UUID) -> dict:
        try:
            recommendation = self.recommend_equipment().execute(
                RecommendEquipmentQuery(customer_id)
            )
        except CustomerNotFound:
            raise Http404("Unknown customer.") from None
        listing = self.list_available_equipment()
        accessories = [
            *listing.execute(ListAvailableEquipmentQuery(type=EquipmentType.HELMET)),
            *listing.execute(ListAvailableEquipmentQuery(type=EquipmentType.POLES)),
        ]
        shown = [*recommendation.skis, *recommendation.snowboards, *recommendation.boots]
        shown_ids = {item.id for item in [*shown, *accessories]}
        others = [
            item
            for item in listing.execute(ListAvailableEquipmentQuery())
            if item.id not in shown_ids
        ]
        return {
            "recommendation": recommendation,
            "accessories": accessories,
            "others": others,
            "item_ids": [*shown_ids, *(item.id for item in others)],
        }

    def _page(self, request, customer_id, sections, form) -> HttpResponse:
        context = {
            **sections,
            "customer_id": customer_id,
            "form": form,
            "selected": set(request.POST.getlist("equipment")),
        }
        return render(request, "rental/rentals/choose.html", context)


class ReturnRentalView(View):
    return_rental: Callable[[], ReturnRental] | None = None

    def post(self, request: HttpRequest, rental_id: UUID) -> HttpResponse:
        try:
            damaged = parse_ids(request.POST.getlist("damaged"))
        except ValueError:
            return HttpResponseBadRequest("Invalid equipment id.")
        try:
            result = self.return_rental().execute(ReturnRentalCommand(rental_id, damaged))
        except RentalNotFound:
            raise Http404("Unknown rental.") from None
        except DomainError as error:
            if is_htmx(request):
                return render(request, "rental/rentals/_return_error.html", {"error": error})
            return HttpResponseBadRequest(str(error))

        if is_htmx(request):
            return render(request, "rental/rentals/_returned.html", {"result": result})
        return redirect(f"{reverse('rentals')}?returned={result.rental_id}")


class MaintenanceView(View):
    """Items waiting for maintenance, repairs first."""

    list_equipment_in_maintenance: Callable[[], ListEquipmentInMaintenance] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {
            "items": self.list_equipment_in_maintenance().execute(),
            "done": _uuid_param(request, "done"),
        }
        return render(request, "rental/maintenance/list.html", context)


class CompleteMaintenanceView(View):
    complete_maintenance: Callable[[], CompleteMaintenance] | None = None

    def post(self, request: HttpRequest, equipment_id: UUID) -> HttpResponse:
        try:
            self.complete_maintenance().execute(CompleteMaintenanceCommand(equipment_id))
        except EquipmentNotFound:
            raise Http404("Unknown equipment.") from None
        except DomainError as error:
            if is_htmx(request):
                return render(request, "rental/maintenance/_row_error.html", {"error": error})
            return HttpResponseBadRequest(str(error))

        if is_htmx(request):
            return render(request, "rental/maintenance/_done.html")
        return redirect(f"{reverse('maintenance')}?done={equipment_id}")
