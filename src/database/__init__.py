"""
WattWatch Database Module.

Supports both SQLite (default) and MongoDB (when MONGO_URI is set).
The get_database() factory returns the correct backend automatically.
get_mongo() returns the MongoDB client (or None if not configured).
"""

import os

from src.database.connection import (
    DatabaseManager,
    DatabaseConfig,
    ConnectionPool,
    get_database
)
from src.database.schema import create_schema, drop_schema
from src.database.models import (
    WasteEvent,
    DetectionCount,
    EnergySaving,
    PrivacyConfig,
    ExportRow
)
from src.database.tracking_models import TrackingLog, EntryExitLog


def get_mongo():
    """
    Return the MongoDBManager singleton if MONGO_URI is set and pymongo is available.
    Returns None if MongoDB is not configured (falls back to SQLite).
    """
    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if not mongo_uri:
        return None
    try:
        from src.database.mongo_client import MongoDBManager
        return MongoDBManager.get_instance()
    except Exception as e:
        print(f"[DB] MongoDB unavailable: {e}")
        return None


__all__ = [
    # SQLite backend
    'DatabaseManager',
    'DatabaseConfig',
    'ConnectionPool',
    'get_database',
    'create_schema',
    'drop_schema',
    # SQLite models
    'WasteEvent',
    'DetectionCount',
    'EnergySaving',
    'PrivacyConfig',
    'ExportRow',
    # Tracking models
    'TrackingLog',
    'EntryExitLog',
    # MongoDB factory
    'get_mongo',
]
