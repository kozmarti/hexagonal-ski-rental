"""QR labels, the QR dialog, the Scan page and scanned item pages, with fake use cases
injected: no database, no bootstrap."""

from datetime import date
from uuid import uuid4

import pytest
from django.http import Http404

from rental.adapters.inbound.web import scanning
from rental.adapters.inbound.web.fleet import AVAILABLE, FleetItem
from rental.adapters.inbound.web.scanning import qr_svg
from rental.adapters.inbound.web.views import (
    InventoryView,
    MaintenanceView,
    NewRentalView,
    RentalsView,
)
from rental.application.ports.inbound.get_dashboard import Dashboard, RentalView
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.inbound.register_customer import RegisterCustomerResult
from tests.unit.factories import eur, make_boots, make_helmet, make_skis
from tests.unit.fakes import Recorder, html
from tests.unit.web.test_rental_views import SKIS, choose_view

TODAY = date(2026, 12, 20)


def view_of(item):
    return EquipmentView.from_entity(item)


def serviced(damaged=False):
    skis = make_skis()
    skis.rent()
    skis.mark_returned(days=2, damaged=damaged)
    return view_of(skis)


def rental_with(*items):
    return RentalView(uuid4(), uuid4(), "Alex Martin", list(items), TODAY, TODAY, eur("40"))


class Fleet:
    """One item in each state: available boots, rented skis, a helmet in maintenance."""

    def __init__(self):
        self.available = view_of(make_boots())
        self.rented = view_of(make_skis())
        self.rental = rental_with(self.rented)
        helmet = make_helmet()
        helmet.rent()
        helmet.mark_returned(days=1, damaged=True)
        self.in_maintenance = view_of(helmet)

    def view(self, view_class, base_url=""):
        dashboard = Dashboard(TODAY, [self.rental], [], [], [])
        return view_class.as_view(
            get_dashboard=lambda: Recorder(dashboard),
            list_equipment_in_maintenance=lambda: Recorder([self.in_maintenance]),
            list_available_equipment=lambda: Recorder([self.available]),
            labels_base_url=lambda: base_url,
        )


@pytest.fixture
def fleet():
    return Fleet()


class TestLabels:
    def test_every_item_in_use_gets_a_sticker_whatever_its_status(self, rf, fleet):
        content = html(fleet.view(scanning.LabelsView)(rf.get("/")))

        assert content.count('<div class="label">') == 3
        for item in (fleet.available, fleet.rented, fleet.in_maintenance):
            assert str(item.id)[:8] in content

    def test_labels_can_be_filtered_by_status(self, rf, fleet):
        content = html(fleet.view(scanning.LabelsView)(rf.get("/", {"status": "rented"})))

        assert content.count('<div class="label">') == 1
        assert str(fleet.rented.id)[:8] in content

    def test_one_label_can_be_printed_alone(self, rf, fleet):
        request = rf.get("/", {"item": str(fleet.in_maintenance.id)})

        content = html(fleet.view(scanning.LabelsView)(request))

        assert content.count('<div class="label">') == 1
        assert "One label only." in content

    def test_stickers_link_to_the_configured_shop_address(self, rf, fleet):
        view = scanning.LabelsView(labels_base_url=lambda: "http://192.168.1.20:8000/")

        label = view.label(rf.get("/"), FleetItem(fleet.available, AVAILABLE))

        assert label.url == f"http://192.168.1.20:8000/scan/{fleet.available.id}/"

    def test_without_an_address_the_printing_page_address_is_used(self, rf, fleet):
        view = scanning.LabelsView(labels_base_url=lambda: "")

        label = view.label(rf.get("/"), FleetItem(fleet.available, AVAILABLE))

        assert label.url == f"http://testserver/scan/{fleet.available.id}/"


class TestQrCodes:
    def test_qr_codes_are_inline_svg(self):
        assert qr_svg("http://shop/scan/1/").startswith("<svg")

    def test_qr_codes_scale_instead_of_being_cropped(self):
        # With a fixed width and height, CSS resizing crops the code and a corner is lost.
        svg = qr_svg("http://shop/scan/1/")

        assert "viewBox" in svg
        assert 'width="' not in svg.split(">", 1)[0]

    def test_qr_codes_have_a_solid_white_background_to_read_in_dark_mode(self):
        # A transparent background shows black modules on a dark page: unreadable.
        assert "#fff" in qr_svg("http://shop/scan/1/").lower()

    def test_the_qr_dialog_shows_the_code_status_and_print_link(self, rf, fleet):
        view = fleet.view(scanning.QrDialogView)

        content = html(view(rf.get("/"), equipment_id=fleet.rented.id))

        assert "<svg" in content
        assert "rented by Alex Martin" in content
        assert f"/inventory/labels/?item={fleet.rented.id}" in content

    def test_every_list_has_a_qr_button_per_item(self, rf, fleet):
        dashboard = Dashboard(TODAY, [fleet.rental], [], [], [])
        inventory = InventoryView.as_view(
            get_dashboard=lambda: Recorder(dashboard),
            list_equipment_in_maintenance=lambda: Recorder([fleet.in_maintenance]),
            list_available_equipment=lambda: Recorder([fleet.available]),
            register_equipment=lambda: Recorder(),
        )
        maintenance = MaintenanceView.as_view(
            list_equipment_in_maintenance=lambda: Recorder([fleet.in_maintenance])
        )
        rentals = RentalsView.as_view(get_dashboard=lambda: Recorder(dashboard))

        assert f"/equipment/{fleet.available.id}/qr/" in html(inventory(rf.get("/")))
        assert f"/equipment/{fleet.in_maintenance.id}/qr/" in html(maintenance(rf.get("/")))
        assert f"/equipment/{fleet.rented.id}/qr/" in html(rentals(rf.get("/")))

    def test_the_qr_button_never_inherits_the_swap_of_the_form_around_it(self, rf, fleet):
        # Bug: on Rentals the button sits in a return form with hx-swap="outerHTML". Inherited,
        # it replaced the dialog's content area itself, so a second QR dialog never opened.
        dashboard = Dashboard(TODAY, [fleet.rental], [], [], [])
        rentals = RentalsView.as_view(get_dashboard=lambda: Recorder(dashboard))

        content = html(rentals(rf.get("/")))
        button = content.split('class="outline secondary qr-button"', 1)[1].split(">", 1)[0]

        assert 'hx-target="#qr-dialog-content"' in button
        assert 'hx-swap="innerHTML"' in button


class TestScanItemPage:
    def test_a_rented_item_offers_to_return_its_whole_rental(self, rf, fleet):
        view = fleet.view(scanning.ScanItemView)

        content = html(view(rf.get("/"), equipment_id=fleet.rented.id))

        assert "Rented by <strong>Alex Martin</strong>" in content
        assert f'action="/rentals/{fleet.rental.id}/return/"' in content

    def test_an_item_in_maintenance_offers_to_finish_it(self, rf, fleet):
        view = fleet.view(scanning.ScanItemView)

        content = html(view(rf.get("/"), equipment_id=fleet.in_maintenance.id))

        assert "Waiting for a repair" in content
        assert f'action="/maintenance/{fleet.in_maintenance.id}/done/"' in content

    def test_an_available_item_can_be_rented_with_the_item_carried_along(self, rf, fleet):
        view = fleet.view(scanning.ScanItemView)

        content = html(view(rf.get("/"), equipment_id=fleet.available.id))

        assert "Available." in content
        assert f"/rentals/new/?item={fleet.available.id}" in content

    def test_an_unknown_or_retired_item_is_a_404(self, rf, fleet):
        with pytest.raises(Http404):
            fleet.view(scanning.ScanItemView)(rf.get("/"), equipment_id=uuid4())


class TestScanFields:
    def test_the_scan_page_opens_the_scanned_items_page(self, rf):
        content = html(scanning.ScanPageView.as_view()(rf.get("/scan/")))

        assert 'data-scan="goto"' in content
        assert 'data-scan-url="/scan/00000000-0000-0000-0000-000000000000/"' in content
        assert "rental/scan.js" in content

    def test_the_counter_page_ticks_scanned_items(self, rf):
        view, _ = choose_view()

        assert 'data-scan="tick"' in html(view(rf.get("/"), customer_id=uuid4()))

    def test_rentals_and_maintenance_have_no_scan_field_any_more(self, rf, fleet):
        maintenance = MaintenanceView.as_view(
            list_equipment_in_maintenance=lambda: Recorder([serviced()])
        )
        dashboard = Dashboard(TODAY, [fleet.rental], [], [], [])
        rentals = RentalsView.as_view(get_dashboard=lambda: Recorder(dashboard))

        assert "data-scan=" not in html(maintenance(rf.get("/")))
        assert "data-scan=" not in html(rentals(rf.get("/")))


class TestRentIt:
    CUSTOMER = {
        "name": "Alex Martin",
        "height_cm": "175",
        "boot_size": "26.5",
        "skill_level": "intermediate",
    }

    def test_the_scanned_item_is_carried_through_the_customer_step(self, rf):
        item_id, customer_id = uuid4(), uuid4()
        register = Recorder(RegisterCustomerResult(customer_id))
        view = NewRentalView.as_view(register_customer=lambda: register)

        page = html(view(rf.get("/", {"item": str(item_id)})))
        response = view(rf.post("/", {**self.CUSTOMER, "item": str(item_id)}))

        assert f'name="item" value="{item_id}"' in page
        assert "1 scanned item will already be ticked" in page
        assert response.url == f"/rentals/new/{customer_id}/?item={item_id}"

    def test_the_carried_item_is_ticked_on_the_equipment_step(self, rf):
        view, _ = choose_view()

        content = html(view(rf.get("/", {"item": str(SKIS.id)}), customer_id=uuid4()))

        assert f'value="{SKIS.id}" checked' in content

    def test_a_wrong_item_id_is_simply_ignored(self, rf):
        view = NewRentalView.as_view(register_customer=lambda: Recorder())

        assert "scanned item" not in html(view(rf.get("/", {"item": "not-an-id"})))
