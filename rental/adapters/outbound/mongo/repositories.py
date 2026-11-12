"""MongoDB repositories: the same outbound ports as the Django ORM ones.

Documents are mapped to domain entities by hand, like the ORM rows. Ids are the domain's
UUIDs (stored as `_id`), amounts and sizes exact decimals (Decimal128, never floats), and
dates ISO strings ("2026-12-20"), which compare correctly as text.

A rental and its items are one aggregate, so they are one document here (`equipment_ids`
inside the rental), where PostgreSQL needs two tables.
"""

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from bson.decimal128 import Decimal128

from rental.adapters.outbound.mongo.context import MongoContext
from rental.domain.customer import Customer
from rental.domain.equipment import Equipment, EquipmentStatus, EquipmentType, Range
from rental.domain.exceptions import CustomerNotFound, EquipmentNotFound, RentalNotFound
from rental.domain.money import Money
from rental.domain.rental import Rental, RentalStatus
from rental.domain.rental_period import RentalPeriod
from rental.domain.size import Size, SizeUnit
from rental.domain.skill_level import SkillLevel


def _size_document(size: Size) -> dict:
    return {"value": Decimal128(size.value), "unit": str(size.unit)}


def _size(document: dict) -> Size:
    return Size(document["value"].to_decimal(), SizeUnit(document["unit"]))


class _MongoRepository:
    collection_name = ""

    def __init__(self, context: MongoContext) -> None:
        self._context = context

    @property
    def _collection(self):
        return self._context.database[self.collection_name]

    @property
    def _session(self):
        return self._context.session

    def _replace(self, document: dict) -> None:
        self._collection.replace_one(
            {"_id": document["_id"]}, document, upsert=True, session=self._session
        )


class MongoEquipmentRepository(_MongoRepository):
    collection_name = "equipment"

    def get(self, equipment_id: UUID) -> Equipment:
        document = self._collection.find_one({"_id": equipment_id}, session=self._session)
        if document is None:
            raise EquipmentNotFound(f"Equipment {equipment_id} not found.")
        return self._to_domain(document)

    def get_many(self, equipment_ids: Sequence[UUID]) -> list[Equipment]:
        query = {"_id": {"$in": list(equipment_ids)}}
        found = {doc["_id"]: doc for doc in self._collection.find(query, session=self._session)}
        missing = [str(equipment_id) for equipment_id in equipment_ids if equipment_id not in found]
        if missing:
            raise EquipmentNotFound(f"Equipment not found: {', '.join(missing)}.")
        return [self._to_domain(found[equipment_id]) for equipment_id in equipment_ids]

    def save(self, equipment: Equipment) -> None:
        self._replace(
            {
                "_id": equipment.id,
                "type": str(equipment.type),
                "brand": equipment.brand,
                "model": equipment.model,
                "size": _size_document(equipment.size),
                "range": str(equipment.range) if equipment.range else None,
                "status": str(equipment.status),
                "days_used": equipment.days_used,
                "needs_repair": equipment.needs_repair,
            }
        )

    def find_available(
        self,
        type: EquipmentType | None = None,
        size: Size | None = None,
        range: Range | None = None,
    ) -> list[Equipment]:
        query: dict = {"status": str(EquipmentStatus.AVAILABLE)}
        if type is not None:
            query["type"] = str(type)
        if size is not None:
            query["size.value"] = Decimal128(size.value)
            query["size.unit"] = str(size.unit)
        if range is not None:
            query["range"] = str(range)
        return self._find(query)

    def find_in_maintenance(self) -> list[Equipment]:
        return self._find({"status": str(EquipmentStatus.MAINTENANCE)})

    def _find(self, query: dict) -> list[Equipment]:
        return [self._to_domain(doc) for doc in self._collection.find(query, session=self._session)]

    @staticmethod
    def _to_domain(document: dict) -> Equipment:
        return Equipment(
            id=document["_id"],
            type=EquipmentType(document["type"]),
            brand=document["brand"],
            model=document["model"],
            size=_size(document["size"]),
            range=Range(document["range"]) if document["range"] else None,
            status=EquipmentStatus(document["status"]),
            days_used=document["days_used"],
            needs_repair=document["needs_repair"],
        )


class MongoCustomerRepository(_MongoRepository):
    collection_name = "customers"

    def get(self, customer_id: UUID) -> Customer:
        document = self._collection.find_one({"_id": customer_id}, session=self._session)
        if document is None:
            raise CustomerNotFound(f"Customer {customer_id} not found.")
        return Customer(
            id=document["_id"],
            name=document["name"],
            height_cm=document["height_cm"],
            boot_size=_size(document["boot_size"]),
            skill_level=SkillLevel(document["skill_level"]),
        )

    def save(self, customer: Customer) -> None:
        self._replace(
            {
                "_id": customer.id,
                "name": customer.name,
                "height_cm": customer.height_cm,
                "boot_size": _size_document(customer.boot_size),
                "skill_level": str(customer.skill_level),
            }
        )

    def delete(self, customer_id: UUID) -> None:
        self._collection.delete_one({"_id": customer_id}, session=self._session)


class MongoRentalRepository(_MongoRepository):
    collection_name = "rentals"

    def get(self, rental_id: UUID) -> Rental:
        document = self._collection.find_one({"_id": rental_id}, session=self._session)
        if document is None:
            raise RentalNotFound(f"Rental {rental_id} not found.")
        return self._to_domain(document)

    def save(self, rental: Rental) -> None:
        self._replace(
            {
                "_id": rental.id,
                "customer_id": rental.customer_id,
                "equipment_ids": list(rental.equipment_ids),
                "start_date": rental.period.start.isoformat(),
                "end_date": rental.period.end.isoformat(),
                "price": {
                    "amount": Decimal128(rental.price.amount),
                    "currency": rental.price.currency,
                },
                "status": str(rental.status),
                "returned_on": rental.returned_on.isoformat() if rental.returned_on else None,
            }
        )

    def has_rentals_for(self, customer_id: UUID) -> bool:
        query = {"customer_id": customer_id}
        return self._collection.count_documents(query, limit=1, session=self._session) > 0

    def find_active(self) -> list[Rental]:
        return self._find({"status": str(RentalStatus.ACTIVE)})

    def find_due_back_on(self, day: date) -> list[Rental]:
        return self._find({"status": str(RentalStatus.ACTIVE), "end_date": day.isoformat()})

    def find_overdue(self, today: date) -> list[Rental]:
        query = {"status": str(RentalStatus.ACTIVE), "end_date": {"$lt": today.isoformat()}}
        return self._find(query)

    def _find(self, query: dict) -> list[Rental]:
        return [self._to_domain(doc) for doc in self._collection.find(query, session=self._session)]

    @staticmethod
    def _to_domain(document: dict) -> Rental:
        returned_on = document["returned_on"]
        return Rental(
            id=document["_id"],
            customer_id=document["customer_id"],
            equipment_ids=tuple(document["equipment_ids"]),
            period=RentalPeriod(
                date.fromisoformat(document["start_date"]),
                date.fromisoformat(document["end_date"]),
            ),
            price=Money(document["price"]["amount"].to_decimal(), document["price"]["currency"]),
            status=RentalStatus(document["status"]),
            returned_on=date.fromisoformat(returned_on) if returned_on else None,
        )
