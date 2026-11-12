# Composition root: the only place that wires concrete adapters into the use case services.
# Each function returns an inbound port; callers never see which adapters are behind it.
from dataclasses import dataclass

from django.conf import settings

from rental.adapters.outbound.clock import SystemClock
from rental.adapters.outbound.mongo.context import MongoContext
from rental.adapters.outbound.mongo.repositories import (
    MongoCustomerRepository,
    MongoEquipmentRepository,
    MongoRentalRepository,
)
from rental.adapters.outbound.mongo.unit_of_work import MongoUnitOfWork
from rental.adapters.outbound.notifications.logging_notifier import LoggingNotifier
from rental.adapters.outbound.orm.repositories import (
    DjangoCustomerRepository,
    DjangoEquipmentRepository,
    DjangoRentalRepository,
)
from rental.adapters.outbound.orm.unit_of_work import DjangoUnitOfWork
from rental.adapters.outbound.price_list.static import StaticPriceList
from rental.application.ports.inbound.complete_maintenance import CompleteMaintenance
from rental.application.ports.inbound.create_rental import CreateRental
from rental.application.ports.inbound.get_dashboard import GetDashboard
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipment
from rental.application.ports.inbound.list_equipment_in_maintenance import (
    ListEquipmentInMaintenance,
)
from rental.application.ports.inbound.recommend_equipment import RecommendEquipment
from rental.application.ports.inbound.register_customer import RegisterCustomer
from rental.application.ports.inbound.register_equipment import RegisterEquipment
from rental.application.ports.inbound.remove_customer import RemoveCustomer
from rental.application.ports.inbound.return_rental import ReturnRental
from rental.application.ports.outbound.clock import Clock
from rental.application.ports.outbound.customer_repository import CustomerRepository
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.application.ports.outbound.rental_repository import RentalRepository
from rental.application.ports.outbound.unit_of_work import UnitOfWork
from rental.application.services.complete_maintenance import CompleteMaintenanceService
from rental.application.services.create_rental import CreateRentalService
from rental.application.services.get_dashboard import GetDashboardService
from rental.application.services.list_available_equipment import ListAvailableEquipmentService
from rental.application.services.list_equipment_in_maintenance import (
    ListEquipmentInMaintenanceService,
)
from rental.application.services.recommend_equipment import RecommendEquipmentService
from rental.application.services.register_customer import RegisterCustomerService
from rental.application.services.register_equipment import RegisterEquipmentService
from rental.application.services.remove_customer import RemoveCustomerService
from rental.application.services.return_rental import ReturnRentalService


@dataclass(frozen=True)
class Storage:
    """The repositories and unit of work of one use case call, all on the same database."""

    equipment: EquipmentRepository
    customers: CustomerRepository
    rentals: RentalRepository
    uow: UnitOfWork


def storage() -> Storage:
    """The only place that chooses the database: REPOSITORY_BACKEND is "orm" or "mongo"."""
    if settings.REPOSITORY_BACKEND == "mongo":
        context = MongoContext(settings.MONGO_URL, settings.MONGO_DB)
        return Storage(
            MongoEquipmentRepository(context),
            MongoCustomerRepository(context),
            MongoRentalRepository(context),
            MongoUnitOfWork(context),
        )
    return Storage(
        DjangoEquipmentRepository(),
        DjangoCustomerRepository(),
        DjangoRentalRepository(),
        DjangoUnitOfWork(),
    )


def register_equipment() -> RegisterEquipment:
    store = storage()
    return RegisterEquipmentService(store.equipment, store.uow)


def list_available_equipment() -> ListAvailableEquipment:
    return ListAvailableEquipmentService(storage().equipment)


def register_customer() -> RegisterCustomer:
    store = storage()
    return RegisterCustomerService(store.customers, store.uow)


def remove_customer() -> RemoveCustomer:
    store = storage()
    return RemoveCustomerService(store.customers, store.rentals, store.uow)


def recommend_equipment() -> RecommendEquipment:
    store = storage()
    return RecommendEquipmentService(store.customers, store.equipment)


def create_rental(clock: Clock | None = None) -> CreateRental:
    """`clock` lets dev tooling (seed_demo) open a rental in the past. The app uses the
    system clock."""
    store = storage()
    return CreateRentalService(
        store.customers,
        store.equipment,
        store.rentals,
        StaticPriceList(),
        clock or SystemClock(),
        LoggingNotifier(),
        store.uow,
    )


def return_rental() -> ReturnRental:
    store = storage()
    return ReturnRentalService(
        store.rentals, store.equipment, SystemClock(), LoggingNotifier(), store.uow
    )


def complete_maintenance() -> CompleteMaintenance:
    store = storage()
    return CompleteMaintenanceService(store.equipment, LoggingNotifier(), store.uow)


def list_equipment_in_maintenance() -> ListEquipmentInMaintenance:
    return ListEquipmentInMaintenanceService(storage().equipment)


def get_dashboard() -> GetDashboard:
    store = storage()
    return GetDashboardService(store.rentals, store.customers, store.equipment, SystemClock())
