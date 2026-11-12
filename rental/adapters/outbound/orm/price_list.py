from rental.adapters.outbound.orm.models import PriceModel
from rental.domain.equipment import EquipmentType, Range
from rental.domain.money import Money
from rental.domain.pricing import PriceList, Rate


class DjangoPriceListRepository:
    """The editable price list in PostgreSQL. Until prices are first saved, `defaults`
    (the shop's starting prices) are used."""

    def __init__(self, defaults: PriceList) -> None:
        self._defaults = defaults

    def get(self) -> PriceList:
        rows = list(PriceModel.objects.all())
        if not rows:
            return self._defaults
        return PriceList({_key(row): _rate(row) for row in rows})

    def save(self, price_list: PriceList) -> None:
        # The whole list is one value: replaced at once (inside the unit of work's transaction).
        PriceModel.objects.all().delete()
        PriceModel.objects.bulk_create(
            PriceModel(
                equipment_type=equipment_type,
                range=range or "",
                day_amount=rate.day.amount,
                week_amount=rate.week.amount,
                currency=rate.day.currency,
            )
            for (equipment_type, range), rate in price_list.rates.items()
        )


def _key(row: PriceModel) -> tuple[EquipmentType, Range | None]:
    return EquipmentType(row.equipment_type), Range(row.range) if row.range else None


def _rate(row: PriceModel) -> Rate:
    return Rate(day=Money(row.day_amount, row.currency), week=Money(row.week_amount, row.currency))
