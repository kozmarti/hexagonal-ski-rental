from rental.domain.pricing import PriceList


class InMemoryPriceList:
    """An editable price list kept in memory, for tests."""

    def __init__(self, initial: PriceList) -> None:
        self._price_list = initial

    def get(self) -> PriceList:
        return PriceList(dict(self._price_list.rates))

    def save(self, price_list: PriceList) -> None:
        self._price_list = PriceList(dict(price_list.rates))
