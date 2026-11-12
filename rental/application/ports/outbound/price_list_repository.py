from typing import Protocol

from rental.domain.pricing import PriceList


class PriceListRepository(Protocol):
    def get(self) -> PriceList: ...

    def save(self, price_list: PriceList) -> None: ...
