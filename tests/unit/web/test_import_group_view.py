"""The group import page, with the real services on in-memory adapters: no database."""

from django.core.files.uploadedfile import SimpleUploadedFile

from rental.adapters.inbound.web.views import ImportGroupView
from tests.unit.application.conftest import Shop
from tests.unit.csv_import.test_import_group import HEADER, boots, skis, wired
from tests.unit.fakes import html


def view(shop: Shop):
    use_cases = wired(shop)
    return ImportGroupView.as_view(
        register_customer=use_cases.register_customer,
        recommend_equipment=use_cases.recommend_equipment,
        list_available_equipment=use_cases.list_available_equipment,
        create_rental=use_cases.create_rental,
    )


def upload(rf, text: str):
    csv_file = SimpleUploadedFile("group.csv", text.encode(), content_type="text/csv")
    return rf.post("/", {"file": csv_file, "end_date": "2026-12-25"})


def test_page_explains_the_csv_format(rf):
    page = html(view(Shop())(rf.get("/")))

    assert HEADER in page
    assert 'enctype="multipart/form-data"' in page


def test_import_shows_a_report_per_child(rf):
    shop = Shop()
    shop.add(skis(165), boots())
    text = f"{HEADER}\nEmma,175,26.5,intermediate,skis,no\nInès,150,23,intermediate,skis,no\n"

    page = html(view(shop)(upload(rf, text)))

    assert "1 of 2 children equipped" in page
    assert "total 180.00 EUR" in page
    assert "✅ Skis 165 cm, Boots 26.5 mondopoint · 180.00 EUR" in page
    assert "No available skis in a fitting size and range." in page


def test_unmatched_children_stay_pending_with_fit_and_not_renting_buttons(rf):
    shop = Shop()
    text = f"{HEADER}\nInès,150,23,intermediate,skis,no\n"

    page = html(view(shop)(upload(rf, text)))

    assert 'data-status="pending"' in page
    assert "?line=2&end_date=2026-12-25" in page
    assert 'hx-target="#fit-dialog-content"' in page
    assert "data-not-renting>Not renting</button>" in page
    assert '<dialog id="fit-dialog">' in page
    assert "beforeunload" in page


def test_a_child_who_could_not_be_registered_is_not_left_pending(rf):
    shop = Shop()
    text = f"{HEADER}\nGhost,0,26.5,intermediate,skis,no\n"

    page = html(view(shop)(upload(rf, text)))

    assert 'data-status="failed"' in page
    assert "fix this line and import it again" in page
    assert "data-not-renting>Not renting</button>" not in page
    assert "/rentals/import/fit/" not in page


def test_a_wrong_file_rents_nothing(rf):
    shop = Shop()
    shop.add(skis(165), boots())
    text = f"{HEADER}\nEmma,175,26.5,intermediate,skis,no\nLucas,175,26.5,pro,skis,no\n"

    page = html(view(shop)(upload(rf, text)))

    assert "Line 3: level must be one of" in page
    assert "children equipped" not in page
    assert shop.rentals.find_active() == []
