"""Group import (e.g. a ski school class): one CSV line per child, one rental per child.

An inbound adapter in plain Python: it turns CSV lines into calls to existing use cases
(register customer, recommend, create rental) and never touches the core. The use cases
are injected through `GroupUseCases`.
"""

import csv
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from rental.application.ports.inbound.create_rental import CreateRental, CreateRentalCommand
from rental.application.ports.inbound.list_available_equipment import (
    EquipmentView,
    ListAvailableEquipment,
    ListAvailableEquipmentQuery,
)
from rental.application.ports.inbound.recommend_equipment import (
    RecommendEquipment,
    RecommendEquipmentQuery,
)
from rental.application.ports.inbound.register_customer import (
    RegisterCustomer,
    RegisterCustomerCommand,
)
from rental.domain.equipment import EquipmentType
from rental.domain.exceptions import DomainError
from rental.domain.money import Money
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel

COLUMNS = ["name", "height_cm", "boot_size", "level", "board", "helmet"]
BOARDS = {"skis": EquipmentType.SKIS, "snowboard": EquipmentType.SNOWBOARD}
YES_NO = {"yes": True, "no": False}


class CsvFormatError(Exception):
    """The file cannot be imported. `problems` lists every problem with its line number."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class NothingFits(Exception):
    """No available item fits the child: staff have to choose by hand."""


@dataclass(frozen=True)
class GroupMember:
    line: int
    name: str
    height_cm: int
    boot_size: Decimal
    level: SkillLevel
    board: EquipmentType
    helmet: bool


@dataclass(frozen=True)
class ImportedLine:
    line: int
    name: str
    customer_id: UUID | None
    rental_id: UUID | None = None
    items: tuple[EquipmentView, ...] = ()
    price: Money | None = None
    error: str | None = None


@dataclass(frozen=True)
class GroupUseCases:
    register_customer: Callable[[], RegisterCustomer]
    recommend_equipment: Callable[[], RecommendEquipment]
    list_available_equipment: Callable[[], ListAvailableEquipment]
    create_rental: Callable[[], CreateRental]


def parse(text: str) -> list[GroupMember]:
    """Reads the whole file first: if any line is wrong, nothing is imported."""
    header = text.split("\n", 1)[0]
    delimiter = ";" if header.count(";") > header.count(",") else ","
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    missing = [column for column in COLUMNS if column not in (reader.fieldnames or [])]
    if missing:
        raise CsvFormatError([f"Line 1: missing column(s): {', '.join(missing)}."])

    members, problems = [], []
    for line, row in enumerate(reader, start=2):
        try:
            members.append(_member(line, row))
        except ValueError as error:
            problems.append(f"Line {line}: {error}")
    if problems:
        raise CsvFormatError(problems)
    if not members:
        raise CsvFormatError(["The file has no children to import."])
    return members


def import_group(
    members: list[GroupMember], end_date: date, use_cases: GroupUseCases
) -> list[ImportedLine]:
    """Rents to each child in turn. A child who cannot be equipped does not stop the others."""
    return [_import_one(member, end_date, use_cases) for member in members]


def _member(line: int, row: dict[str, str]) -> GroupMember:
    value = {column: (row.get(column) or "").strip() for column in COLUMNS}
    if not value["name"]:
        raise ValueError("name is empty.")
    try:
        height_cm = int(value["height_cm"])
        boot_size = Decimal(value["boot_size"].replace(",", "."))
    except (ValueError, InvalidOperation):
        raise ValueError("height_cm and boot_size must be numbers.") from None
    try:
        level = SkillLevel(value["level"].lower())
    except ValueError:
        levels = ", ".join(SkillLevel)
        raise ValueError(f"level must be one of {levels}.") from None
    board = BOARDS.get(value["board"].lower())
    if board is None:
        raise ValueError("board must be skis or snowboard.")
    helmet = YES_NO.get(value["helmet"].lower())
    if helmet is None:
        raise ValueError("helmet must be yes or no.")
    return GroupMember(line, value["name"], height_cm, boot_size, level, board, helmet)


def _import_one(member: GroupMember, end_date: date, use_cases: GroupUseCases) -> ImportedLine:
    customer_id = None
    try:
        customer = RegisterCustomerCommand(
            member.name, member.height_cm, Size.mondopoint(member.boot_size), member.level
        )
        customer_id = use_cases.register_customer().execute(customer).customer_id
        items = _choose_items(member, customer_id, use_cases)
        rental = use_cases.create_rental().execute(
            CreateRentalCommand(customer_id, tuple(item.id for item in items), end_date)
        )
    except (DomainError, NothingFits) as error:
        return ImportedLine(member.line, member.name, customer_id, error=str(error))
    return ImportedLine(
        member.line,
        member.name,
        customer_id,
        rental_id=rental.rental_id,
        items=tuple(items),
        price=rental.price,
    )


def _choose_items(
    member: GroupMember, customer_id: UUID, use_cases: GroupUseCases
) -> list[EquipmentView]:
    """The closest-fitting available items, as recommended at the counter."""
    recommendation = use_cases.recommend_equipment().execute(RecommendEquipmentQuery(customer_id))
    if member.board is EquipmentType.SKIS:
        boards = recommendation.skis
    else:
        boards = recommendation.snowboards
    if not boards:
        raise NothingFits(f"No available {member.board} in a fitting size and range.")
    if not recommendation.boots:
        raise NothingFits("No available boots in a fitting size and range.")
    items = [boards[0], recommendation.boots[0]]
    if member.helmet:
        query = ListAvailableEquipmentQuery(type=EquipmentType.HELMET)
        helmets = use_cases.list_available_equipment().execute(query)
        if not helmets:
            raise NothingFits("No helmet available.")
        items.append(helmets[0])
    return items
