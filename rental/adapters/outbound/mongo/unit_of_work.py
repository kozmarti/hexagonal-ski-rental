from types import TracebackType
from typing import Self

from rental.adapters.outbound.mongo.context import MongoContext


class MongoUnitOfWork:
    """A MongoDB transaction: aborted unless commit() was called inside the block."""

    def __init__(self, context: MongoContext) -> None:
        self._context = context

    def __enter__(self) -> Self:
        self._committed = False
        session = self._context.client.start_session()
        session.start_transaction()
        self._context.session = session
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session, self._context.session = self._context.session, None
        try:
            if exc_type is None and self._committed:
                session.commit_transaction()
            else:
                session.abort_transaction()
        finally:
            session.end_session()

    def commit(self) -> None:
        self._committed = True
