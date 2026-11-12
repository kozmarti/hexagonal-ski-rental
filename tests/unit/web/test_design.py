"""The design pass: totals, pagination, badges, "See all" links and the theme toggle.
Fake use cases injected: no database, no bootstrap."""

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from rental.adapters.inbound.web import scanning
from rental.adapters.inbound.web.fleet import FleetFilterForm
from rental.adapters.inbound.web.pagination import paginate
from rental.adapters.inbound.web.views import (
    DashboardView,
    InventoryView,
    MaintenanceView,
    RentalsView,
)
from rental.application.ports.inbound.get_dashboard import Dashboard, RentalView
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from tests.unit.factories import eur, make_boots, make_skis
from tests.unit.fakes import Recorder, html

TODAY = date(2026, 12, 23)


def rental(name: str, end: date) -> RentalView:
    skis = EquipmentView.from_entity(make_skis())
    return RentalView(uuid4(), uuid4(), name, [skis], date(2026, 12, 20), end, eur("90"))


def in_maintenance(damaged: bool) -> EquipmentView:
    boots = make_boots()
    boots.rent()
    boots.mark_returned(days=1, damaged=damaged)
    return EquipmentView.from_entity(boots)


class TestPagination:
    def test_a_page_and_links_keeping_the_other_parameters(self, rf):
        pagination = paginate(rf.get("/", {"type": "skis", "page": "2"}), list(range(60)))

        assert list(pagination.page) == list(range(25, 50))
        assert pagination.previous_url == "?type=skis&page=1"
        assert pagination.next_url == "?type=skis&page=3"

    def test_a_wrong_page_number_shows_a_real_page(self, rf):
        assert paginate(rf.get("/", {"page": "abc"}), list(range(3))).page.number == 1
        assert paginate(rf.get("/", {"page": "99"}), list(range(30))).page.number == 2


class TestRentals:
    def view(self, *, active, due_today=(), overdue=()):
        dashboard = Dashboard(TODAY, list(active), list(due_today), list(overdue), [])
        return RentalsView.as_view(get_dashboard=lambda: Recorder(dashboard))

    def test_totals_badges_and_tabs(self, rf):
        late = rental("Léa", date(2026, 12, 21))
        due = rental("Hugo", TODAY)
        out = rental("Alex", date(2026, 12, 25))
        view = self.view(active=[late, due, out], due_today=[due], overdue=[late])

        content = html(view(rf.get("/rentals/")))

        assert "<strong>3 active rentals</strong>" in content
        assert "1 due back today" in content
        assert '<span class="badge badge-overdue">1 overdue</span>' in content
        assert content.count('class="badge badge-overdue">Overdue') == 1
        assert "?show=overdue" in content

    def test_show_overdue_lists_only_the_overdue_rentals(self, rf):
        late, out = rental("Léa", date(2026, 12, 21)), rental("Alex", date(2026, 12, 25))
        view = self.view(active=[late, out], overdue=[late])

        content = html(view(rf.get("/rentals/", {"show": "overdue"})))

        assert "Léa" in content
        assert "<strong>Alex</strong>" not in content

    def test_a_long_list_is_split_into_pages(self, rf):
        view = self.view(active=[rental(f"Customer {n}", date(2026, 12, 25)) for n in range(30)])

        content = html(view(rf.get("/rentals/")))

        assert content.count('<article id="rental-') == 25
        assert "Page 1 of 2" in content


class TestMaintenance:
    def test_totals_and_badges(self, rf):
        items = [in_maintenance(damaged=True), in_maintenance(damaged=False)]
        view = MaintenanceView.as_view(list_equipment_in_maintenance=lambda: Recorder(items))

        content = html(view(rf.get("/maintenance/")))

        assert "<strong>2 items waiting</strong>" in content
        assert "🔧 1 to repair" in content
        assert 'class="badge badge-maintenance">Service' in content


class TestLabels:
    def test_one_page_of_labels_is_one_a4_sheet_of_36_stickers(self, rf):
        available = [EquipmentView.from_entity(make_skis()) for _ in range(40)]
        view = scanning.LabelsView.as_view(
            get_dashboard=lambda: Recorder(Dashboard(TODAY, [], [], [], [])),
            list_equipment_in_maintenance=lambda: Recorder([]),
            list_available_equipment=lambda: Recorder(available),
            labels_base_url=lambda: "",
        )

        content = html(view(rf.get("/inventory/labels/")))

        assert content.count('<div class="label">') == 36
        assert "<strong>40 labels</strong>" in content
        assert "Page 1 of 2" in content


class TestDashboard:
    def test_section_titles_count_and_link_to_the_full_lists(self, rf):
        late = rental("Léa", date(2026, 12, 21))
        items = [in_maintenance(damaged=True), in_maintenance(damaged=False)]
        dashboard = Dashboard(TODAY, [late], [], [late], items)
        view = DashboardView.as_view(get_dashboard=lambda: Recorder(dashboard))

        content = html(view(rf.get("/")))

        assert "<h2>Overdue (1)</h2>" in content
        assert "<h2>Due back today (0)</h2>" in content
        assert "<h2>In maintenance (2, 1 to repair)</h2>" in content
        assert "/rentals/?show=overdue" in content
        assert "See all items in maintenance" in content

    def test_sections_show_their_first_ten_rows(self, rf):
        overdue = [rental(f"Customer {n}", date(2026, 12, 21)) for n in range(12)]
        dashboard = Dashboard(TODAY, overdue, [], overdue, [])
        view = DashboardView.as_view(get_dashboard=lambda: Recorder(dashboard))

        content = html(view(rf.get("/")))

        assert "<h2>Overdue (12)</h2>" in content
        assert content.count("late</span>") == 10


class TestThemeToggle:
    def test_every_page_has_the_toggle_and_applies_the_saved_theme_early(self, rf):
        dashboard = Dashboard(TODAY, [], [], [], [])
        view = DashboardView.as_view(get_dashboard=lambda: Recorder(dashboard))

        content = html(view(rf.get("/")))

        assert "data-theme-toggle" in content
        assert "rental/theme.js" in content
        # Applied in <head>, before the page renders: a saved theme never flashes.
        assert content.index('localStorage.getItem("theme")') < content.index("<body")


class TestInventoryTitle:
    @pytest.mark.parametrize(
        ("filters", "title"),
        [
            ({}, "All equipment"),
            ({"status": "available"}, "Available equipment"),
            ({"status": "rented", "type": "skis", "range": "sport"}, "Rented sport skis"),
            ({"status": "maintenance", "type": "boots"}, "Boots in maintenance"),
            ({"type": "snowboard"}, "Snowboards"),
            ({"range": "premium"}, "Premium equipment"),
        ],
    )
    def test_the_heading_says_what_the_filters_show(self, filters, title):
        assert FleetFilterForm(filters).title() == title

    def test_the_heading_is_inside_the_part_htmx_reloads(self, rf):
        dashboard = Dashboard(TODAY, [], [], [], [])
        view = InventoryView.as_view(
            get_dashboard=lambda: Recorder(dashboard),
            list_equipment_in_maintenance=lambda: Recorder([]),
            list_available_equipment=lambda: Recorder([]),
            register_equipment=lambda: Recorder(),
        )
        request = rf.get("/inventory/", {"type": "boots"}, headers={"HX-Request": "true"})

        assert "<h2>Boots</h2>" in html(view(request))


class TestMessages:
    WEB = Path(__file__).parents[3] / "rental" / "adapters" / "inbound" / "web"

    def test_messages_use_notice_boxes_never_crossed_out_or_underlined_text(self):
        """Pico shows <del> crossed out and <ins> underlined (deleted / inserted text):
        messages after an action use the .notice boxes of app.css instead."""
        files = [*self.WEB.glob("templates/**/*.html"), *self.WEB.glob("static/rental/*.js")]

        offending = [
            file.name
            for file in files
            if any(tag in file.read_text() for tag in ("<del", "<ins", "<mark", '"del"', '"ins"'))
        ]

        assert files
        assert offending == []
