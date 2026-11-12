from functools import cache

from pymongo import MongoClient
from pymongo.client_session import ClientSession
from pymongo.database import Database


@cache
def mongo_client(url: str) -> MongoClient:
    """One client per address: MongoClient is thread-safe and keeps its own connection pool."""
    return MongoClient(url, uuidRepresentation="standard", serverSelectionTimeoutMS=3000)


class MongoContext:
    """Shared by the repositories and the unit of work of one use case call.

    In MongoDB a transaction is a session that every read and write must receive (Django keeps
    its transaction implicitly instead). The unit of work opens the session here, and the
    repositories pass it along. Outside a unit of work, `session` is None.
    """

    def __init__(self, url: str, database: str) -> None:
        self.client = mongo_client(url)
        self.database: Database = self.client[database]
        self.session: ClientSession | None = None
