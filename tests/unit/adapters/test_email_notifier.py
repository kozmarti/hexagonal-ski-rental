"""The email notifier, with Django's test mailbox: no mail server needed."""

import logging
import smtplib
from datetime import date
from uuid import UUID

import pytest

from rental.adapters.outbound.notifications import email_notifier
from rental.adapters.outbound.notifications.email_notifier import EmailNotifier
from rental.application.ports.outbound.notifier import (
    EquipmentSentToMaintenance,
    MaintenanceCompleted,
    RentalCreated,
    RentalReturned,
)
from tests.unit.factories import eur

RENTAL = UUID("00000000-0000-0000-0000-000000000001")
CUSTOMER = UUID("00000000-0000-0000-0000-000000000002")
SKIS = UUID("aaaaaaaa-0000-0000-0000-000000000003")
BOOTS = UUID("bbbbbbbb-0000-0000-0000-000000000004")


def notifier() -> EmailNotifier:
    return EmailNotifier(recipient="shop@example.com", sender="ski-rental@example.com")


def test_a_created_rental_is_emailed_to_the_shop(mailoutbox):
    notifier().notify(RentalCreated(RENTAL, CUSTOMER, (SKIS, BOOTS), eur("180")))

    (email,) = mailoutbox
    assert email.to == ["shop@example.com"]
    assert email.from_email == "ski-rental@example.com"
    assert email.subject == "Rental created: 2 item(s), 180.00 EUR"
    assert f"Customer {CUSTOMER}" in email.body
    assert f"- {BOOTS}" in email.body


@pytest.mark.parametrize(
    ("notification", "subject"),
    [
        (RentalReturned(RENTAL, date(2026, 12, 22)), "Rental returned on 2026-12-22"),
        (
            EquipmentSentToMaintenance(SKIS, needs_repair=True),
            "🔧 Repair needed: equipment aaaaaaaa",
        ),
        (
            EquipmentSentToMaintenance(SKIS, needs_repair=False),
            "Routine service: equipment aaaaaaaa",
        ),
        (MaintenanceCompleted(SKIS), "Available again: equipment aaaaaaaa"),
    ],
)
def test_every_notification_has_a_clear_subject(mailoutbox, notification, subject):
    notifier().notify(notification)

    assert [email.subject for email in mailoutbox] == [subject]


def test_an_email_that_cannot_be_sent_is_logged_and_never_breaks_the_rental(monkeypatch, caplog):
    def mail_server_down(*args, **kwargs):
        raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

    monkeypatch.setattr(email_notifier, "send_mail", mail_server_down)

    with caplog.at_level(logging.ERROR, logger="rental.notifications"):
        notifier().notify(MaintenanceCompleted(SKIS))

    assert "Email notification could not be sent: Available again" in caplog.text
