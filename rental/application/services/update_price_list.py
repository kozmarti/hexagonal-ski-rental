from rental.application.ports.inbound.update_price_list import (
    UpdatePriceListCommand,
    UpdatePriceListResult,
)
from rental.application.ports.outbound.price_list_repository import PriceListRepository
from rental.application.ports.outbound.unit_of_work import UnitOfWork
from rental.domain.exceptions import DomainError, InvalidPriceList
from rental.domain.pricing import Rate


class UpdatePriceListService:
    def __init__(self, price_list: PriceListRepository, uow: UnitOfWork) -> None:
        self._price_list = price_list
        self._uow = uow

    def execute(self, command: UpdatePriceListCommand) -> UpdatePriceListResult:
        rates = {}
        for change in command.changes:
            try:
                rates[(change.type, change.range)] = Rate(day=change.day, week=change.week)
            except DomainError as error:
                # Say which row is wrong: the domain rule does not know where it is shown.
                name = f"{change.type} {change.range}" if change.range else str(change.type)
                raise InvalidPriceList(f"{name.capitalize()}: {error}") from error

        with self._uow:
            self._price_list.save(self._price_list.get().with_rates(rates))
            self._uow.commit()
        return UpdatePriceListResult(changed=len(rates))
