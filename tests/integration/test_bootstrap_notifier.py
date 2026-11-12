"""NOTIFIERS chooses the notification channels; only bootstrap.py reads it."""

import logging

import pytest
from django.core.exceptions import ImproperlyConfigured

from rental import bootstrap
from rental.adapters.outbound.notifications.composite import CompositeNotifier
from rental.adapters.outbound.notifications.email_notifier import EmailNotifier
from rental.adapters.outbound.notifications.logging_notifier import LoggingNotifier
from rental.application.ports.outbound.notifier import MaintenanceCompleted
from tests.unit.factories import make_skis


def test_logging_is_the_default(settings):
    assert isinstance(bootstrap.notifier(), LoggingNotifier)


def test_email_alone(settings):
    settings.NOTIFIERS = ["email"]

    assert isinstance(bootstrap.notifier(), EmailNotifier)


def test_logging_and_email_together(settings, mailoutbox, caplog):
    settings.NOTIFIERS = ["logging", "email"]
    notifier = bootstrap.notifier()

    with caplog.at_level(logging.INFO, logger="rental.notifications"):
        notifier.notify(MaintenanceCompleted(make_skis().id))

    assert isinstance(notifier, CompositeNotifier)
    assert len(mailoutbox) == 1
    assert "is available again" in caplog.text


def test_an_unknown_channel_is_a_configuration_error(settings):
    settings.NOTIFIERS = ["logging", "sms"]

    with pytest.raises(ImproperlyConfigured, match="sms"):
        bootstrap.notifier()
