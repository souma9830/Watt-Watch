"""
ByteTrack-based tracking module for WattWatch.
Provides persistent multi-person tracking with unique IDs.
"""

from .byte_tracker import ByteTracker, Track, TrackState
from .entry_exit_monitor import EntryExitMonitor, EntryExitEvent

__all__ = [
    "ByteTracker",
    "Track",
    "TrackState",
    "EntryExitMonitor",
    "EntryExitEvent",
]
