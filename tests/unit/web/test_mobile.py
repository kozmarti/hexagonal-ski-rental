"""The phone layout: the tab bar at the bottom and the lists shown as cards.
The layout itself is CSS (app.css); these tests check the HTML it relies on.
Fake use cases injected: no database, no bootstrap."""

from datetime import date

import pytest
from django.urls import resolve

from rental.adapters.inbound.web.templatetags.rental_tags import menu_section
from rental.adapters.inbound.web.views import DashboardView, InventoryView, MaintenanceView
from rental.application.ports.inbound.get_dashboard import Dashboard
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from tests.unit.factories import make_boots, make_skis
from tests.unit.fakes import Recorder, html

TODAY = date(2026, 12, 23)
EMPTY = Dashboard(TODAY, [], [], [], [])


def tab_bar(content: str) -> str:
    """The tab bar's HTML only."""
    start = content.index('<nav class="tab-bar"')
    return content[start : content.index("</nav>", start)]


@pytest.mark.parametrize(
    ("url_name", "section"),
    [
        ("dashboard", "dashboard"),
        ("rentals", "rentals"),
        ("rental-new", "rentals"),
        ("rental-import-fit", "rentals"),
        ("inventory-labels", "inventory"),
        ("scan-page", "scan"),
        ("scan", "scan"),
        ("maintenance", "maintenance"),
        ("pricing", "pricing"),
        ("api-rentals", ""),
        (None, ""),
    ],
)
def test_each_page_belongs_to_one_menu_section(url_name, section):
    assert menu_section(url_name) == section


class TestTabBar:
    def get(self, rf, path):
        request = rf.get(path)
        request.resolver_match = resolve(path)
        return request

    def test_every_page_has_the_tab_bar_with_scan_in_the_middle(self, rf):
        view = DashboardView.as_view(get_dashboard=lambda: Recorder(EMPTY))

        bar = tab_bar(html(view(self.get(rf, "/"))))

        labels = ["Dashboard", "Rentals", "Scan", "Inventory", "Maintenance"]
        assert [bar.index(f"<span>{label}</span>") for label in labels] == sorted(
            bar.index(f"<span>{label}</span>") for label in labels
        )
        assert 'class="tab-scan"' in bar
        assert "Pricing" not in bar

    def test_the_current_page_is_marked_in_the_tab_bar(self, rf):
        view = MaintenanceView.as_view(list_equipment_in_maintenance=lambda: Recorder([]))

        bar = tab_bar(html(view(self.get(rf, "/maintenance/"))))

        assert bar.count('aria-current="page"') == 1
        assert '/maintenance/" aria-current="page"' in bar

    def test_on_phones_the_top_bar_keeps_only_pricing_and_the_theme_button(self, rf):
        view = DashboardView.as_view(get_dashboard=lambda: Recorder(EMPTY))

        content = html(view(self.get(rf, "/")))
        header = content[content.index('<header class="site-header">') : content.index("</header>")]

        assert header.count('<li class="wide-only">') == 5
        assert '<li><a href="/pricing/"' in header


class TestCards:
    def test_inventory_cells_carry_their_column_name(self, rf):
        view = InventoryView.as_view(
            get_dashboard=lambda: Recorder(EMPTY),
            list_equipment_in_maintenance=lambda: Recorder([]),
            list_available_equipment=lambda: Recorder([EquipmentView.from_entity(make_skis())]),
            register_equipment=lambda: Recorder(),
        )

        content = html(view(rf.get("/inventory/")))

        assert '<table class="striped cards">' in content
        for column in ["Type", "Brand", "Model", "Size", "Range", "Days used"]:
            assert f'<td data-label="{column}">' in content
        assert '<td class="action">' in content  # the QR button, without a label

    def test_maintenance_buttons_are_card_actions(self, rf):
        boots = make_boots()
        boots.rent()
        boots.mark_returned(days=1, damaged=False)
        items = [EquipmentView.from_entity(boots)]
        view = MaintenanceView.as_view(list_equipment_in_maintenance=lambda: Recorder(items))

        content = html(view(rf.get("/maintenance/")))

        assert '<table class="striped cards">' in content
        assert content.count('<td class="action">') == 2  # Done and QR
