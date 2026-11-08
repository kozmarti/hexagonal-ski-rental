from types import TracebackType
from typing import Self

from django.db import transaction


class DjangoUnitOfWork:
    """A database transaction: rolled back unless commit() was called inside the block."""

    def __enter__(self) -> Self:
        self._committed = False
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None and not self._committed:
            transaction.set_rollback(True)
        self._atomic.__exit__(exc_type, exc, traceback)

    def commit(self) -> None:
        self._committed = True
