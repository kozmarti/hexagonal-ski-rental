"""The Pricing page with fake use cases injected: no database, no bootstrap."""

from rental.adapters.inbound.web.pricing import PricingView
from rental.application.ports.inbound.get_price_list import RateView
from rental.application.ports.inbound.update_price_list import UpdatePriceListResult
from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import InvalidPriceList
from tests.unit.factories import eur
from tests.unit.fakes import Recorder, html

RATES = [
    RateView(EquipmentType.SKIS, Range.SPORT, eur("30"), eur("140")),
    RateView(EquipmentType.HELMET, None, eur("6"), eur("30")),
]
FORM = {
    "day-skis-sport": "35",
    "week-skis-sport": "160",
    "day-helmet-none": "6",
    "week-helmet-none": "30",
}


def view(update):
    return PricingView.as_view(
        get_price_list=lambda: Recorder(RATES), update_price_list=lambda: update
    )


def test_every_rate_is_shown_in_an_editable_field(rf):
    content = html(view(Recorder())(rf.get("/pricing/")))

    assert 'name="day-skis-sport" value="30.00"' in content
    assert 'name="week-helmet-none" value="30.00"' in content


def test_saving_sends_every_rate_and_shows_the_confirmation(rf):
    update = Recorder(UpdatePriceListResult(changed=2))

    response = view(update)(rf.post("/pricing/", FORM))

    assert response.status_code == 302
    assert response.url == "/pricing/?saved=1"
    skis, helmet = update.calls[0].changes
    assert (skis.type, skis.range, skis.day, skis.week) == (
        EquipmentType.SKIS,
        Range.SPORT,
        eur("35"),
        eur("160"),
    )
    assert helmet.range is None


def test_text_or_negative_amounts_never_reach_the_use_case(rf):
    update = Recorder()

    content = html(view(update)(rf.post("/pricing/", {**FORM, "day-skis-sport": "-5"})))

    assert "Skis sport: prices must be amounts" in content
    assert 'value="-5"' in content
    assert update.calls == []


def test_a_business_rule_refusal_is_shown(rf):
    update = Recorder(error=InvalidPriceList("Skis sport: A week must cost less than 6 days."))

    content = html(view(update)(rf.post("/pricing/", FORM)))

    assert "Skis sport: A week must cost less than 6 days." in content
