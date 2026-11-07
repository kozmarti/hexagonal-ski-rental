from types import TracebackType
from typing import Protocol, Self


class UnitOfWork(Protocol):
    """A transaction boundary: changes are kept only if commit() is called inside the block.

    with uow:
        ...
        uow.commit()
    """

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...
