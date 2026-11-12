from uuid import uuid4

import pytest
from django.conf import settings as django_settings

from rental.adapters.outbound.mongo.context import MongoContext, mongo_client


@pytest.fixture(autouse=True)
def isolated_storage(settings):
    """Tests never follow the developer's .env choices of database and notifiers.

    With REPOSITORY_BACKEND=mongo in .env, tests going through bootstrap.py would otherwise run
    on the developer's own MongoDB data. By default they use the ORM, on pytest-django's test
    database; MongoDB tests opt in with their own temporary database (`mongo_context`).
    Notifications go to the log; tests about email opt in (Django's test mailbox catches it).
    With DEBUG off (CI, or a .env without DJANGO_DEBUG=1) the production settings redirect
    every plain HTTP request to HTTPS: the test client speaks plain HTTP, so no redirect.
    """
    settings.REPOSITORY_BACKEND = "orm"
    settings.MONGO_DB = f"test_{uuid4().hex[:12]}"
    settings.NOTIFIERS = ["logging"]
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture
def mongo_context():
    """A MongoDB database of its own for one test, dropped afterwards."""
    name = f"test_{uuid4().hex[:12]}"
    yield MongoContext(django_settings.MONGO_URL, name)
    mongo_client(django_settings.MONGO_URL).drop_database(name)
