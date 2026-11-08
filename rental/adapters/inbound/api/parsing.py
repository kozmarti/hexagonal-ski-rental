"""Turns JSON requests into use case commands. Only the format is checked here:
business rules stay in the domain."""

import json
from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from uuid import UUID

from rental.application.ports.inbound.create_rental import CreateRentalCommand
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipmentQuery
from rental.application.ports.inbound.register_customer import RegisterCustomerCommand
from rental.application.ports.inbound.return_rental import ReturnRentalCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel


class InvalidRequest(Exception):
    """The request cannot be understood. `errors` maps each wrong field to a message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__(errors)
        self.errors = errors


def json_body(raw: bytes) -> dict:
    try:
        data = json.loads(raw or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise InvalidRequest({"body": "Invalid JSON."}) from None
    if not isinstance(data, dict):
        raise InvalidRequest({"body": "Expected a JSON object."})
    return data


def equipment_query(params: Mapping[str, str]) -> ListAvailableEquipmentQuery:
    errors: dict[str, str] = {}
    query = ListAvailableEquipmentQuery(
        type=_enum(params, "type", EquipmentType, errors, required=False),
        range=_enum(params, "range", Range, errors, required=False),
    )
    _raise_if(errors)
    return query


def register_customer_command(data: dict) -> RegisterCustomerCommand:
    errors: dict[str, str] = {}
    name = _text(data, "name", errors)
    height_cm = _integer(data, "height_cm", errors)
    boot_size = _decimal(data, "boot_size", errors)
    skill_level = _enum(data, "skill_level", SkillLevel, errors)
    _raise_if(errors)
    return RegisterCustomerCommand(name, height_cm, Size.mondopoint(boot_size), skill_level)


def create_rental_command(data: dict) -> CreateRentalCommand:
    errors: dict[str, str] = {}
    customer_id = _uuid(data.get("customer_id"), "customer_id", errors)
    equipment_ids = _uuid_list(data, "equipment_ids", errors, required=True)
    end_date = _date(data, "end_date", errors)
    _raise_if(errors)
    return CreateRentalCommand(customer_id, tuple(equipment_ids), end_date)


def return_rental_command(rental_id: UUID, data: dict) -> ReturnRentalCommand:
    errors: dict[str, str] = {}
    damaged = _uuid_list(data, "damaged_equipment_ids", errors, required=False)
    _raise_if(errors)
    return ReturnRentalCommand(rental_id, frozenset(damaged))


def _raise_if(errors: dict[str, str]) -> None:
    if errors:
        raise InvalidRequest(errors)


def _text(data, name, errors):
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        errors[name] = "A non-empty string is required."
    return value


def _integer(data, name, errors):
    value = data.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        errors[name] = "An integer is required."
    return value


def _decimal(data, name, errors):
    try:
        value = Decimal(str(data[name]))
    except (KeyError, InvalidOperation):
        value = None
    if value is None or not value.is_finite():
        errors[name] = "A number is required, e.g. 26.5."
    return value


def _enum(data, name, enum: type[StrEnum], errors, required=True):
    value = data.get(name)
    if value in (None, "") and not required:
        return None
    try:
        return enum(value)
    except ValueError:
        errors[name] = f"Expected one of: {', '.join(enum)}."


def _uuid(value, name, errors):
    try:
        return UUID(str(value))
    except ValueError:
        errors[name] = "A UUID is required."


def _uuid_list(data, name, errors, required):
    values = data.get(name, [])
    if not isinstance(values, list) or (required and not values):
        errors[name] = "A non-empty list of UUIDs is required." if required else "A list of UUIDs."
        return []
    try:
        return [UUID(str(value)) for value in values]
    except ValueError:
        errors[name] = "Every value must be a UUID."
        return []


def _date(data, name, errors):
    try:
        return date.fromisoformat(str(data[name]))
    except (KeyError, ValueError):
        errors[name] = "A date is required, as YYYY-MM-DD."
