from datetime import date
from uuid import uuid4

from rental.adapters.outbound.memory.clock import FixedClock
from rental.adapters.outbound.memory.notifier import RecordingNotifier
from rental.adapters.outbound.memory.unit_of_work import InMemoryUnitOfWork
from rental.application.ports.outbound.notifier import MaintenanceCompleted


def test_fixed_clock_always_returns_the_same_day():
    clock = FixedClock(date(2026, 12, 20))

    assert clock.today() == date(2026, 12, 20)


def test_recording_notifier_keeps_sent_notifications():
    notifier = RecordingNotifier()
    notification = MaintenanceCompleted(equipment_id=uuid4())

    notifier.notify(notification)

    assert notifier.sent == [notification]


def test_unit_of_work_records_commit():
    uow = InMemoryUnitOfWork()

    with uow:
        assert not uow.committed
        uow.commit()

    assert uow.committed
