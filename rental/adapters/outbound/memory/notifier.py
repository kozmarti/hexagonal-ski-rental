from rental.application.ports.outbound.notifier import Notification


class RecordingNotifier:
    """Keeps every notification so tests can check what was sent."""

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def notify(self, notification: Notification) -> None:
        self.sent.append(notification)
