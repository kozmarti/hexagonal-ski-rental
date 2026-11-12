"""Pagination of the lists, in the web adapter: the use cases return the whole list and a page
shows a slice of it. Fine at a shop's size (a few hundred items); asking the database for one
page only would need a change of the ports."""

from dataclasses import dataclass

from django.core.paginator import Page, Paginator
from django.http import HttpRequest

PER_PAGE = 25


@dataclass(frozen=True)
class Pagination:
    page: Page
    previous_url: str | None
    next_url: str | None


def paginate(request: HttpRequest, items: list, per_page: int = PER_PAGE) -> Pagination:
    """A page of `items` (?page=N). The links keep the other parameters, e.g. the filters."""
    page = Paginator(items, per_page).get_page(request.GET.get("page"))

    def url(number: int) -> str:
        query = request.GET.copy()
        query["page"] = str(number)
        return f"?{query.urlencode()}"

    return Pagination(
        page=page,
        previous_url=url(page.previous_page_number()) if page.has_previous() else None,
        next_url=url(page.next_page_number()) if page.has_next() else None,
    )
