from decimal import Decimal

from rental.adapters.inbound.web.templatetags.rental_tags import money, needing_repair, size
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.domain.size import Size, SizeUnit
from tests.unit.factories import eur, make_boots, make_skis


def test_sizes_are_shown_without_useless_decimals():
    assert size(Size(Decimal("160.0"), SizeUnit.CM)) == "160 cm"
    assert size(Size.mondopoint("26.5")) == "26.5 mondopoint"


def test_money_is_shown_with_cents_and_currency():
    assert money(eur("180")) == "180.00 EUR"


def test_needing_repair_keeps_only_flagged_items():
    repair, service = make_skis(), make_boots()
    for item, damaged in [(repair, True), (service, False)]:
        item.rent()
        item.mark_returned(days=1, damaged=damaged)
    views = [EquipmentView.from_entity(repair), EquipmentView.from_entity(service)]

    assert [view.id for view in needing_repair(views)] == [repair.id]
