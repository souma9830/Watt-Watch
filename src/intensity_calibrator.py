"""
Intensity Calibration Module

Provides per-room brightness threshold calibration for improved occupancy detection.
Supports auto-calibration from sample frames and manual threshold configuration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
from pathlib import Path


@dataclass
class RoomCalibration:
    """Calibration data for a single room."""
    room_id: str
    day_dark_threshold: int = 80
    day_medium_threshold: int = 160
    night_dark_threshold: int = 40
    night_medium_threshold: int = 100
    last_calibrated: Optional[str] = None
    sample_count: int = 0

    def get_thresholds(self, is_daytime: bool) -> Tuple[int, int]:
        """Get thresholds for day or night."""
        if is_daytime:
            return self.day_dark_threshold, self.day_medium_threshold
        return self.night_dark_threshold, self.night_medium_threshold

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "day": {
                "dark_threshold": self.day_dark_threshold,
                "medium_threshold": self.day_medium_threshold
            },
            "night": {
                "dark_threshold": self.night_dark_threshold,
                "medium_threshold": self.night_medium_threshold
            },
            "last_calibrated": self.last_calibrated,
            "sample_count": self.sample_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RoomCalibration':
        day = data.get("day", {})
        night = data.get("night", {})
        return cls(
            room_id=data.get("room_id", ""),
            day_dark_threshold=day.get("dark_threshold", 80),
            day_medium_threshold=day.get("medium_threshold", 160),
            night_dark_threshold=night.get("dark_threshold", 40),
            night_medium_threshold=night.get("medium_threshold", 100),
            last_calibrated=data.get("last_calibrated"),
            sample_count=data.get("sample_count", 0)
        )


class IntensityCalibrator:
    """
    Manages intensity calibration for multiple rooms.
    
    Supports:
    - Auto-calibration from sample frames
    - Day/night threshold switching
    - Manual threshold updates
    - Config persistence
    """

    DEFAULT_ROOM = "default"

    def __init__(
        self,
        config: Optional[dict] = None,
        day_start_hour: int = 6,
        day_end_hour: int = 18,
        sensitivity: float = 1.0
    ):
        self.day_start_hour = day_start_hour
        self.day_end_hour = day_end_hour
        self.sensitivity = sensitivity
        self._rooms: Dict[str, RoomCalibration] = {}
        self._config = config or {}
        self._load_rooms()

    def _load_rooms(self) -> None:
        """Load room calibrations from config."""
        cal_config = self._config.get("intensity_calibration", {})
        rooms_data = cal_config.get("rooms", {})

        if not rooms_data:
            self._rooms[self.DEFAULT_ROOM] = RoomCalibration(room_id=self.DEFAULT_ROOM)
            return

        for room_id, room_data in rooms_data.items():
            if isinstance(room_data, dict):
                self._rooms[room_id] = RoomCalibration.from_dict(room_data)
            else:
                self._rooms[room_id] = RoomCalibration(room_id=room_id)

    def save_to_config(self, config_path: Path) -> None:
        """Save current calibrations to config file."""
        import yaml

        cal_data = {}
        for room_id, calib in self._rooms.items():
            cal_data[room_id] = calib.to_dict()

        cal_config = {
            "enabled": True,
            "day_start_hour": self.day_start_hour,
            "day_end_hour": self.day_end_hour,
            "rooms": cal_data,
            "auto_calibrate": {
                "enabled": True,
                "sample_frames": 30,
                "min_samples": 10,
                "sensitivity": self.sensitivity
            }
        }

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        config["intensity_calibration"] = cal_config

        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def is_daytime(self, timestamp: Optional[datetime] = None) -> bool:
        """Check if given time is daytime."""
        if timestamp is None:
            timestamp = datetime.now()
        hour = timestamp.hour
        return self.day_start_hour <= hour < self.day_end_hour

    @staticmethod
    def calculate_brightness(frame: np.ndarray) -> float:
        """
        Calculate mean brightness of a frame.
        
        Args:
            frame: Video frame (BGR format from OpenCV)
            
        Returns:
            Mean brightness value (0-255)
        """
        gray = np.mean(frame, axis=2)
        return float(np.mean(gray))

    def classify_brightness(
        self,
        brightness: float,
        room_id: str = DEFAULT_ROOM,
        is_daytime: Optional[bool] = None
    ) -> str:
        """
        Classify brightness level based on room thresholds.
        
        Args:
            brightness: Calculated brightness value
            room_id: Room identifier
            is_daytime: Override day/night detection
            
        Returns:
            'dark', 'medium', or 'bright'
        """
        if room_id not in self._rooms:
            room_id = self.DEFAULT_ROOM

        if is_daytime is None:
            is_daytime = self.is_daytime()

        dark_th, medium_th = self._rooms[room_id].get_thresholds(is_daytime)

        if brightness < dark_th:
            return "dark"
        elif brightness < medium_th:
            return "medium"
        return "bright"

    def auto_calibrate(
        self,
        room_id: str,
        empty_frames: List[np.ndarray],
        occupied_frames: Optional[List[np.ndarray]] = None,
        sensitivity: Optional[float] = None
    ) -> RoomCalibration:
        """
        Auto-calibrate thresholds based on sample frames.
        
        Args:
            room_id: Room identifier
            empty_frames: List of frames from empty room
            occupied_frames: Optional frames from occupied room
            sensitivity: Override sensitivity (0.5-1.5)
            
        Returns:
            Updated RoomCalibration
        """
        if room_id not in self._rooms:
            self._rooms[room_id] = RoomCalibration(room_id=room_id)

        calib = self._rooms[room_id]
        sens = sensitivity or self.sensitivity

        empty_brightnesses = [self.calculate_brightness(f) for f in empty_frames]
        empty_avg = np.mean(empty_brightnesses) if empty_brightnesses else 0

        if occupied_frames:
            occupied_brightnesses = [self.calculate_brightness(f) for f in occupied_frames]
            occupied_avg = np.mean(occupied_brightnesses) if occupied_brightnesses else 255
        else:
            occupied_avg = empty_avg + 80

        mid_point = (empty_avg + occupied_avg) / 2
        range_val = occupied_avg - empty_avg
        margin = (range_val / 4) * sens

        day_dark = int(max(0, empty_avg - margin))
        day_medium = int(min(255, mid_point + margin))

        night_factor = 0.5
        night_dark = int(max(0, day_dark * night_factor))
        night_medium = int(max(night_dark + 10, day_medium * night_factor))

        calib.day_dark_threshold = day_dark
        calib.day_medium_threshold = day_medium
        calib.night_dark_threshold = night_dark
        calib.night_medium_threshold = night_medium
        calib.last_calibrated = datetime.now().isoformat()
        calib.sample_count = len(empty_brightnesses)

        return calib

    def update_thresholds(
        self,
        room_id: str,
        day_dark: Optional[int] = None,
        day_medium: Optional[int] = None,
        night_dark: Optional[int] = None,
        night_medium: Optional[int] = None
    ) -> RoomCalibration:
        """Manually update thresholds for a room."""
        if room_id not in self._rooms:
            self._rooms[room_id] = RoomCalibration(room_id=room_id)

        calib = self._rooms[room_id]

        if day_dark is not None:
            calib.day_dark_threshold = day_dark
        if day_medium is not None:
            calib.day_medium_threshold = day_medium
        if night_dark is not None:
            calib.night_dark_threshold = night_dark
        if night_medium is not None:
            calib.night_medium_threshold = night_medium

        calib.last_calibrated = datetime.now().isoformat()

        return calib

    def get_calibration(self, room_id: str = DEFAULT_ROOM) -> Optional[RoomCalibration]:
        """Get calibration for a room."""
        return self._rooms.get(room_id)

    def get_all_rooms(self) -> Dict[str, RoomCalibration]:
        """Get all room calibrations."""
        return self._rooms.copy()

    def get_occupancy_indicator(
        self,
        frame: np.ndarray,
        room_id: str = DEFAULT_ROOM
    ) -> Dict[str, any]:
        """
        Get comprehensive occupancy indicator based on intensity.
        
        Returns:
            Dict with brightness, level, thresholds, and recommendation
        """
        brightness = self.calculate_brightness(frame)
        is_daytime = self.is_daytime()
        level = self.classify_brightness(brightness, room_id, is_daytime)

        calib = self._rooms.get(room_id, self._rooms.get(self.DEFAULT_ROOM))
        dark_th, medium_th = calib.get_thresholds(is_daytime)

        return {
            "room_id": room_id,
            "brightness": round(brightness, 2),
            "level": level,
            "is_daytime": is_daytime,
            "thresholds": {
                "dark": dark_th,
                "medium": medium_th
            },
            "recommendation": self._get_recommendation(level, brightness, dark_th, medium_th)
        }

    def _get_recommendation(
        self,
        level: str,
        brightness: float,
        dark_th: int,
        medium_th: int
    ) -> str:
        """Get recommendation based on brightness level."""
        if level == "dark":
            if brightness < dark_th * 0.5:
                return "very_low_occupancy"
            return "low_occupancy"
        elif level == "medium":
            return "normal_occupancy"
        return "high_occupancy"

    def validate_thresholds(self, room_id: str) -> List[str]:
        """Validate thresholds and return warnings."""
        warnings = []
        calib = self._rooms.get(room_id)

        if not calib:
            return [f"Room {room_id} not found"]

        day_dark = calib.day_dark_threshold
        day_medium = calib.day_medium_threshold
        night_dark = calib.night_dark_threshold
        night_medium = calib.night_medium_threshold

        if day_dark >= day_medium:
            warnings.append("Day dark threshold >= medium threshold")

        if night_dark >= night_medium:
            warnings.append("Night dark threshold >= medium threshold")

        if day_dark < 10 or day_dark > 200:
            warnings.append(f"Day dark threshold ({day_dark}) outside typical range (10-200)")

        if day_medium < 50 or day_medium > 250:
            warnings.append(f"Day medium threshold ({day_medium}) outside typical range (50-250)")

        return warnings


def create_calibrator(config: dict) -> IntensityCalibrator:
    """Factory function to create IntensityCalibrator from config."""
    cal_config = config.get("intensity_calibration", {})
    return IntensityCalibrator(
        config=config,
        day_start_hour=cal_config.get("day_start_hour", 6),
        day_end_hour=cal_config.get("day_end_hour", 18),
        sensitivity=cal_config.get("auto_calibrate", {}).get("sensitivity", 1.0)
    )
