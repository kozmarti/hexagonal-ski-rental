# Views are inbound adapters. They never import bootstrap.py: each view receives the
# use cases it needs (as factories returning inbound ports) through as_view() in config/urls.py.
from collections.abc import Callable
from urllib.parse import urlencode
from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from rental.adapters.inbound.csv_import.importer import (
    CsvFormatError,
    GroupUseCases,
    import_group,
    parse,
)
from rental.adapters.inbound.web.fleet import FleetFilterForm, FleetTotals, FleetView
from rental.adapters.inbound.web.forms import (
    CreateRentalForm,
    ImportGroupForm,
    RegisterCustomerForm,
    RegisterEquipmentForm,
    parse_ids,
)
from rental.adapters.inbound.web.pagination import paginate
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
from rental.application.ports.inbound.remove_customer import (
    RemoveCustomer,
    RemoveCustomerCommand,
)
from rental.application.ports.inbound.return_rental import ReturnRental, ReturnRentalCommand
from rental.domain.equipment import EquipmentType
from rental.domain.exceptions import (
    CustomerNotFound,
    DomainError,
    EquipmentNotFound,
    RentalNotFound,
)
from rental.domain.money import Money


def is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


class DashboardView(View):
    """The home page: what is out, due back today, overdue and in maintenance."""

    get_dashboard: Callable[[], GetDashboard] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {"dashboard": self.get_dashboard().execute()}
        return render(request, "rental/dashboard.html", context)


class InventoryView(FleetView):
    """The complete inventory: every item in use with its status, filters, totals, pages."""

    register_equipment: Callable[[], RegisterEquipment] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        filters = FleetFilterForm(request.GET)
        if is_htmx(request):
            return render(request, "rental/inventory/_list.html", self._list(request, filters))
        return self._page(request, filters, RegisterEquipmentForm())

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
        return self._page(request, FleetFilterForm(), form)

    def _list(self, request: HttpRequest, filters: FleetFilterForm) -> dict:
        """Totals count every status (the status filter only narrows the table)."""
        entries = [entry for entry in self.fleet() if filters.keeps(entry, with_status=False)]
        shown = [entry for entry in entries if filters.keeps(entry)]
        return {
            "title": filters.title(),
            "totals": FleetTotals.of(entries),
            "pagination": paginate(request, shown),
        }

    def _registered(self, request: HttpRequest) -> HttpResponse:
        if not is_htmx(request):
            return redirect("inventory")
        context = {
            **self._list(request, FleetFilterForm()),
            "form": RegisterEquipmentForm(),
            "registered": True,
        }
        return render(request, "rental/inventory/_registered.html", context)

    def _page(self, request, filters, form) -> HttpResponse:
        context = {**self._list(request, filters), "filters": filters, "form": form}
        return render(request, "rental/inventory/page.html", context)


def _uuid_param(request: HttpRequest, name: str) -> UUID | None:
    try:
        return UUID(request.GET.get(name, ""))
    except ValueError:
        return None


class RentalsView(View):
    """Active rentals, each with a return form. `?show=due-today` or `?show=overdue` narrows
    the list (the dashboard's "See all" links)."""

    get_dashboard: Callable[[], GetDashboard] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        dashboard = self.get_dashboard().execute()
        show = request.GET.get("show", "all")
        rentals = {
            "due-today": dashboard.due_back_today,
            "overdue": dashboard.overdue,
        }.get(show, dashboard.active_rentals)
        created = _uuid_param(request, "created")
        context = {
            "dashboard": dashboard,
            "show": show if show in ("due-today", "overdue") else "all",
            "pagination": paginate(request, rentals),
            "overdue_ids": {rental.id for rental in dashboard.overdue},
            "due_today_ids": {rental.id for rental in dashboard.due_back_today},
            "created": next((r for r in dashboard.active_rentals if r.id == created), None),
            "returned": _uuid_param(request, "returned"),
        }
        return render(request, "rental/rentals/list.html", context)


def _item_ids(values) -> list[UUID]:
    """Items already chosen before the equipment step (e.g. "Rent it" on a scanned item)."""
    try:
        return list(dict.fromkeys(parse_ids(values)))
    except ValueError:
        return []


def _with_items(url: str, item_ids: list[UUID]) -> str:
    return (
        f"{url}?{urlencode([('item', str(item_id)) for item_id in item_ids])}" if item_ids else url
    )


class NewRentalView(View):
    """Step 1 at the counter: register the customer."""

    register_customer: Callable[[], RegisterCustomer] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {"form": RegisterCustomerForm(), "items": _item_ids(request.GET.getlist("item"))}
        return render(request, "rental/rentals/new.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        form = RegisterCustomerForm(request.POST)
        items = _item_ids(request.POST.getlist("item"))
        if form.is_valid():
            try:
                result = self.register_customer().execute(form.to_command())
            except DomainError as error:
                form.add_error(None, str(error))
            else:
                url = reverse("rental-equipment", kwargs={"customer_id": result.customer_id})
                return redirect(_with_items(url, items))
        return render(request, "rental/rentals/new.html", {"form": form, "items": items})


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
        form = CreateRentalForm(request.POST, item_ids=[item.id for item in sections["items"]])
        if form.is_valid():
            command = form.to_command(customer_id)
            try:
                result = self.create_rental().execute(command)
            except DomainError as error:
                form.add_error(None, str(error))
            else:
                return self._created(request, result, command, sections)
        return self._page(request, customer_id, sections, form)

    def _created(self, request, result, command, sections) -> HttpResponse:
        return redirect(f"{reverse('rentals')}?created={result.rental_id}")

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
            "items": [*shown, *accessories, *others],
        }

    def _page(self, request, customer_id, sections, form) -> HttpResponse:
        # Ticked: the items chosen in this form, or the ones carried from "Rent it" (?item=).
        preselected = [str(item_id) for item_id in _item_ids(request.GET.getlist("item"))]
        context = {
            **sections,
            "customer_id": customer_id,
            "form": form,
            "selected": set(request.POST.getlist("equipment") or preselected),
        }
        return render(request, "rental/rentals/choose.html", context)


class FitChildView(ChooseEquipmentView):
    """'Fit by hand' after a group import: the counter's equipment choice, inside a dialog.

    The report page stays open. On success only the child's result cell is replaced;
    on a business error the dialog stays open and shows it.
    """

    def get(self, request: HttpRequest, customer_id: UUID) -> HttpResponse:
        sections = self._sections(customer_id)
        end_date = request.GET.get("end_date") or timezone.localdate()
        form = CreateRentalForm(initial={"end_date": end_date})
        return self._page(request, customer_id, sections, form)

    def _page(self, request, customer_id, sections, form) -> HttpResponse:
        try:
            line = int(request.GET.get("line") or request.POST.get("line"))
        except (TypeError, ValueError):
            return HttpResponseBadRequest("Missing line number.")
        context = {
            **sections,
            "customer_id": customer_id,
            "form": form,
            "line": line,
            "selected": set(request.POST.getlist("equipment")),
        }
        response = render(request, "rental/rentals/_fit_dialog.html", context)
        if request.method == "POST":
            # The form targets the child's result cell: errors go back into the dialog instead.
            response["HX-Retarget"] = "#fit-dialog-content"
            response["HX-Reswap"] = "innerHTML"
        return response

    def _created(self, request, result, command, sections) -> HttpResponse:
        by_id = {item.id: item for item in sections["items"]}
        context = {"items": [by_id[item_id] for item_id in command.equipment_ids]}
        context["price"] = result.price
        return render(request, "rental/rentals/_import_result.html", context)


class NotRentingView(View):
    """'Not renting' after a group import: the child's customer record is removed."""

    remove_customer: Callable[[], RemoveCustomer] | None = None

    def post(self, request: HttpRequest, customer_id: UUID) -> HttpResponse:
        try:
            self.remove_customer().execute(RemoveCustomerCommand(customer_id))
        except CustomerNotFound:
            raise Http404("Unknown customer.") from None
        except DomainError as error:
            # Not swapped by HTMX (4xx): the row stays pending and the message is shown.
            return HttpResponse(str(error), status=409)
        return render(request, "rental/rentals/_not_renting.html")


class ImportGroupView(View):
    """A ski school class arrives: one CSV line per child, one rental per child."""

    register_customer: Callable[[], RegisterCustomer] | None = None
    recommend_equipment: Callable[[], RecommendEquipment] | None = None
    list_available_equipment: Callable[[], ListAvailableEquipment] | None = None
    create_rental: Callable[[], CreateRental] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        form = ImportGroupForm(initial={"end_date": timezone.localdate()})
        return render(request, "rental/rentals/import.html", {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ImportGroupForm(request.POST, request.FILES)
        context = {"form": form}
        if form.is_valid():
            try:
                members = parse(form.cleaned_data["file"].read().decode("utf-8-sig"))
            except UnicodeDecodeError:
                form.add_error("file", "The file must be a UTF-8 text file.")
            except CsvFormatError as error:
                for problem in error.problems:
                    form.add_error("file", problem)
            else:
                end_date = form.cleaned_data["end_date"]
                lines = import_group(members, end_date, self._use_cases())
                context.update(self._report(lines), end_date=end_date)
        return render(request, "rental/rentals/import.html", context)

    def _use_cases(self) -> GroupUseCases:
        return GroupUseCases(
            register_customer=self.register_customer,
            recommend_equipment=self.recommend_equipment,
            list_available_equipment=self.list_available_equipment,
            create_rental=self.create_rental,
        )

    @staticmethod
    def _report(lines) -> dict:
        rented = [line for line in lines if line.rental_id]
        total = Money.zero()
        for line in rented:
            total = total + line.price
        return {"lines": lines, "rented": len(rented), "total": total}


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
        items = self.list_equipment_in_maintenance().execute()
        context = {
            "pagination": paginate(request, items),
            "total": len(items),
            "repairs": sum(item.needs_repair for item in items),
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
