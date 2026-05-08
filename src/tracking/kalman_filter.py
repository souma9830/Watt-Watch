"""
Kalman Filter for bounding box state estimation.
State vector: [cx, cy, w, h, vx, vy, vw, vh]
Measurement:  [cx, cy, w, h]
"""

import numpy as np
from typing import Tuple


class KalmanFilter:
    """
    Constant velocity Kalman filter for tracking bounding boxes.
    Predicts the next position of a tracked object.

    State: (cx, cy, w, h, vx, vy, vw, vh)
    Observation: (cx, cy, w, h)
    """

    def __init__(self):
        # State transition matrix (constant velocity model)
        self.F = np.eye(8, dtype=np.float64)
        for i in range(4):
            self.F[i, i + 4] = 1.0  # position += velocity

        # Observation matrix (observe only position/size)
        self.H = np.eye(4, 8, dtype=np.float64)

        # Process noise covariance
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

        # Measurement noise covariance (fixed)
        self.R = np.diag([
            (1.0 / 20) ** 2,  # cx
            (1.0 / 20) ** 2,  # cy
            (1.0 / 20) ** 2,  # w
            (1.0 / 20) ** 2,  # h
        ]).astype(np.float64)

    def initiate(self, measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Initialize state from first measurement [cx, cy, w, h].
        Returns (mean, covariance).
        """
        mean_pos = measurement
        mean_vel = np.zeros(4, dtype=np.float64)
        mean = np.concatenate([mean_pos, mean_vel])

        std = [
            2 * self._std_weight_position * measurement[2],  # cx
            2 * self._std_weight_position * measurement[3],  # cy
            2 * self._std_weight_position * measurement[2],  # w
            2 * self._std_weight_position * measurement[3],  # h
            10 * self._std_weight_velocity * measurement[2],  # vx
            10 * self._std_weight_velocity * measurement[3],  # vy
            10 * self._std_weight_velocity * measurement[2],  # vw
            10 * self._std_weight_velocity * measurement[3],  # vh
        ]
        covariance = np.diag(np.square(std)).astype(np.float64)
        return mean, covariance

    def predict(
        self, mean: np.ndarray, covariance: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Predict next state using constant velocity model."""
        std = [
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
            self._std_weight_velocity * mean[2],
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[2],
            self._std_weight_velocity * mean[3],
        ]
        Q = np.diag(np.square(std)).astype(np.float64)

        mean = self.F @ mean
        covariance = self.F @ covariance @ self.F.T + Q
        return mean, covariance

    def update(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        measurement: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Correct state with new measurement [cx, cy, w, h]."""
        projected_mean = self.H @ mean
        projected_cov = self.H @ covariance @ self.H.T + self.R

        # Kalman gain
        K = covariance @ self.H.T @ np.linalg.inv(projected_cov)

        innovation = measurement - projected_mean
        mean = mean + K @ innovation
        covariance = (np.eye(8) - K @ self.H) @ covariance
        return mean, covariance

    def gating_distance(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        measurements: np.ndarray,
    ) -> np.ndarray:
        """
        Compute Mahalanobis distance between predicted state and measurements.
        Used to gate unlikely associations.
        """
        projected_mean = self.H @ mean
        projected_cov = self.H @ covariance @ self.H.T + self.R

        chol = np.linalg.cholesky(projected_cov)
        diff = measurements - projected_mean
        z = np.linalg.solve(chol, diff.T)
        squared_maha = np.sum(z * z, axis=0)
        return squared_maha
