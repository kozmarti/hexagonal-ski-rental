from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class RemoveCustomerCommand:
    customer_id: UUID


@dataclass(frozen=True)
class RemoveCustomerResult:
    customer_id: UUID


class RemoveCustomer(Protocol):
    def execute(self, command: RemoveCustomerCommand) -> RemoveCustomerResult: ...
