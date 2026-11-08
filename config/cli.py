# The CLI composition root: the command-line adapter receives its use cases from
# bootstrap.py here, outside the hexagon, exactly like the views in config/urls.py.
from rental import bootstrap
from rental.adapters.inbound.cli.app import UseCases

USE_CASES = UseCases(
    list_available_equipment=bootstrap.list_available_equipment,
    register_customer=bootstrap.register_customer,
    create_rental=bootstrap.create_rental,
    return_rental=bootstrap.return_rental,
)
