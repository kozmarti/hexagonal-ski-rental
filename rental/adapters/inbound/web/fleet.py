"""The "fleet": every item in use with its status, available, rented or in maintenance.

Each existing use case lists one state, so the fleet combines three of them; the core is
unchanged. Used by the complete Inventory page, the labels, the QR dialog and the scan pages.
Retired items are not listed: no use case lists them (and none retires an item yet).
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from django import forms
from django.http import Http404
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
from rental.domain.equipment import EquipmentType

AVAILABLE, RENTED, MAINTENANCE = "available", "rented", "maintenance"
PLURALS = {
    EquipmentType.SKIS: "skis",
    EquipmentType.SNOWBOARD: "snowboards",
    EquipmentType.BOOTS: "boots",
    EquipmentType.HELMET: "helmets",
    EquipmentType.POLES: "poles",
}


@dataclass(frozen=True)
class FleetItem:
    item: EquipmentView
    status: str
    rental: RentalView | None = None


@dataclass(frozen=True)
class FleetTotals:
    total: int
    available: int
    rented: int
    maintenance: int
    repairs: int

    @classmethod
    def of(cls, entries: list[FleetItem]) -> "FleetTotals":
        statuses = [entry.status for entry in entries]
        return cls(
            total=len(entries),
            available=statuses.count(AVAILABLE),
            rented=statuses.count(RENTED),
            maintenance=statuses.count(MAINTENANCE),
            repairs=sum(e.status == MAINTENANCE and e.item.needs_repair for e in entries),
        )


class FleetView(View):
    """Base for views that need every item in use."""

    get_dashboard: Callable[[], GetDashboard] | None = None
    list_equipment_in_maintenance: Callable[[], ListEquipmentInMaintenance] | None = None
    list_available_equipment: Callable[[], ListAvailableEquipment] | None = None

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


class FleetFilterForm(EquipmentFilterForm):
    """Type and range filters, plus the status and, for a single label, one item."""

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

    def title(self) -> str:
        """What the filters show, e.g. "Rented sport skis", "Boots in maintenance",
        "All equipment"."""
        data = self.cleaned_data if self.is_valid() else {}
        query = self.to_query()
        status = data.get("status")
        words = [{AVAILABLE: "available", RENTED: "rented"}.get(status, "")]
        words.append(str(query.range) if query.range else "")
        words.append(PLURALS[query.type] if query.type else "equipment")
        words.append("in maintenance" if status == MAINTENANCE else "")
        title = " ".join(word for word in words if word)
        return title.capitalize() if status or query.range or query.type else "All equipment"

    def keeps(self, entry: FleetItem, with_status: bool = True) -> bool:
        """`with_status=False` ignores the status filter: totals per status use it."""
        data = self.cleaned_data if self.is_valid() else {}
        query = self.to_query()
        return (
            (not data.get("item") or entry.item.id == data["item"])
            and (not with_status or not data.get("status") or entry.status == data["status"])
            and (query.type is None or entry.item.type is query.type)
            and (query.range is None or entry.item.range is query.range)
        )
