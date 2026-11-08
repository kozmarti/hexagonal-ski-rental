# The web composition root: each view receives its use cases from bootstrap.py here,
# outside the hexagon, so the views themselves only know inbound ports.
from django.urls import path

from rental import bootstrap
from rental.adapters.inbound.web import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "inventory/",
        views.InventoryView.as_view(
            list_available_equipment=bootstrap.list_available_equipment,
            register_equipment=bootstrap.register_equipment,
        ),
        name="inventory",
    ),
]
