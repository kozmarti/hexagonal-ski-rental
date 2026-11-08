"""The dashboard with a fake use case injected: no database, no bootstrap."""

from datetime import date
from uuid import uuid4

from rental.adapters.inbound.web.views import DashboardView
from rental.application.ports.inbound.get_dashboard import Dashboard, RentalView
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from tests.unit.factories import eur, make_boots, make_skis
from tests.unit.fakes import Recorder, html

WEDNESDAY = date(2026, 12, 23)


def rental(customer_name: str, end: date) -> RentalView:
    items = [EquipmentView.from_entity(make_skis()), EquipmentView.from_entity(make_boots())]
    return RentalView(uuid4(), uuid4(), customer_name, items, date(2026, 12, 20), end, eur("180"))


def in_maintenance(item, damaged):
    item.rent()
    item.mark_returned(days=1, damaged=damaged)
    return EquipmentView.from_entity(item)


def page(rf, dashboard: Dashboard) -> str:
    view = DashboardView.as_view(get_dashboard=lambda: Recorder(dashboard))
    return html(view(rf.get("/")))


def test_dashboard_shows_today_and_every_section(rf):
    late = rental("Léa Dupont", date(2026, 12, 21))
    due = rental("Alex Martin", WEDNESDAY)
    repair = in_maintenance(make_skis(), damaged=True)
    dashboard = Dashboard(WEDNESDAY, [late, due], [due], [late], [repair])

    content = page(rf, dashboard)

    assert "Today: Wednesday 23 December" in content
    assert "Léa Dupont" in content
    assert "2\xa0days late" in content
    assert "Alex Martin" in content
    assert "Skis, Boots" in content
    assert "🔧 1 to repair" in content
    assert f"#rental-{late.id}" in content


def test_quiet_day_says_so(rf):
    content = page(rf, Dashboard(WEDNESDAY, [], [], [], []))

    assert "Nothing due back today." in content
    assert "Nothing to service." in content
    assert "<h2>Overdue</h2>" not in content


def test_dashboard_refreshes_itself(rf):
    content = page(rf, Dashboard(WEDNESDAY, [], [], [], []))

    assert 'hx-trigger="every 60s"' in content
