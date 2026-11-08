"""Turns use case results into JSON-ready dictionaries."""

from rental.application.ports.inbound.create_rental import CreateRentalResult
from rental.application.ports.inbound.list_available_equipment import EquipmentView
from rental.application.ports.inbound.recommend_equipment import RecommendEquipmentResult
from rental.application.ports.inbound.return_rental import ReturnRentalResult
from rental.domain.money import Money
from rental.domain.size import Size


def money(value: Money) -> dict:
    return {"amount": str(value.amount), "currency": value.currency}


def size(value: Size) -> dict:
    return {"value": f"{value.value.normalize():f}", "unit": value.unit}


def equipment(view: EquipmentView) -> dict:
    return {
        "id": str(view.id),
        "type": view.type,
        "brand": view.brand,
        "model": view.model,
        "size": size(view.size),
        "range": view.range,
        "days_used": view.days_used,
        "needs_repair": view.needs_repair,
    }


def recommendation(result: RecommendEquipmentResult) -> dict:
    return {
        "range": result.range,
        "ski_length": size(result.ski_length),
        "snowboard_length": size(result.snowboard_length),
        "boot_size": size(result.boot_size),
        "skis": [equipment(item) for item in result.skis],
        "snowboards": [equipment(item) for item in result.snowboards],
        "boots": [equipment(item) for item in result.boots],
    }


def rental_created(result: CreateRentalResult) -> dict:
    return {
        "id": str(result.rental_id),
        "start_date": result.start_date.isoformat(),
        "end_date": result.end_date.isoformat(),
        "price": money(result.price),
    }


def rental_returned(result: ReturnRentalResult) -> dict:
    return {
        "id": str(result.rental_id),
        "returned_on": result.returned_on.isoformat(),
        "needs_repair_ids": sorted(str(item_id) for item_id in result.needs_repair_ids),
    }
