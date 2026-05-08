"""
Entry/Exit Monitor using virtual line crossing detection.

A horizontal line is drawn across the frame at a configurable ratio.
When a tracked person's centroid crosses this line:
  - Downward crossing (y increasing) → ENTRY
  - Upward crossing (y decreasing)   → EXIT

Events are emitted with person_id, camera_id, event_type, timestamp.
"""

import time
import os
import cv2
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any

from .byte_tracker import Track


@dataclass
class EntryExitEvent:
    """An entry or exit event for a tracked person."""
    person_id: int
    camera_id: str
    event_type: str          # "ENTRY" or "EXIT"
    timestamp: float
    confidence: float
    frame_number: int
    snapshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EntryExitMonitor:
    """
    Monitors tracked persons crossing a virtual horizontal line.

    The virtual line is at y = frame_height * line_ratio.
    Line ratio 0.5 means the midpoint of the frame.

    Cooldown prevents repeated events for the same person.
    """

    def __init__(
        self,
        line_ratio: float = 0.5,
        min_crossing_frames: int = 2,
        cooldown_seconds: float = 3.0,
        snapshot_dir: Optional[str] = None,
    ):
        """
        Args:
            line_ratio: fraction of frame height for the virtual line (0.0–1.0)
            min_crossing_frames: require N consistent frames before firing event
            cooldown_seconds: min seconds between events for the same person
            snapshot_dir: if set, save frame snapshot when event fires
        """
        self.line_ratio = line_ratio
        self.min_crossing_frames = min_crossing_frames
        self.cooldown_seconds = cooldown_seconds
        self.snapshot_dir = snapshot_dir

        # Track each person's recent centroid history (id → deque of y positions)
        self._centroid_history: Dict[int, List[float]] = {}
        # Last event time per person (id → timestamp)
        self._last_event_time: Dict[int, float] = {}
        # Last event type per person (id → "ENTRY"/"EXIT") to avoid duplicate
        self._last_event_type: Dict[int, str] = {}

        self._history_len = max(min_crossing_frames + 2, 5)

        if snapshot_dir:
            os.makedirs(snapshot_dir, exist_ok=True)

    def update(
        self,
        tracks: List[Track],
        frame_height: int,
        frame_width: int,
        frame_number: int,
        camera_id: str,
        frame: Optional[np.ndarray] = None,
    ) -> List[EntryExitEvent]:
        """
        Compute entry/exit events for this frame.

        Args:
            tracks: list of active Track objects
            frame_height: height of the video frame
            frame_width: width of the video frame
            frame_number: current frame index
            camera_id: camera/room identifier
            frame: current frame (optional, for saving snapshots)

        Returns:
            List of new EntryExitEvent objects fired this frame
        """
        events: List[EntryExitEvent] = []
        line_y = frame_height * self.line_ratio
        now = time.time()

        active_ids = {t.track_id for t in tracks}

        # Prune history for tracks that are no longer active
        stale_ids = set(self._centroid_history.keys()) - active_ids
        for sid in stale_ids:
            self._centroid_history.pop(sid, None)

        for track in tracks:
            tid = track.track_id
            _, cy = track.centroid

            # Accumulate centroid history
            if tid not in self._centroid_history:
                self._centroid_history[tid] = []
            history = self._centroid_history[tid]
            history.append(cy)
            if len(history) > self._history_len:
                history.pop(0)

            if len(history) < self.min_crossing_frames + 1:
                continue

            # Check cooldown
            last_t = self._last_event_time.get(tid, 0.0)
            if now - last_t < self.cooldown_seconds:
                continue

            # Detect crossing: compare oldest vs newest position relative to line
            prev_y = history[-(self.min_crossing_frames + 1)]
            curr_y = history[-1]

            crossed_down = prev_y < line_y <= curr_y   # entering (top → bottom)
            crossed_up = prev_y > line_y >= curr_y     # exiting (bottom → top)

            if not crossed_down and not crossed_up:
                continue

            event_type = "ENTRY" if crossed_down else "EXIT"

            # Avoid firing the same event type twice in a row
            if self._last_event_type.get(tid) == event_type:
                continue

            # Save snapshot if enabled
            snapshot_path = None
            if frame is not None and self.snapshot_dir:
                snapshot_path = self._save_snapshot(frame, tid, event_type, frame_number)

            event = EntryExitEvent(
                person_id=tid,
                camera_id=camera_id,
                event_type=event_type,
                timestamp=now,
                confidence=float(track.score),
                frame_number=frame_number,
                snapshot_path=snapshot_path,
            )
            events.append(event)

            self._last_event_time[tid] = now
            self._last_event_type[tid] = event_type

        return events

    def _save_snapshot(
        self,
        frame: np.ndarray,
        person_id: int,
        event_type: str,
        frame_number: int,
    ) -> Optional[str]:
        """Save a JPEG snapshot of the frame when an event fires."""
        try:
            filename = f"{event_type}_{person_id}_{frame_number}_{int(time.time())}.jpg"
            path = os.path.join(self.snapshot_dir, filename)
            cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            return path
        except Exception as e:
            print(f"[EntryExitMonitor] Snapshot error: {e}")
            return None

    def draw_line(
        self,
        frame: np.ndarray,
        color: Tuple[int, int, int] = (0, 255, 255),
        thickness: int = 2,
        label: str = "VIRTUAL_LINE",
    ) -> np.ndarray:
        """Draw the virtual entry/exit line on the frame (in-place)."""
        h, w = frame.shape[:2]
        line_y = int(h * self.line_ratio)
        cv2.line(frame, (0, line_y), (w, line_y), color, thickness)
        cv2.putText(
            frame, label,
            (10, line_y - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45,
            color, 1,
        )
        return frame

    def draw_events_flash(
        self,
        frame: np.ndarray,
        events: List[EntryExitEvent],
    ) -> np.ndarray:
        """
        Draw a brief flash/overlay on the frame for recent entry/exit events.
        ENTRY = green flash, EXIT = red flash.
        """
        if not events:
            return frame

        h, w = frame.shape[:2]
        overlay = frame.copy()

        for event in events:
            color = (0, 200, 50) if event.event_type == "ENTRY" else (50, 50, 220)
            label = f"{'→ ENTRY' if event.event_type == 'ENTRY' else '← EXIT'} ID:{event.person_id}"
            cv2.rectangle(overlay, (0, 0), (w, h), color, 6)
            cv2.putText(
                frame, label,
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                color, 2,
            )

        # Blend
        frame = cv2.addWeighted(overlay, 0.15, frame, 0.85, 0)
        return frame
