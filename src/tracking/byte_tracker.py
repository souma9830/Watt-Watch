"""
ByteTrack-compatible multi-object tracker.

Implements the core ByteTrack algorithm:
  - High-confidence detections matched first
  - Low-confidence detections matched to lost tracks (re-identification)
  - Kalman filter for motion prediction
  - IoU + score based matching via linear_sum_assignment (scipy/numpy)

Reference: Zhang et al., "ByteTrack: Multi-Object Tracking by Associating
           Every Detection Box", ECCV 2022.
"""

import numpy as np
import time
from enum import IntEnum
from typing import List, Dict, Any, Tuple, Optional

from .kalman_filter import KalmanFilter


class TrackState(IntEnum):
    TRACKED = 1   # Currently visible
    LOST = 2      # Temporarily invisible
    REMOVED = 3   # Removed from tracking


def _iou_batch(bboxes_a: np.ndarray, bboxes_b: np.ndarray) -> np.ndarray:
    """
    Compute pairwise IoU between two sets of bounding boxes.
    Both inputs: [N/M, 4] in [x1, y1, x2, y2] format.
    Returns: [N, M] IoU matrix.
    """
    if len(bboxes_a) == 0 or len(bboxes_b) == 0:
        return np.zeros((len(bboxes_a), len(bboxes_b)), dtype=np.float32)

    ax1 = bboxes_a[:, 0:1]
    ay1 = bboxes_a[:, 1:2]
    ax2 = bboxes_a[:, 2:3]
    ay2 = bboxes_a[:, 3:4]

    bx1 = bboxes_b[:, 0]
    by1 = bboxes_b[:, 1]
    bx2 = bboxes_b[:, 2]
    by2 = bboxes_b[:, 3]

    inter_x1 = np.maximum(ax1, bx1)
    inter_y1 = np.maximum(ay1, by1)
    inter_x2 = np.minimum(ax2, bx2)
    inter_y2 = np.minimum(ay2, by2)

    inter_area = np.maximum(0, inter_x2 - inter_x1) * np.maximum(0, inter_y2 - inter_y1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)

    union = area_a + area_b - inter_area
    iou = np.where(union > 0, inter_area / union, 0.0)
    return iou.astype(np.float32)


def _linear_assignment(cost_matrix: np.ndarray) -> np.ndarray:
    """
    Solve linear assignment problem.
    Falls back to greedy matching if scipy unavailable.
    Returns array of shape [N, 2] with (row, col) pairs.
    """
    try:
        from scipy.optimize import linear_sum_assignment
        rows, cols = linear_sum_assignment(cost_matrix)
        return np.stack([rows, cols], axis=1)
    except ImportError:
        # Greedy fallback
        n_rows, n_cols = cost_matrix.shape
        assignments = []
        used_cols = set()
        for row in range(n_rows):
            best_col = -1
            best_cost = float('inf')
            for col in range(n_cols):
                if col not in used_cols and cost_matrix[row, col] < best_cost:
                    best_cost = cost_matrix[row, col]
                    best_col = col
            if best_col >= 0:
                assignments.append([row, best_col])
                used_cols.add(best_col)
        return np.array(assignments) if assignments else np.empty((0, 2), dtype=int)


def _xywh_to_xyxy(xywh: np.ndarray) -> np.ndarray:
    """Convert [cx, cy, w, h] → [x1, y1, x2, y2]."""
    xy = xywh.copy()
    xy[..., 0] = xywh[..., 0] - xywh[..., 2] / 2
    xy[..., 1] = xywh[..., 1] - xywh[..., 3] / 2
    xy[..., 2] = xywh[..., 0] + xywh[..., 2] / 2
    xy[..., 3] = xywh[..., 1] + xywh[..., 3] / 2
    return xy


def _xyxy_to_xywh(xyxy: np.ndarray) -> np.ndarray:
    """Convert [x1, y1, x2, y2] → [cx, cy, w, h]."""
    xywh = xyxy.copy()
    xywh[..., 0] = (xyxy[..., 0] + xyxy[..., 2]) / 2
    xywh[..., 1] = (xyxy[..., 1] + xyxy[..., 3]) / 2
    xywh[..., 2] = xyxy[..., 2] - xyxy[..., 0]
    xywh[..., 3] = xyxy[..., 3] - xyxy[..., 1]
    return xywh


class Track:
    """Represents a single tracked person."""

    _id_counter = 0

    @classmethod
    def _next_id(cls) -> int:
        cls._id_counter += 1
        return cls._id_counter

    @classmethod
    def reset_id_counter(cls):
        cls._id_counter = 0

    def __init__(self, bbox_xyxy: np.ndarray, score: float, kalman: KalmanFilter):
        """
        Args:
            bbox_xyxy: [x1, y1, x2, y2]
            score: detection confidence
            kalman: shared KalmanFilter instance
        """
        self.track_id = self._next_id()
        self.state = TrackState.TRACKED
        self.score = score
        self.is_activated = False
        self.frame_id = 0
        self.start_frame = 0
        self.tracklet_len = 0

        # Kalman state
        self._kalman = kalman
        bbox_xywh = _xyxy_to_xywh(bbox_xyxy.astype(np.float64))
        self.mean, self.covariance = kalman.initiate(bbox_xywh)

        # History for trail visualization (last N centroids)
        self.trail: List[Tuple[int, int]] = []
        self._max_trail = 30

        # Timestamps
        self.first_seen = time.time()
        self.last_seen = time.time()

    @property
    def bbox_xyxy(self) -> np.ndarray:
        """Current bounding box as [x1, y1, x2, y2]."""
        return _xywh_to_xyxy(self.mean[:4])

    @property
    def centroid(self) -> Tuple[float, float]:
        """Centroid (cx, cy) from Kalman mean."""
        return float(self.mean[0]), float(self.mean[1])

    def predict(self):
        """Predict next state with Kalman."""
        self.mean, self.covariance = self._kalman.predict(self.mean, self.covariance)

    def activate(self, frame_id: int):
        """Activate a newly created track."""
        self.frame_id = frame_id
        self.start_frame = frame_id
        self.is_activated = True
        self.tracklet_len = 1
        cx, cy = self.centroid
        self.trail.append((int(cx), int(cy)))

    def update(self, detection_bbox_xyxy: np.ndarray, score: float, frame_id: int):
        """Update track with new detection."""
        self.frame_id = frame_id
        self.tracklet_len += 1
        self.score = score
        self.state = TrackState.TRACKED
        self.last_seen = time.time()

        bbox_xywh = _xyxy_to_xywh(detection_bbox_xyxy.astype(np.float64))
        self.mean, self.covariance = self._kalman.update(
            self.mean, self.covariance, bbox_xywh
        )

        # Update trail
        cx, cy = self.centroid
        self.trail.append((int(cx), int(cy)))
        if len(self.trail) > self._max_trail:
            self.trail.pop(0)

    def mark_lost(self):
        self.state = TrackState.LOST

    def mark_removed(self):
        self.state = TrackState.REMOVED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for WebSocket/API output."""
        bbox = self.bbox_xyxy
        return {
            "id": self.track_id,
            "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
            "confidence": float(self.score),
            "centroid": [float(self.mean[0]), float(self.mean[1])],
            "trail": list(self.trail[-15:]),  # Last 15 points
            "tracklet_len": self.tracklet_len,
            "state": int(self.state),
        }


class ByteTracker:
    """
    ByteTrack-compatible multi-person tracker.

    Algorithm:
    1. Separate detections into high/low confidence
    2. Match high-confidence detections to active tracks (IoU + Kalman gate)
    3. Match low-confidence detections to unmatched tracks (IoU)
    4. Initialize new tracks from unmatched high-confidence detections
    5. Remove tracks that have been lost for too long
    """

    def __init__(
        self,
        track_buffer: int = 30,
        match_threshold: float = 0.8,
        high_threshold: float = 0.6,
        low_threshold: float = 0.1,
        min_box_area: float = 10.0,
    ):
        """
        Args:
            track_buffer: frames to keep lost tracks alive
            match_threshold: IoU threshold for matching (higher = stricter)
            high_threshold: min confidence for first-pass matching
            low_threshold: min confidence for second-pass (ByteTrack recovery)
            min_box_area: ignore detections smaller than this (px²)
        """
        self.track_buffer = track_buffer
        self.match_threshold = match_threshold
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.min_box_area = min_box_area

        self._kalman = KalmanFilter()
        self._tracked_tracks: List[Track] = []   # currently tracked
        self._lost_tracks: List[Track] = []       # temporarily lost
        self._removed_tracks: List[Track] = []    # to be garbage collected

        self.frame_id = 0

    def reset(self):
        """Reset tracker state."""
        self._tracked_tracks.clear()
        self._lost_tracks.clear()
        self._removed_tracks.clear()
        self.frame_id = 0
        Track.reset_id_counter()

    def update(self, detections: List[Dict[str, Any]]) -> List[Track]:
        """
        Process detections for one frame and return active tracks.

        Args:
            detections: list of dicts with 'bbox' [x1,y1,x2,y2] and 'confidence'

        Returns:
            List of active Track objects
        """
        self.frame_id += 1

        # --- Parse detections ---
        det_boxes = []
        det_scores = []
        for d in detections:
            bbox = d.get("bbox", [])
            score = float(d.get("confidence", 0.5))
            if len(bbox) != 4:
                continue
            x1, y1, x2, y2 = bbox
            area = (x2 - x1) * (y2 - y1)
            if area < self.min_box_area:
                continue
            det_boxes.append([x1, y1, x2, y2])
            det_scores.append(score)

        if not det_boxes:
            # No detections — mark all tracks as lost
            for t in self._tracked_tracks:
                t.mark_lost()
                t.predict()
            self._lost_tracks.extend(self._tracked_tracks)
            self._tracked_tracks.clear()
            self._remove_old_lost_tracks()
            return []

        det_boxes = np.array(det_boxes, dtype=np.float32)
        det_scores = np.array(det_scores, dtype=np.float32)

        # Split into high/low confidence
        high_mask = det_scores >= self.high_threshold
        low_mask = (det_scores >= self.low_threshold) & ~high_mask

        high_boxes = det_boxes[high_mask]
        high_scores = det_scores[high_mask]
        low_boxes = det_boxes[low_mask]
        low_scores = det_scores[low_mask]

        # --- Predict all existing tracks ---
        for t in self._tracked_tracks + self._lost_tracks:
            t.predict()

        # Active tracks = currently tracked + recently lost (for recovery)
        active_tracks = [t for t in self._tracked_tracks if t.is_activated]
        unconfirmed_tracks = [t for t in self._tracked_tracks if not t.is_activated]

        # ======================================
        # STEP 1: Match high-confidence detections to active tracks
        # ======================================
        matched_track_indices, matched_det_high, unmatched_tracks_1, unmatched_det_high = \
            self._match(active_tracks, high_boxes, high_scores, threshold=self.match_threshold)

        newly_activated = []
        for t_idx, d_idx in zip(matched_track_indices, matched_det_high):
            active_tracks[t_idx].update(high_boxes[d_idx], high_scores[d_idx], self.frame_id)
        
        # Unmatched active tracks from step 1 become temporarily lost
        lost_after_1 = [active_tracks[i] for i in unmatched_tracks_1]
        for t in lost_after_1:
            t.mark_lost()

        # ======================================
        # STEP 2: Match low-confidence detections to unmatched active + lost tracks
        # ======================================
        candidate_tracks = lost_after_1 + self._lost_tracks
        if len(low_boxes) > 0 and len(candidate_tracks) > 0:
            matched_t2, matched_d_low, _, _ = self._match(
                candidate_tracks, low_boxes, low_scores, threshold=0.5
            )
            for t_idx, d_idx in zip(matched_t2, matched_d_low):
                t = candidate_tracks[t_idx]
                t.update(low_boxes[d_idx], low_scores[d_idx], self.frame_id)
                if t.state == TrackState.LOST:
                    t.state = TrackState.TRACKED
                newly_activated.append(t)

            # Remaining lost
            recovered_set = set(t_idx for t_idx, _ in zip(matched_t2, matched_d_low))
            for i, t in enumerate(candidate_tracks):
                if i not in recovered_set and t.state != TrackState.LOST:
                    t.mark_lost()

        # ======================================
        # STEP 3: Match remaining high-conf detections to unconfirmed tracks
        # ======================================
        matched_unc, matched_d_unc, unmatched_unc, unmatched_det_final = \
            self._match(unconfirmed_tracks, high_boxes[unmatched_det_high],
                        high_scores[unmatched_det_high], threshold=0.7)

        for t_idx, d_idx in zip(matched_unc, matched_d_unc):
            det_original_idx = np.where(unmatched_det_high)[0][d_idx] \
                if isinstance(unmatched_det_high, np.ndarray) else unmatched_det_high[d_idx]
            unconfirmed_tracks[t_idx].update(
                high_boxes[det_original_idx], high_scores[det_original_idx], self.frame_id
            )
            newly_activated.append(unconfirmed_tracks[t_idx])

        for i in unmatched_unc:
            unconfirmed_tracks[i].mark_removed()

        # ======================================
        # STEP 4: Create new tracks for truly unmatched high-conf detections
        # ======================================
        unmatched_det_final_indices = list(unmatched_det_high)
        for d_idx in unmatched_det_final_indices:
            score = high_scores[d_idx]
            if score < self.high_threshold:
                continue
            new_track = Track(high_boxes[d_idx], score, self._kalman)
            new_track.activate(self.frame_id)
            newly_activated.append(new_track)

        # ======================================
        # STEP 5: Promote lost tracks that were recovered + expire old ones
        # ======================================
        self._remove_old_lost_tracks()

        # Rebuild tracked list
        current_tracked = []
        for t in self._tracked_tracks:
            if t.state == TrackState.TRACKED:
                current_tracked.append(t)
            elif t.state == TrackState.LOST and t not in lost_after_1:
                self._lost_tracks.append(t)

        for t in lost_after_1:
            if t.state == TrackState.LOST:
                if t not in self._lost_tracks:
                    self._lost_tracks.append(t)

        self._tracked_tracks = current_tracked + [
            t for t in newly_activated if t.state == TrackState.TRACKED
        ]

        # Remove duplicates
        seen = set()
        unique_tracked = []
        for t in self._tracked_tracks:
            if t.track_id not in seen:
                seen.add(t.track_id)
                unique_tracked.append(t)
        self._tracked_tracks = unique_tracked

        return [t for t in self._tracked_tracks if t.is_activated]

    def _match(
        self,
        tracks: List[Track],
        det_boxes: np.ndarray,
        det_scores: np.ndarray,
        threshold: float
    ) -> Tuple[List[int], List[int], List[int], List[int]]:
        """
        Match detections to tracks using IoU cost matrix + linear assignment.

        Returns:
            (matched_track_indices, matched_det_indices,
             unmatched_track_indices, unmatched_det_indices)
        """
        if len(tracks) == 0 or len(det_boxes) == 0:
            return [], [], list(range(len(tracks))), list(range(len(det_boxes)))

        track_boxes = np.array([t.bbox_xyxy for t in tracks], dtype=np.float32)
        iou_matrix = _iou_batch(track_boxes, det_boxes)
        cost_matrix = 1.0 - iou_matrix  # lower cost = better match

        assignments = _linear_assignment(cost_matrix)

        matched_tracks, matched_dets = [], []
        unmatched_tracks = list(range(len(tracks)))
        unmatched_dets = list(range(len(det_boxes)))

        for row, col in assignments:
            if cost_matrix[row, col] > (1.0 - threshold):
                continue  # IoU too low
            matched_tracks.append(row)
            matched_dets.append(col)

        unmatched_tracks = [i for i in range(len(tracks)) if i not in matched_tracks]
        unmatched_dets = [i for i in range(len(det_boxes)) if i not in matched_dets]

        return matched_tracks, matched_dets, unmatched_tracks, unmatched_dets

    def _remove_old_lost_tracks(self):
        """Remove tracks that have been lost for too long."""
        remaining_lost = []
        for t in self._lost_tracks:
            frames_lost = self.frame_id - t.frame_id
            if frames_lost > self.track_buffer:
                t.mark_removed()
                self._removed_tracks.append(t)
            else:
                remaining_lost.append(t)
        self._lost_tracks = remaining_lost

        # Cap removed track history
        if len(self._removed_tracks) > 200:
            self._removed_tracks = self._removed_tracks[-100:]

    @property
    def active_count(self) -> int:
        return len(self._tracked_tracks)

    def get_all_tracks(self) -> List[Track]:
        """Get all currently active tracks."""
        return list(self._tracked_tracks)
