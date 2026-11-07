class DomainError(Exception):
    """Base class for every business rule violation."""


class InvalidMoney(DomainError):
    pass


class CurrencyMismatch(DomainError):
    pass


class InvalidSize(DomainError):
    pass


class InvalidRentalPeriod(DomainError):
    pass


class InvalidEquipment(DomainError):
    pass


class InvalidCustomer(DomainError):
    pass


class EquipmentNotAvailable(DomainError):
    pass


class InvalidStatusTransition(DomainError):
    pass


class InvalidRental(DomainError):
    pass


class RentalAlreadyReturned(DomainError):
    pass


class InvalidPriceList(DomainError):
    pass


class PriceNotFound(DomainError):
    pass
