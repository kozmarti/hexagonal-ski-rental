from datetime import date

from django.utils import timezone


class SystemClock:
    def today(self) -> date:
        """Today in the shop's time zone (TIME_ZONE setting), not the server's."""
        return timezone.localdate()
