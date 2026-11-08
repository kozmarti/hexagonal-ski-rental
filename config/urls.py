# The web composition root: each view receives its use cases from bootstrap.py here,
# outside the hexagon, so the views themselves only know inbound ports.
from django.urls import path

from rental import bootstrap
from rental.adapters.inbound.web import views

urlpatterns = [
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
]
