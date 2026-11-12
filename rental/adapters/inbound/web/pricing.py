"""The Pricing page: every rate of the price list, editable in one form."""

from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from rental.application.ports.inbound.get_price_list import GetPriceList, RateView
from rental.application.ports.inbound.update_price_list import (
    RateChange,
    UpdatePriceList,
    UpdatePriceListCommand,
)
from rental.domain.exceptions import DomainError
from rental.domain.money import Money


def field_name(rate: RateView, period: str) -> str:
    return f"{period}-{rate.type}-{rate.range or 'none'}"


class PricingView(View):
    get_price_list: Callable[[], GetPriceList] | None = None
    update_price_list: Callable[[], UpdatePriceList] | None = None

    def get(self, request: HttpRequest) -> HttpResponse:
        rates = self.get_price_list().execute()
        rows = [self._row(rate, str(rate.day.amount), str(rate.week.amount)) for rate in rates]
        return self._page(request, rows, saved=request.GET.get("saved") == "1")

    def post(self, request: HttpRequest) -> HttpResponse:
        rates = self.get_price_list().execute()
        rows, changes, errors = [], [], []
        for rate in rates:
            day = request.POST.get(field_name(rate, "day"), "")
            week = request.POST.get(field_name(rate, "week"), "")
            rows.append(self._row(rate, day, week))
            try:
                changes.append(
                    RateChange(rate.type, rate.range, _money(day, rate), _money(week, rate))
                )
            except (InvalidOperation, DomainError):
                errors.append(f"{_name(rate)}: prices must be amounts, e.g. 30 or 29.50.")

        if not errors:
            try:
                self.update_price_list().execute(UpdatePriceListCommand(tuple(changes)))
            except DomainError as error:
                errors.append(str(error))
            else:
                return redirect(f"{reverse('pricing')}?saved=1")
        return self._page(request, rows, errors=errors)

    @staticmethod
    def _row(rate: RateView, day: str, week: str) -> dict:
        return {
            "rate": rate,
            "name": _name(rate),
            "day_field": field_name(rate, "day"),
            "week_field": field_name(rate, "week"),
            "day": day,
            "week": week,
        }

    @staticmethod
    def _page(request, rows, saved=False, errors=()) -> HttpResponse:
        context = {"rows": rows, "saved": saved, "errors": errors}
        return render(request, "rental/pricing.html", context)


def _money(value: str, rate: RateView) -> Money:
    """Raises InvalidOperation for text, InvalidMoney (a DomainError) for a negative amount."""
    return Money(Decimal(value.strip().replace(",", ".")), rate.day.currency)


def _name(rate: RateView) -> str:
    return f"{rate.type.capitalize()} {rate.range}" if rate.range else rate.type.capitalize()
