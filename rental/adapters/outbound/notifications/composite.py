from collections.abc import Sequence

from rental.application.ports.outbound.notifier import Notification, Notifier


class CompositeNotifier:
    """Passes every notification to several notifiers (e.g. logging and email).

    The services still see one Notifier: they never know how many channels there are.
    """

    def __init__(self, notifiers: Sequence[Notifier]) -> None:
        self._notifiers = list(notifiers)

    def notify(self, notification: Notification) -> None:
        for notifier in self._notifiers:
            notifier.notify(notification)
