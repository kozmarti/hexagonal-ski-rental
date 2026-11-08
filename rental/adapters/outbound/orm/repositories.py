from collections.abc import Sequence
from datetime import date
from uuid import UUID

from rental.adapters.outbound.orm.models import (
    CustomerModel,
    EquipmentModel,
    RentalItemModel,
    RentalModel,
)
from rental.domain.customer import Customer
from rental.domain.equipment import Equipment, EquipmentStatus, EquipmentType, Range
from rental.domain.exceptions import CustomerNotFound, EquipmentNotFound, RentalNotFound
from rental.domain.money import Money
from rental.domain.rental import Rental, RentalStatus
from rental.domain.rental_period import RentalPeriod
from rental.domain.size import Size, SizeUnit
from rental.domain.skill_level import SkillLevel


def _equipment_to_domain(row: EquipmentModel) -> Equipment:
    return Equipment(
        id=row.id,
        type=EquipmentType(row.type),
        brand=row.brand,
        model=row.model_name,
        size=Size(row.size_value, SizeUnit(row.size_unit)),
        range=Range(row.range) if row.range else None,
        status=EquipmentStatus(row.status),
        days_used=row.days_used,
        needs_repair=row.needs_repair,
    )


def _customer_to_domain(row: CustomerModel) -> Customer:
    return Customer(
        id=row.id,
        name=row.name,
        height_cm=row.height_cm,
        boot_size=Size(row.boot_size_value, SizeUnit(row.boot_size_unit)),
        skill_level=SkillLevel(row.skill_level),
    )


def _rental_to_domain(row: RentalModel) -> Rental:
    return Rental(
        id=row.id,
        customer_id=row.customer_id,
        equipment_ids=tuple(item.equipment_id for item in row.items.all()),
        period=RentalPeriod(row.start_date, row.end_date),
        price=Money(row.price_amount, row.price_currency),
        status=RentalStatus(row.status),
        returned_on=row.returned_on,
    )


class DjangoEquipmentRepository:
    def get(self, equipment_id: UUID) -> Equipment:
        try:
            return _equipment_to_domain(EquipmentModel.objects.get(id=equipment_id))
        except EquipmentModel.DoesNotExist:
            raise EquipmentNotFound(f"Equipment {equipment_id} not found.") from None

    def get_many(self, equipment_ids: Sequence[UUID]) -> list[Equipment]:
        rows = EquipmentModel.objects.in_bulk(list(equipment_ids))
        missing = [str(equipment_id) for equipment_id in equipment_ids if equipment_id not in rows]
        if missing:
            raise EquipmentNotFound(f"Equipment not found: {', '.join(missing)}.")
        return [_equipment_to_domain(rows[equipment_id]) for equipment_id in equipment_ids]

    def save(self, equipment: Equipment) -> None:
        EquipmentModel.objects.update_or_create(
            id=equipment.id,
            defaults={
                "type": equipment.type,
                "brand": equipment.brand,
                "model_name": equipment.model,
                "size_value": equipment.size.value,
                "size_unit": equipment.size.unit,
                "range": equipment.range,
                "status": equipment.status,
                "days_used": equipment.days_used,
                "needs_repair": equipment.needs_repair,
            },
        )

    def find_available(
        self,
        type: EquipmentType | None = None,
        size: Size | None = None,
        range: Range | None = None,
    ) -> list[Equipment]:
        rows = EquipmentModel.objects.filter(status=EquipmentStatus.AVAILABLE)
        if type is not None:
            rows = rows.filter(type=type)
        if size is not None:
            rows = rows.filter(size_value=size.value, size_unit=size.unit)
        if range is not None:
            rows = rows.filter(range=range)
        return [_equipment_to_domain(row) for row in rows]

    def find_in_maintenance(self) -> list[Equipment]:
        rows = EquipmentModel.objects.filter(status=EquipmentStatus.MAINTENANCE)
        return [_equipment_to_domain(row) for row in rows]


class DjangoCustomerRepository:
    def get(self, customer_id: UUID) -> Customer:
        try:
            return _customer_to_domain(CustomerModel.objects.get(id=customer_id))
        except CustomerModel.DoesNotExist:
            raise CustomerNotFound(f"Customer {customer_id} not found.") from None

    def save(self, customer: Customer) -> None:
        CustomerModel.objects.update_or_create(
            id=customer.id,
            defaults={
                "name": customer.name,
                "height_cm": customer.height_cm,
                "boot_size_value": customer.boot_size.value,
                "boot_size_unit": customer.boot_size.unit,
                "skill_level": customer.skill_level,
            },
        )


class DjangoRentalRepository:
    def get(self, rental_id: UUID) -> Rental:
        try:
            return _rental_to_domain(self._rentals().get(id=rental_id))
        except RentalModel.DoesNotExist:
            raise RentalNotFound(f"Rental {rental_id} not found.") from None

    def save(self, rental: Rental) -> None:
        row, _ = RentalModel.objects.update_or_create(
            id=rental.id,
            defaults={
                "customer_id": rental.customer_id,
                "start_date": rental.period.start,
                "end_date": rental.period.end,
                "price_amount": rental.price.amount,
                "price_currency": rental.price.currency,
                "status": rental.status,
                "returned_on": rental.returned_on,
            },
        )
        # The rental and its items are one aggregate: they are always saved together.
        row.items.all().delete()
        RentalItemModel.objects.bulk_create(
            RentalItemModel(rental=row, equipment_id=equipment_id, position=position)
            for position, equipment_id in enumerate(rental.equipment_ids)
        )

    def find_active(self) -> list[Rental]:
        rows = self._rentals().filter(status=RentalStatus.ACTIVE)
        return [_rental_to_domain(row) for row in rows]

    def find_due_back_on(self, day: date) -> list[Rental]:
        rows = self._rentals().filter(status=RentalStatus.ACTIVE, end_date=day)
        return [_rental_to_domain(row) for row in rows]

    def find_overdue(self, today: date) -> list[Rental]:
        rows = self._rentals().filter(status=RentalStatus.ACTIVE, end_date__lt=today)
        return [_rental_to_domain(row) for row in rows]

    @staticmethod
    def _rentals():
        return RentalModel.objects.prefetch_related("items")
