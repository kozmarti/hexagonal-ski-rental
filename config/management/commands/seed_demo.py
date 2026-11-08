"""Creates demo data through the use cases, never by writing tables directly:
the domain checks every item and computes every price, exactly as at the counter.
"""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from rental import bootstrap
from rental.adapters.outbound.memory.clock import FixedClock
from rental.adapters.outbound.notifications.logging_notifier import LoggingNotifier
from rental.adapters.outbound.orm.repositories import (
    DjangoCustomerRepository,
    DjangoEquipmentRepository,
    DjangoRentalRepository,
)
from rental.adapters.outbound.orm.unit_of_work import DjangoUnitOfWork
from rental.adapters.outbound.price_list.static import StaticPriceList
from rental.application.ports.inbound.create_rental import CreateRental, CreateRentalCommand
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipmentQuery
from rental.application.ports.inbound.register_customer import RegisterCustomerCommand
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.application.ports.inbound.return_rental import ReturnRentalCommand
from rental.application.services.create_rental import CreateRentalService
from rental.domain.equipment import EquipmentType, Range, size_unit_for
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel

SKIS, SNOWBOARD, BOOTS = EquipmentType.SKIS, EquipmentType.SNOWBOARD, EquipmentType.BOOTS
HELMET, POLES = EquipmentType.HELMET, EquipmentType.POLES
DISCOVERY, SPORT, PREMIUM = Range.DISCOVERY, Range.SPORT, Range.PREMIUM

EQUIPMENT = [
    (SKIS, DISCOVERY, "Rossignol", "Experience 76", ["150", "155", "160", "165"]),
    (SKIS, SPORT, "Atomic", "Redster Q7", ["160", "165", "170", "175"]),
    (SKIS, PREMIUM, "Salomon", "Stance 90", ["165", "170", "175", "180"]),
    (SNOWBOARD, DISCOVERY, "Burton", "Ripcord", ["150", "155"]),
    (SNOWBOARD, SPORT, "Burton", "Process", ["155", "158"]),
    (SNOWBOARD, PREMIUM, "Lib Tech", "Orca", ["156", "159"]),
    (BOOTS, DISCOVERY, "Salomon", "Access", ["24.5", "25.5", "26.5", "27.5"]),
    (BOOTS, SPORT, "Rossignol", "Alltrack", ["25.5", "26.5", "27.5", "28.5"]),
    (BOOTS, PREMIUM, "Lange", "RX 120", ["26", "27", "28"]),
    (HELMET, None, "Giro", "Ledge", ["54", "56", "58", "60"]),
    (POLES, None, "Leki", "Spitfire", ["110", "115", "120", "125"]),
]

CUSTOMERS = {
    "lea": ("Léa Dupont", 158, "24.5", SkillLevel.BEGINNER),
    "alex": ("Alex Martin", 175, "26.5", SkillLevel.INTERMEDIATE),
    "hugo": ("Hugo Bernard", 182, "28", SkillLevel.ADVANCED),
    "camille": ("Camille Roux", 168, "26", SkillLevel.EXPERT),
    "noah": ("Noah Petit", 170, "27.5", SkillLevel.INTERMEDIATE),
}


class Command(BaseCommand):
    help = "Fills an empty database with demo equipment, customers and rentals in every state."

    def handle(self, *args, **options):
        self._refuse_if_not_empty()
        with transaction.atomic():
            items = self._register_equipment()
            customers = self._register_customers()
            self._create_rentals(items, customers)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data created: {len(items)} items, {len(customers)} customers, 5 rentals."
            )
        )

    def _refuse_if_not_empty(self) -> None:
        dashboard = bootstrap.get_dashboard().execute()
        available = bootstrap.list_available_equipment().execute(ListAvailableEquipmentQuery())
        if available or dashboard.active_rentals or dashboard.in_maintenance:
            raise CommandError(
                "The database already has data. Empty it first: python manage.py flush --no-input"
            )

    def _register_equipment(self) -> dict[tuple, UUID]:
        register = bootstrap.register_equipment()
        ids = {}
        for equipment_type, range, brand, model, sizes in EQUIPMENT:
            for size in sizes:
                command = RegisterEquipmentCommand(
                    type=equipment_type,
                    brand=brand,
                    model=model,
                    size=Size(Decimal(size), size_unit_for(equipment_type)),
                    range=range,
                )
                ids[(equipment_type, range, size)] = register.execute(command).equipment_id
        return ids

    def _register_customers(self) -> dict[str, UUID]:
        register = bootstrap.register_customer()
        ids = {}
        for key, (name, height, boots, level) in CUSTOMERS.items():
            command = RegisterCustomerCommand(name, height, Size.mondopoint(boots), level)
            ids[key] = register.execute(command).customer_id
        return ids

    def _create_rentals(self, items: dict[tuple, UUID], customers: dict[str, UUID]) -> None:
        today = timezone.localdate()
        create_today = bootstrap.create_rental()

        def rent(create: CreateRental, customer: str, keys: list[tuple], end) -> UUID:
            command = CreateRentalCommand(customers[customer], tuple(items[k] for k in keys), end)
            return create.execute(command).rental_id

        # Out for the week.
        week = [(SKIS, SPORT, "165"), (BOOTS, SPORT, "26.5"), (HELMET, None, "58")]
        rent(create_today, "alex", week, today + timedelta(days=5))

        # Due back today.
        one_day = [(SKIS, DISCOVERY, "150"), (BOOTS, DISCOVERY, "24.5")]
        rent(create_today, "lea", one_day, today)

        # Overdue: a rental always starts "today", so this one is created with a clock
        # set four days ago. Same use case, same rules, another Clock adapter.
        late = [(SKIS, PREMIUM, "175"), (BOOTS, PREMIUM, "28"), (POLES, None, "125")]
        create_four_days_ago = self._create_rental_on(today - timedelta(days=4))
        rent(create_four_days_ago, "hugo", late, today - timedelta(days=2))

        # Returned today: every item goes to maintenance, the damaged board needs a repair.
        return_rental = bootstrap.return_rental()
        board = (SNOWBOARD, PREMIUM, "156")
        damaged = rent(create_today, "camille", [board, (BOOTS, PREMIUM, "26")], today)
        return_rental.execute(ReturnRentalCommand(damaged, frozenset({items[board]})))

        serviced = [(SNOWBOARD, SPORT, "155"), (BOOTS, SPORT, "27.5")]
        rental_id = rent(create_today, "noah", serviced, today)
        return_rental.execute(ReturnRentalCommand(rental_id))

    @staticmethod
    def _create_rental_on(day) -> CreateRental:
        return CreateRentalService(
            DjangoCustomerRepository(),
            DjangoEquipmentRepository(),
            DjangoRentalRepository(),
            StaticPriceList(),
            FixedClock(day),
            LoggingNotifier(),
            DjangoUnitOfWork(),
        )
