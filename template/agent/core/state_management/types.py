"""Session (state) backend enum. Used by state_management factory."""

from __future__ import annotations

from enum import Enum


class SessionBackend(str, Enum):
    """Supported session service backends. Set via SESSION_SERVICE_BACKEND env."""

    INMEMORY = "inmemory"
    FIRESTORE = "firestore"
    REDIS = "redis"
    MEMORYSTORE = "memorystore"
    POSTGRES = "postgres"
    MONGODB = "mongodb"
