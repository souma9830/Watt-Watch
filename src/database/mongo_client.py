"""
MongoDB client for WattWatch.

Collections:
  - tracking_logs      : per-frame bounding box + ID data
  - entry_exit_events  : entry/exit crossing events
  - waste_events       : energy waste alerts
  - detection_counts   : periodic room-level person counts
  - energy_logs        : daily energy summaries

Indexes are created on startup for timestamp, person_id, camera_id.

Usage:
    # Set MONGO_URI in .env, e.g.:
    # MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/wattwatch
    client = MongoDBManager()
    client.log_tracking(...)
    client.log_entry_exit(...)
"""

import os
import time
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING, errors as mongo_errors
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None


class MongoDBManager:
    """
    Thread-safe MongoDB manager for WattWatch.
    Falls back gracefully if pymongo is not installed or URI is not set.
    """

    _instance: Optional['MongoDBManager'] = None
    _lock = threading.Lock()

    def __init__(self, uri: Optional[str] = None, db_name: str = "wattwatch"):
        self._uri = uri or os.getenv("MONGO_URI", "")
        self._db_name = db_name
        self._client = None
        self._db = None
        self._connected = False
        self._write_lock = threading.Lock()

        if not PYMONGO_AVAILABLE:
            print("[MongoDB] pymongo not installed. Install with: pip install pymongo")
            return

        if not self._uri:
            print("[MongoDB] MONGO_URI not set in .env — MongoDB disabled.")
            return

        self._connect()

    def _connect(self):
        """Establish MongoDB connection and create indexes."""
        try:
            self._client = MongoClient(
                self._uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )
            # Force connection check
            self._client.admin.command('ping')
            self._db = self._client[self._db_name]
            self._connected = True
            self._create_indexes()
            print(f"[MongoDB] Connected to database: '{self._db_name}'")
        except Exception as e:
            print(f"[MongoDB] Connection failed: {e}")
            self._connected = False

    def _create_indexes(self):
        """Create indexes for all collections."""
        try:
            # tracking_logs indexes
            tl = self._db["tracking_logs"]
            tl.create_index([("camera_id", ASCENDING), ("timestamp", DESCENDING)])
            tl.create_index([("person_id", ASCENDING)])
            tl.create_index([("timestamp", DESCENDING)])

            # entry_exit_events indexes
            ee = self._db["entry_exit_events"]
            ee.create_index([("camera_id", ASCENDING), ("timestamp", DESCENDING)])
            ee.create_index([("person_id", ASCENDING)])
            ee.create_index([("event_type", ASCENDING)])
            ee.create_index([("timestamp", DESCENDING)])

            # waste_events indexes
            we = self._db["waste_events"]
            we.create_index([("room_id", ASCENDING), ("timestamp", DESCENDING)])
            we.create_index([("timestamp", DESCENDING)])

            # detection_counts indexes
            dc = self._db["detection_counts"]
            dc.create_index([("room_id", ASCENDING), ("timestamp", DESCENDING)])

            # energy_logs indexes
            el = self._db["energy_logs"]
            el.create_index([("room_id", ASCENDING), ("date", DESCENDING)], unique=True)

            print("[MongoDB] Indexes created successfully")
        except Exception as e:
            print(f"[MongoDB] Index creation error: {e}")

    @classmethod
    def get_instance(cls) -> 'MongoDBManager':
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def is_connected(self) -> bool:
        return self._connected and self._db is not None

    # ------------------------------------------------------------------
    # Tracking Log
    # ------------------------------------------------------------------

    def log_tracking(self, tracking_log: Dict[str, Any]) -> bool:
        """Insert a tracking log document."""
        if not self.is_connected:
            return False
        try:
            with self._write_lock:
                self._db["tracking_logs"].insert_one(tracking_log)
            return True
        except Exception as e:
            print(f"[MongoDB] log_tracking error: {e}")
            return False

    def log_tracking_batch(self, logs: List[Dict[str, Any]]) -> bool:
        """Insert many tracking log documents at once."""
        if not self.is_connected or not logs:
            return False
        try:
            with self._write_lock:
                self._db["tracking_logs"].insert_many(logs, ordered=False)
            return True
        except Exception as e:
            print(f"[MongoDB] log_tracking_batch error: {e}")
            return False

    # ------------------------------------------------------------------
    # Entry/Exit Events
    # ------------------------------------------------------------------

    def log_entry_exit(self, event: Dict[str, Any]) -> bool:
        """Insert an entry/exit event document."""
        if not self.is_connected:
            return False
        try:
            with self._write_lock:
                self._db["entry_exit_events"].insert_one(event)
            return True
        except Exception as e:
            print(f"[MongoDB] log_entry_exit error: {e}")
            return False

    def get_entry_exit_events(
        self,
        camera_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent entry/exit events."""
        if not self.is_connected:
            return []
        try:
            query = {}
            if camera_id:
                query["camera_id"] = camera_id
            cursor = (
                self._db["entry_exit_events"]
                .find(query, {"_id": 0})
                .sort("timestamp", DESCENDING)
                .limit(limit)
            )
            return list(cursor)
        except Exception as e:
            print(f"[MongoDB] get_entry_exit_events error: {e}")
            return []

    # ------------------------------------------------------------------
    # Waste Events (mirrors SQLite waste_events)
    # ------------------------------------------------------------------

    def log_waste_event(self, event: Dict[str, Any]) -> bool:
        """Insert a waste event document."""
        if not self.is_connected:
            return False
        try:
            with self._write_lock:
                self._db["waste_events"].insert_one(event)
            return True
        except Exception as e:
            print(f"[MongoDB] log_waste_event error: {e}")
            return False

    def get_waste_events(
        self,
        room_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent waste events."""
        if not self.is_connected:
            return []
        try:
            query = {}
            if room_id:
                query["room_id"] = room_id
            cursor = (
                self._db["waste_events"]
                .find(query, {"_id": 0})
                .sort("timestamp", DESCENDING)
                .limit(limit)
            )
            return list(cursor)
        except Exception as e:
            print(f"[MongoDB] get_waste_events error: {e}")
            return []

    # ------------------------------------------------------------------
    # Detection Counts
    # ------------------------------------------------------------------

    def log_detection(self, room_id: str, timestamp: float, person_count: int,
                      light_status: str, fan_status: str, monitor_status: str) -> bool:
        """Insert a detection count document."""
        if not self.is_connected:
            return False
        try:
            doc = {
                "room_id": room_id,
                "timestamp": timestamp,
                "person_count": person_count,
                "light_status": light_status,
                "fan_status": fan_status,
                "monitor_status": monitor_status,
                "created_at": datetime.utcnow().isoformat(),
            }
            with self._write_lock:
                self._db["detection_counts"].insert_one(doc)
            return True
        except Exception as e:
            print(f"[MongoDB] log_detection error: {e}")
            return False

    # ------------------------------------------------------------------
    # Stats / Health
    # ------------------------------------------------------------------

    def get_collection_counts(self) -> Dict[str, int]:
        """Return document counts per collection."""
        if not self.is_connected:
            return {}
        try:
            collections = [
                "tracking_logs", "entry_exit_events",
                "waste_events", "detection_counts", "energy_logs"
            ]
            return {col: self._db[col].count_documents({}) for col in collections}
        except Exception as e:
            print(f"[MongoDB] get_collection_counts error: {e}")
            return {}

    def close(self):
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._connected = False
            print("[MongoDB] Connection closed")
