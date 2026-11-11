"""QR code labels and scanning: stickers, the QR dialog, the Scan page and a scanned item's page.

Each sticker holds a link to the item's page (`/scan/<id>/`), so a phone's own camera app can
open it. Only existing use cases are used, combined into the "fleet": every item in use with
its status. The core does not know about QR codes.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import segno
from django import forms
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.safestring import SafeString, mark_safe
from django.views import View

from rental.adapters.inbound.web.forms import EquipmentFilterForm
from rental.application.ports.inbound.get_dashboard import GetDashboard, RentalView
from rental.application.ports.inbound.list_available_equipment import (
    EquipmentView,
    ListAvailableEquipment,
    ListAvailableEquipmentQuery,
)
from rental.application.ports.inbound.list_equipment_in_maintenance import (
    ListEquipmentInMaintenance,
)

AVAILABLE, RENTED, MAINTENANCE = "available", "rented", "maintenance"


def qr_svg(text: str) -> SafeString:
    """An inline SVG QR code, black on solid white with the standard 4-module quiet zone,
    so it reads on screen in dark mode too. Error correction M: a slightly scratched sticker
    still reads.

    `omitsize` replaces the fixed width and height with a viewBox: the CSS then scales the
    whole code instead of cropping it (a cropped code loses a corner and cannot be read)."""
    qr = segno.make_qr(text, error="m")
    svg = qr.svg_inline(scale=3, border=4, dark="#000000", light="#ffffff", omitsize=True)
    return mark_safe(svg)


@dataclass(frozen=True)
class FleetItem:
    item: EquipmentView
    status: str
    rental: RentalView | None = None


@dataclass(frozen=True)
class Label:
    entry: FleetItem
    url: str
    qr: SafeString


class FleetView(View):
    """Base for views that need every item in use: available, rented and in maintenance.

    Retired items are not listed: no use case lists them (and none retires an item yet).
    """

    get_dashboard: Callable[[], GetDashboard] | None = None
    list_equipment_in_maintenance: Callable[[], ListEquipmentInMaintenance] | None = None
    list_available_equipment: Callable[[], ListAvailableEquipment] | None = None
    labels_base_url: Callable[[], str] | None = None

    def fleet(self) -> list[FleetItem]:
        available = self.list_available_equipment().execute(ListAvailableEquipmentQuery())
        entries = [FleetItem(item, AVAILABLE) for item in available]
        for rental in self.get_dashboard().execute().active_rentals:
            entries += [FleetItem(item, RENTED, rental) for item in rental.equipment]
        for item in self.list_equipment_in_maintenance().execute():
            entries.append(FleetItem(item, MAINTENANCE))
        return sorted(entries, key=lambda entry: (entry.item.type, entry.item.size.value))

    def entry(self, equipment_id: UUID) -> FleetItem:
        for entry in self.fleet():
            if entry.item.id == equipment_id:
                return entry
        raise Http404("Unknown or retired item.")

    def label(self, request: HttpRequest, entry: FleetItem) -> Label:
        path = reverse("scan", kwargs={"equipment_id": entry.item.id})
        base_url = self.labels_base_url() if self.labels_base_url else ""
        url = f"{base_url.rstrip('/')}{path}" if base_url else request.build_absolute_uri(path)
        return Label(entry=entry, url=url, qr=qr_svg(url))


class LabelFilterForm(EquipmentFilterForm):
    status = forms.ChoiceField(
        choices=[
            ("", "All statuses"),
            (AVAILABLE, "Available"),
            (RENTED, "Rented"),
            (MAINTENANCE, "In maintenance"),
        ],
        required=False,
    )
    item = forms.UUIDField(required=False, widget=forms.HiddenInput)

    def keeps(self, entry: FleetItem) -> bool:
        data = self.cleaned_data if self.is_valid() else {}
        query = self.to_query()
        return (
            (not data.get("item") or entry.item.id == data["item"])
            and (not data.get("status") or entry.status == data["status"])
            and (query.type is None or entry.item.type is query.type)
            and (query.range is None or entry.item.range is query.range)
        )


class LabelsView(FleetView):
    """A printable sheet of QR stickers, for any item in use or for one item (`?item=<id>`)."""

    def get(self, request: HttpRequest) -> HttpResponse:
        filters = LabelFilterForm(request.GET)
        entries = [entry for entry in self.fleet() if filters.keeps(entry)]
        context = {"filters": filters, "labels": [self.label(request, e) for e in entries]}
        return render(request, "rental/inventory/labels.html", context)


class QrDialogView(FleetView):
    """The content of the QR dialog opened by an item's "QR" button."""

    def get(self, request: HttpRequest, equipment_id: UUID) -> HttpResponse:
        label = self.label(request, self.entry(equipment_id))
        return render(request, "rental/_qr_dialog.html", {"label": label})


class ScanPageView(View):
    """The "Scan" menu page: scanning an item opens its page."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "rental/scan_page.html")


class ScanItemView(FleetView):
    """The page a scanned sticker opens: the item, and the one action that makes sense now."""

    def get(self, request: HttpRequest, equipment_id: UUID) -> HttpResponse:
        entry = self.entry(equipment_id)
        context = {"item": entry.item, "status": entry.status, "rental": entry.rental}
        return render(request, "rental/scan_item.html", context)
