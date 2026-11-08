import logging

from rental.application.ports.outbound.notifier import (
    EquipmentSentToMaintenance,
    MaintenanceCompleted,
    Notification,
    RentalCreated,
    RentalReturned,
)

logger = logging.getLogger("rental.notifications")


class LoggingNotifier:
    """Writes every notification to the log. The only notification channel for now."""

    def notify(self, notification: Notification) -> None:
        logger.info(self._format(notification))

    @staticmethod
    def _format(notification: Notification) -> str:
        match notification:
            case RentalCreated(rental_id=rental_id, equipment_ids=ids, price=price):
                total = f"{price.amount} {price.currency}"
                return f"Rental {rental_id} created: {len(ids)} item(s), {total}."
            case RentalReturned(rental_id=rental_id, returned_on=returned_on):
                return f"Rental {rental_id} returned on {returned_on.isoformat()}."
            case EquipmentSentToMaintenance(equipment_id=equipment_id, needs_repair=True):
                return f"Equipment {equipment_id} sent to maintenance: needs repair."
            case EquipmentSentToMaintenance(equipment_id=equipment_id):
                return f"Equipment {equipment_id} sent to maintenance: routine service."
            case MaintenanceCompleted(equipment_id=equipment_id):
                return f"Equipment {equipment_id} is available again."
