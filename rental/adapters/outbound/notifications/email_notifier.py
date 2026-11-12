import logging

from django.core.mail import send_mail

from rental.application.ports.outbound.notifier import (
    EquipmentSentToMaintenance,
    MaintenanceCompleted,
    Notification,
    RentalCreated,
    RentalReturned,
)

logger = logging.getLogger("rental.notifications")


class EmailNotifier:
    """Emails every notification to the shop. Customers have no email address yet: when they
    do, a confirmation to the customer belongs here too.

    An email that cannot be sent never breaks the rental (notifications are sent after the
    commit anyway): the failure is logged instead.
    """

    def __init__(self, recipient: str, sender: str) -> None:
        self._recipient = recipient
        self._sender = sender

    def notify(self, notification: Notification) -> None:
        subject, body = self._message(notification)
        try:
            send_mail(subject, body, self._sender, [self._recipient])
        except OSError:
            # SMTP and network errors are OSErrors.
            logger.exception("Email notification could not be sent: %s", subject)

    @staticmethod
    def _message(notification: Notification) -> tuple[str, str]:
        match notification:
            case RentalCreated(rental_id=rental_id, customer_id=customer_id, price=price):
                total = f"{price.amount} {price.currency}"
                count = len(notification.equipment_ids)
                lines = [f"Rental {rental_id}", f"Customer {customer_id}", f"Price {total}"]
                lines += ["Items:", *(f"- {item_id}" for item_id in notification.equipment_ids)]
                return f"Rental created: {count} item(s), {total}", "\n".join(lines) + "\n"
            case RentalReturned(rental_id=rental_id, returned_on=returned_on):
                return (
                    f"Rental returned on {returned_on.isoformat()}",
                    f"Rental {rental_id} was returned. Its items are in maintenance.\n",
                )
            case EquipmentSentToMaintenance(equipment_id=equipment_id, needs_repair=True):
                return (
                    f"🔧 Repair needed: equipment {str(equipment_id)[:8]}",
                    f"Equipment {equipment_id} came back damaged and needs a repair.\n",
                )
            case EquipmentSentToMaintenance(equipment_id=equipment_id):
                return (
                    f"Routine service: equipment {str(equipment_id)[:8]}",
                    f"Equipment {equipment_id} came back and needs its routine service.\n",
                )
            case MaintenanceCompleted(equipment_id=equipment_id):
                return (
                    f"Available again: equipment {str(equipment_id)[:8]}",
                    f"Equipment {equipment_id} is serviced and available again.\n",
                )
