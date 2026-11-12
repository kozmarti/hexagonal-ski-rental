from django.conf import settings
from django.core.management.base import BaseCommand

from rental.adapters.outbound.mongo.context import mongo_client


class Command(BaseCommand):
    help = "Empties the MongoDB database (REPOSITORY_BACKEND=mongo), like flush for PostgreSQL."

    def handle(self, *args, **options):
        mongo_client(settings.MONGO_URL).drop_database(settings.MONGO_DB)
        self.stdout.write(self.style.SUCCESS(f"MongoDB database {settings.MONGO_DB} emptied."))
