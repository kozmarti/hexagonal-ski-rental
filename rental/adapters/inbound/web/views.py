# Views are inbound adapters. They never import bootstrap.py: each view receives the
# use cases it needs (as factories returning inbound ports) through as_view() in config/urls.py.
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from rental.adapters.inbound.web.forms import EquipmentFilterForm, RegisterEquipmentForm
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipment
from rental.application.ports.inbound.register_equipment import RegisterEquipment
from rental.domain.exceptions import DomainError


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
