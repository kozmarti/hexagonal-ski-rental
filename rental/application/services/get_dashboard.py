from rental.application.ports.inbound.get_dashboard import Dashboard, RentalView
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.outbound.clock import Clock
from rental.application.ports.outbound.customer_repository import CustomerRepository
from rental.application.ports.outbound.equipment_repository import EquipmentRepository
from rental.application.ports.outbound.rental_repository import RentalRepository
from rental.application.services.list_equipment_in_maintenance import maintenance_order
from rental.domain.rental import Rental


class GetDashboardService:
    def __init__(
        self,
        rentals: RentalRepository,
        customers: CustomerRepository,
        equipment: EquipmentRepository,
        clock: Clock,
    ) -> None:
        self._rentals = rentals
        self._customers = customers
        self._equipment = equipment
        self._clock = clock

    def execute(self) -> Dashboard:
        today = self._clock.today()
        active = sorted(self._rentals.find_active(), key=lambda rental: rental.period.end)
        due_back = self._rentals.find_due_back_on(today)
        overdue = sorted(self._rentals.find_overdue(today), key=lambda rental: rental.period.end)
        in_maintenance = sorted(self._equipment.find_in_maintenance(), key=maintenance_order)
        return Dashboard(
            today=today,
            active_rentals=[self._view(rental) for rental in active],
            due_back_today=[self._view(rental) for rental in due_back],
            overdue=[self._view(rental) for rental in overdue],
            in_maintenance=[EquipmentView.from_entity(item) for item in in_maintenance],
        )

    def _view(self, rental: Rental) -> RentalView:
        customer = self._customers.get(rental.customer_id)
        items = self._equipment.get_many(rental.equipment_ids)
        return RentalView(
            id=rental.id,
            customer_id=customer.id,
            customer_name=customer.name,
            equipment=[EquipmentView.from_entity(item) for item in items],
            start_date=rental.period.start,
            end_date=rental.period.end,
            price=rental.price,
        )
