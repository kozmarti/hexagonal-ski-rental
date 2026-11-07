from typing import Self


class InMemoryUnitOfWork:
    """Records whether commit() was called. In-memory storage has no transaction to roll back."""

    def __init__(self) -> None:
        self.committed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def commit(self) -> None:
        self.committed = True
