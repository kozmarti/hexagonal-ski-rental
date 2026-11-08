# Composition root: the only place that wires concrete adapters into the use case services.
# Each function returns an inbound port; callers never see which adapters are behind it.
from rental.adapters.outbound.clock import SystemClock
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
from rental.application.ports.inbound.return_rental import ReturnRental
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
from rental.application.services.return_rental import ReturnRentalService


def register_equipment() -> RegisterEquipment:
    return RegisterEquipmentService(DjangoEquipmentRepository(), DjangoUnitOfWork())


def list_available_equipment() -> ListAvailableEquipment:
    return ListAvailableEquipmentService(DjangoEquipmentRepository())


def register_customer() -> RegisterCustomer:
    return RegisterCustomerService(DjangoCustomerRepository(), DjangoUnitOfWork())


def recommend_equipment() -> RecommendEquipment:
    return RecommendEquipmentService(DjangoCustomerRepository(), DjangoEquipmentRepository())


def create_rental() -> CreateRental:
    return CreateRentalService(
        DjangoCustomerRepository(),
        DjangoEquipmentRepository(),
        DjangoRentalRepository(),
        StaticPriceList(),
        SystemClock(),
        LoggingNotifier(),
        DjangoUnitOfWork(),
    )


def return_rental() -> ReturnRental:
    return ReturnRentalService(
        DjangoRentalRepository(),
        DjangoEquipmentRepository(),
        SystemClock(),
        LoggingNotifier(),
        DjangoUnitOfWork(),
    )


def complete_maintenance() -> CompleteMaintenance:
    return CompleteMaintenanceService(
        DjangoEquipmentRepository(), LoggingNotifier(), DjangoUnitOfWork()
    )


def list_equipment_in_maintenance() -> ListEquipmentInMaintenance:
    return ListEquipmentInMaintenanceService(DjangoEquipmentRepository())


def get_dashboard() -> GetDashboard:
    return GetDashboardService(
        DjangoRentalRepository(),
        DjangoCustomerRepository(),
        DjangoEquipmentRepository(),
        SystemClock(),
    )
