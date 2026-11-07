from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel


@dataclass(frozen=True)
class RegisterCustomerCommand:
    name: str
    height_cm: int
    boot_size: Size
    skill_level: SkillLevel


@dataclass(frozen=True)
class RegisterCustomerResult:
    customer_id: UUID


class RegisterCustomer(Protocol):
    def execute(self, command: RegisterCustomerCommand) -> RegisterCustomerResult: ...
