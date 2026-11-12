from bson.decimal128 import Decimal128

from rental.adapters.outbound.mongo.context import MongoContext
from rental.domain.equipment import EquipmentType, Range
from rental.domain.money import Money
from rental.domain.pricing import PriceList, Rate

DOCUMENT_ID = "current"


class MongoPriceListRepository:
    """The editable price list in MongoDB: one document holding every rate. Until prices are
    first saved, `defaults` (the shop's starting prices) are used."""

    def __init__(self, context: MongoContext, defaults: PriceList) -> None:
        self._context = context
        self._defaults = defaults

    @property
    def _collection(self):
        return self._context.database["prices"]

    def get(self) -> PriceList:
        document = self._collection.find_one({"_id": DOCUMENT_ID}, session=self._context.session)
        if document is None:
            return self._defaults
        return PriceList({_key(rate): _rate(rate) for rate in document["rates"]})

    def save(self, price_list: PriceList) -> None:
        rates = [
            {
                "type": str(equipment_type),
                "range": str(range) if range else None,
                "day": Decimal128(rate.day.amount),
                "week": Decimal128(rate.week.amount),
                "currency": rate.day.currency,
            }
            for (equipment_type, range), rate in price_list.rates.items()
        ]
        self._collection.replace_one(
            {"_id": DOCUMENT_ID},
            {"_id": DOCUMENT_ID, "rates": rates},
            upsert=True,
            session=self._context.session,
        )


def _key(rate: dict) -> tuple[EquipmentType, Range | None]:
    return EquipmentType(rate["type"]), Range(rate["range"]) if rate["range"] else None


def _rate(rate: dict) -> Rate:
    return Rate(
        day=Money(rate["day"].to_decimal(), rate["currency"]),
        week=Money(rate["week"].to_decimal(), rate["currency"]),
    )
