import logging
from datetime import date
from uuid import UUID

import pytest

from rental.adapters.outbound.notifications.logging_notifier import LoggingNotifier
from rental.application.ports.outbound.notifier import (
    EquipmentSentToMaintenance,
    MaintenanceCompleted,
    RentalCreated,
    RentalReturned,
)
from tests.unit.factories import eur

RENTAL = UUID("00000000-0000-0000-0000-000000000001")
CUSTOMER = UUID("00000000-0000-0000-0000-000000000002")
SKIS = UUID("00000000-0000-0000-0000-000000000003")
BOOTS = UUID("00000000-0000-0000-0000-000000000004")


@pytest.mark.parametrize(
    ("notification", "message"),
    [
        (
            RentalCreated(RENTAL, CUSTOMER, (SKIS, BOOTS), eur("180")),
            f"Rental {RENTAL} created: 2 item(s), 180.00 EUR.",
        ),
        (
            RentalReturned(RENTAL, date(2026, 12, 22)),
            f"Rental {RENTAL} returned on 2026-12-22.",
        ),
        (
            EquipmentSentToMaintenance(SKIS, needs_repair=False),
            f"Equipment {SKIS} sent to maintenance: routine service.",
        ),
        (
            EquipmentSentToMaintenance(BOOTS, needs_repair=True),
            f"Equipment {BOOTS} sent to maintenance: needs repair.",
        ),
        (
            MaintenanceCompleted(SKIS),
            f"Equipment {SKIS} is available again.",
        ),
    ],
)
def test_each_notification_is_logged_as_a_readable_message(caplog, notification, message):
    with caplog.at_level(logging.INFO, logger="rental.notifications"):
        LoggingNotifier().notify(notification)

    assert caplog.messages == [message]
