from uuid import uuid4

from rental.adapters.outbound.memory.notifier import RecordingNotifier
from rental.adapters.outbound.notifications.composite import CompositeNotifier
from rental.application.ports.outbound.notifier import MaintenanceCompleted


def test_every_notifier_receives_every_notification():
    logs, emails = RecordingNotifier(), RecordingNotifier()
    notification = MaintenanceCompleted(uuid4())

    CompositeNotifier([logs, emails]).notify(notification)

    assert logs.sent == emails.sent == [notification]
