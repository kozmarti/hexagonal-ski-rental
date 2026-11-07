from dataclasses import dataclass
from uuid import UUID


@dataclass(eq=False)
class Entity:
    """An entity is identified by its id, not by its attribute values."""

    id: UUID

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)
