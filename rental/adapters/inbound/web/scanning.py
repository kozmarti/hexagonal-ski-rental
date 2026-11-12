"""QR code labels and scanning: stickers, the QR dialog, the Scan page and a scanned item's page.

Each sticker holds a link to the item's page (`/scan/<id>/`), so a phone's own camera app can
open it. Items come from the "fleet" (fleet.py), which combines existing use cases: the core
does not know about QR codes.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import segno
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.safestring import SafeString, mark_safe
from django.views import View

from rental.adapters.inbound.web.fleet import FleetFilterForm, FleetItem, FleetView
from rental.adapters.inbound.web.pagination import paginate

# One page of labels is one A4 sheet of 50 x 30 mm stickers (4 columns, 9 rows).
LABELS_PER_SHEET = 36


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
class Label:
    entry: FleetItem
    url: str
    qr: SafeString


class LabelledFleetView(FleetView):
    """A fleet view that also builds QR labels, with the shop's address in their links."""

    labels_base_url: Callable[[], str] | None = None

    def label(self, request: HttpRequest, entry: FleetItem) -> Label:
        path = reverse("scan", kwargs={"equipment_id": entry.item.id})
        base_url = self.labels_base_url() if self.labels_base_url else ""
        url = f"{base_url.rstrip('/')}{path}" if base_url else request.build_absolute_uri(path)
        return Label(entry=entry, url=url, qr=qr_svg(url))


class LabelsView(LabelledFleetView):
    """Printable sheets of QR stickers, for any item in use or for one item (`?item=<id>`).
    One page is one A4 sheet."""

    def get(self, request: HttpRequest) -> HttpResponse:
        filters = FleetFilterForm(request.GET)
        entries = [entry for entry in self.fleet() if filters.keeps(entry)]
        pagination = paginate(request, entries, per_page=LABELS_PER_SHEET)
        context = {
            "filters": filters,
            "pagination": pagination,
            "labels": [self.label(request, entry) for entry in pagination.page],
        }
        return render(request, "rental/inventory/labels.html", context)


class QrDialogView(LabelledFleetView):
    """The content of the QR dialog opened by an item's "QR" button."""

    def get(self, request: HttpRequest, equipment_id: UUID) -> HttpResponse:
        label = self.label(request, self.entry(equipment_id))
        return render(request, "rental/_qr_dialog.html", {"label": label})


class ScanPageView(View):
    """The "Scan" menu page: scanning an item opens its page."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "rental/scan_page.html")


class ScanItemView(LabelledFleetView):
    """The page a scanned sticker opens: the item, and the one action that makes sense now."""

    def get(self, request: HttpRequest, equipment_id: UUID) -> HttpResponse:
        entry = self.entry(equipment_id)
        context = {"item": entry.item, "status": entry.status, "rental": entry.rental}
        return render(request, "rental/scan_item.html", context)
