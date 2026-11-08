"""Command-line inbound adapter: the same counter work as the web screens, from a terminal.

Like the views, it only knows inbound ports. The use cases are injected through `UseCases`;
the wiring lives in config/cli.py, outside the hexagon. Plain argparse, no Django.
"""

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TextIO
from uuid import UUID

from rental.application.ports.inbound.create_rental import CreateRental, CreateRentalCommand
from rental.application.ports.inbound.list_available_equipment import (
    EquipmentView,
    ListAvailableEquipment,
    ListAvailableEquipmentQuery,
)
from rental.application.ports.inbound.register_customer import (
    RegisterCustomer,
    RegisterCustomerCommand,
)
from rental.application.ports.inbound.return_rental import ReturnRental, ReturnRentalCommand
from rental.domain.equipment import EquipmentType, Range
from rental.domain.exceptions import DomainError
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel


@dataclass(frozen=True)
class UseCases:
    list_available_equipment: Callable[[], ListAvailableEquipment]
    register_customer: Callable[[], RegisterCustomer]
    create_rental: Callable[[], CreateRental]
    return_rental: Callable[[], ReturnRental]


def run(argv: Sequence[str], use_cases: UseCases, out: TextIO, err: TextIO) -> int:
    """Runs one command and returns the exit code: 0 on success, 1 on a business error."""
    args = _parser().parse_args(argv)
    try:
        args.handler(args, use_cases, out)
    except DomainError as error:
        err.write(f"Error: {error}\n")
        return 1
    return 0


def _available(args, use_cases: UseCases, out: TextIO) -> None:
    query = ListAvailableEquipmentQuery(type=args.type, range=args.range)
    items = use_cases.list_available_equipment().execute(query)
    for item in items:
        out.write(_describe(item) + "\n")
    out.write(f"{len(items)} item(s) available.\n")


def _customer(args, use_cases: UseCases, out: TextIO) -> None:
    command = RegisterCustomerCommand(
        name=args.name,
        height_cm=args.height,
        boot_size=Size.mondopoint(args.boots),
        skill_level=args.level,
    )
    result = use_cases.register_customer().execute(command)
    out.write(f"Customer {result.customer_id} registered.\n")


def _rent(args, use_cases: UseCases, out: TextIO) -> None:
    command = CreateRentalCommand(args.customer, tuple(args.items), args.until)
    result = use_cases.create_rental().execute(command)
    price = f"{result.price.amount} {result.price.currency}"
    out.write(
        f"Rental {result.rental_id} created: {result.start_date} to {result.end_date}, {price}.\n"
    )


def _return(args, use_cases: UseCases, out: TextIO) -> None:
    command = ReturnRentalCommand(args.rental, frozenset(args.damaged))
    result = use_cases.return_rental().execute(command)
    repairs = len(result.needs_repair_ids)
    out.write(
        f"Rental {result.rental_id} returned on {result.returned_on}. "
        f"All items are in maintenance, {repairs} need a repair.\n"
    )


def _describe(item: EquipmentView) -> str:
    size = f"{item.size.value.normalize():f} {item.size.unit}"
    range_name = item.range.capitalize() if item.range else "-"
    return f"{item.id}  {item.type:<9}  {item.brand} {item.model}  {size}  {range_name}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ski_rental", description="Ski rental counter.")
    commands = parser.add_subparsers(required=True, metavar="command")

    available = commands.add_parser("available", help="list available equipment")
    available.add_argument("--type", type=EquipmentType, choices=list(EquipmentType))
    available.add_argument("--range", type=Range, choices=list(Range))
    available.set_defaults(handler=_available)

    customer = commands.add_parser("customer", help="register a customer")
    customer.add_argument("--name", required=True)
    customer.add_argument("--height", type=int, required=True, help="in cm")
    customer.add_argument("--boots", type=Decimal, required=True, help="mondopoint, e.g. 26.5")
    customer.add_argument("--level", type=SkillLevel, choices=list(SkillLevel), required=True)
    customer.set_defaults(handler=_customer)

    rent = commands.add_parser("rent", help="rent equipment, starting today")
    rent.add_argument("--customer", type=UUID, required=True)
    rent.add_argument("--items", type=UUID, nargs="+", required=True)
    rent.add_argument("--until", type=date.fromisoformat, required=True, help="last day")
    rent.set_defaults(handler=_rent)

    return_ = commands.add_parser("return", help="return a rental")
    return_.add_argument("rental", type=UUID)
    return_.add_argument("--damaged", type=UUID, nargs="*", default=[])
    return_.set_defaults(handler=_return)

    return parser
