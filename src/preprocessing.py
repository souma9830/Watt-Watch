"""
Low-light preprocessing for improved detection in dark environments.
Supports intensity calibration for room-specific brightness thresholds.
"""

import numpy as np
from typing import Tuple, List, Optional, Any


LOW_LIGHT_THRESHOLD = 50


def detect_low_light(frame: np.ndarray, threshold: float = LOW_LIGHT_THRESHOLD) -> Tuple[bool, float]:
    """
    Detect if frame is low-light.
    
    Args:
        frame: Video frame (BGR format from OpenCV)
        threshold: Custom brightness threshold (optional)
        
    Returns:
        Tuple of (is_low_light, brightness_score)
    """
    gray = np.mean(frame, axis=2)
    brightness = np.mean(gray)
    is_low_light = brightness < threshold
    
    return is_low_light, float(brightness)


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Enhance frame for better detection in low-light.
    
    Uses CLAHE (Contrast Limited Adaptive Histogram Equalization)
    to improve visibility in dark regions.
    
    Args:
        frame: Video frame (BGR format)
        
    Returns:
        Enhanced frame (BGR format)
    """
    try:
        import cv2
        
        # Convert to YUV color space
        yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        
        # Apply CLAHE to Y channel (luminance)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        yuv[:, :, 0] = clahe.apply(yuv[:, :, 0])
        
        # Convert back to BGR
        enhanced = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        
        return enhanced
        
    except ImportError:
        # Fallback: simple histogram equalization
        return enhance_frame_fallback(frame)


def enhance_frame_fallback(frame: np.ndarray) -> np.ndarray:
    """Fallback enhancement without cv2."""
    # Simple normalization
    normalized = frame.astype(np.float32)
    normalized = normalized * (255.0 / np.max(normalized))
    return normalized.astype(np.uint8)


class LowLightDetector:
    """Track low-light conditions over time with optional calibration support."""
    
    def __init__(
        self,
        threshold: float = LOW_LIGHT_THRESHOLD,
        calibrator: Optional[Any] = None,
        room_id: str = "default"
    ):
        self.threshold = threshold
        self.calibrator = calibrator
        self.room_id = room_id
        self.low_light_count = 0
        self.total_frames = 0
    
    def set_calibrator(self, calibrator: Any, room_id: str = "default") -> None:
        """Set intensity calibrator for room-specific thresholds."""
        self.calibrator = calibrator
        self.room_id = room_id
    
    def process(self, frame: np.ndarray) -> Tuple[bool, float, bool]:
        """
        Process a frame for low-light detection.
        
        Args:
            frame: Video frame
            
        Returns:
            Tuple of (is_low_light, brightness, should_enhance)
        """
        self.total_frames += 1

        if self.calibrator:
            brightness = self.calibrator.calculate_brightness(frame)
            is_daytime = self.calibrator.is_daytime()
            level = self.calibrator.classify_brightness(brightness, self.room_id, is_daytime)
            is_low_light = level == "dark"
        else:
            is_low_light, brightness = detect_low_light(frame, self.threshold)
        
        if is_low_light:
            self.low_light_count += 1
        
        should_enhance = is_low_light
        
        return is_low_light, brightness, should_enhance
    
    def get_intensity_info(self, frame: np.ndarray) -> dict:
        """Get detailed intensity information if calibrator is set."""
        if self.calibrator:
            return self.calibrator.get_occupancy_indicator(frame, self.room_id)
        return {}
    
    def get_stats(self) -> dict:
        """Get low-light statistics."""
        if self.total_frames == 0:
            return {
                'total_frames': 0,
                'low_light_frames': 0,
                'percentage': 0.0
            }
        
        return {
            'total_frames': self.total_frames,
            'low_light_frames': self.low_light_count,
            'percentage': (self.low_light_count / self.total_frames) * 100
        }


def create_low_light_detector(threshold: float = LOW_LIGHT_THRESHOLD) -> LowLightDetector:
    """Factory function to create LowLightDetector."""
    return LowLightDetector(threshold=threshold)