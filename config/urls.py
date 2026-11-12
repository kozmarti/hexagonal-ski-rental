# The web composition root: each view receives its use cases from bootstrap.py here,
# outside the hexagon, so the views themselves only know inbound ports.
from django.conf import settings
from django.urls import path

from rental import bootstrap
from rental.adapters.inbound.api import views as api
from rental.adapters.inbound.web import pricing, scanning, views


def api_keys() -> frozenset[str]:
    """Read on every request, so a changed setting applies without restarting the URL config."""
    return frozenset(settings.API_KEYS)


def labels_base_url() -> str:
    return settings.LABELS_BASE_URL


def fleet_view(view_class):
    """A labels / QR / scan view: it combines the 3 use cases that together list every item."""
    return view_class.as_view(
        get_dashboard=bootstrap.get_dashboard,
        list_equipment_in_maintenance=bootstrap.list_equipment_in_maintenance,
        list_available_equipment=bootstrap.list_available_equipment,
        labels_base_url=labels_base_url,
    )


def endpoint(view_class, **use_cases):
    """An API view with its use cases and the device keys injected."""
    return view_class.as_view(api_keys=api_keys, **use_cases)


api_urlpatterns = [
    path(
        "api/equipment/",
        endpoint(api.EquipmentApi, list_available_equipment=bootstrap.list_available_equipment),
        name="api-equipment",
    ),
    path(
        "api/customers/",
        endpoint(api.CustomersApi, register_customer=bootstrap.register_customer),
        name="api-customers",
    ),
    path(
        "api/customers/<uuid:customer_id>/recommendation/",
        endpoint(api.RecommendationApi, recommend_equipment=bootstrap.recommend_equipment),
        name="api-recommendation",
    ),
    path(
        "api/rentals/",
        endpoint(api.RentalsApi, create_rental=bootstrap.create_rental),
        name="api-rentals",
    ),
    path(
        "api/rentals/<uuid:rental_id>/return/",
        endpoint(api.ReturnRentalApi, return_rental=bootstrap.return_rental),
        name="api-rental-return",
    ),
]

urlpatterns = [
    *api_urlpatterns,
    path(
        "",
        views.DashboardView.as_view(get_dashboard=bootstrap.get_dashboard),
        name="dashboard",
    ),
    path(
        "inventory/",
        views.InventoryView.as_view(
            list_available_equipment=bootstrap.list_available_equipment,
            register_equipment=bootstrap.register_equipment,
        ),
        name="inventory",
    ),
    path("inventory/labels/", fleet_view(scanning.LabelsView), name="inventory-labels"),
    path(
        "equipment/<uuid:equipment_id>/qr/",
        fleet_view(scanning.QrDialogView),
        name="equipment-qr",
    ),
    path("scan/", scanning.ScanPageView.as_view(), name="scan-page"),
    path("scan/<uuid:equipment_id>/", fleet_view(scanning.ScanItemView), name="scan"),
    path(
        "rentals/",
        views.RentalsView.as_view(get_dashboard=bootstrap.get_dashboard),
        name="rentals",
    ),
    path(
        "rentals/new/",
        views.NewRentalView.as_view(register_customer=bootstrap.register_customer),
        name="rental-new",
    ),
    path(
        "rentals/new/<uuid:customer_id>/",
        views.ChooseEquipmentView.as_view(
            recommend_equipment=bootstrap.recommend_equipment,
            list_available_equipment=bootstrap.list_available_equipment,
            create_rental=bootstrap.create_rental,
        ),
        name="rental-equipment",
    ),
    path(
        "rentals/import/",
        views.ImportGroupView.as_view(
            register_customer=bootstrap.register_customer,
            recommend_equipment=bootstrap.recommend_equipment,
            list_available_equipment=bootstrap.list_available_equipment,
            create_rental=bootstrap.create_rental,
        ),
        name="rental-import",
    ),
    path(
        "rentals/import/fit/<uuid:customer_id>/",
        views.FitChildView.as_view(
            recommend_equipment=bootstrap.recommend_equipment,
            list_available_equipment=bootstrap.list_available_equipment,
            create_rental=bootstrap.create_rental,
        ),
        name="rental-import-fit",
    ),
    path(
        "rentals/import/not-renting/<uuid:customer_id>/",
        views.NotRentingView.as_view(remove_customer=bootstrap.remove_customer),
        name="rental-import-not-renting",
    ),
    path(
        "rentals/<uuid:rental_id>/return/",
        views.ReturnRentalView.as_view(return_rental=bootstrap.return_rental),
        name="rental-return",
    ),
    path(
        "maintenance/",
        views.MaintenanceView.as_view(
            list_equipment_in_maintenance=bootstrap.list_equipment_in_maintenance
        ),
        name="maintenance",
    ),
    path(
        "maintenance/<uuid:equipment_id>/done/",
        views.CompleteMaintenanceView.as_view(complete_maintenance=bootstrap.complete_maintenance),
        name="maintenance-done",
    ),
    path(
        "pricing/",
        pricing.PricingView.as_view(
            get_price_list=bootstrap.get_price_list,
            update_price_list=bootstrap.update_price_list,
        ),
        name="pricing",
    ),
]
