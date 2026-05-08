"""
Tracking data models for MongoDB / extended storage.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
import time


@dataclass
class TrackingLog:
    """
    Per-frame log entry for a single tracked person.
    Stored in the `tracking_logs` MongoDB collection.
    """
    person_id: int
    camera_id: str
    bbox: List[float]          # [x1, y1, x2, y2]
    centroid: List[float]      # [cx, cy]
    confidence: float
    frame_number: int
    timestamp: float = field(default_factory=time.time)
    tracklet_len: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EntryExitLog:
    """
    Entry/Exit event record.
    Stored in the `entry_exit_events` MongoDB collection.
    """
    person_id: int
    camera_id: str
    event_type: str            # "ENTRY" or "EXIT"
    timestamp: float
    confidence: float
    frame_number: int
    snapshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
