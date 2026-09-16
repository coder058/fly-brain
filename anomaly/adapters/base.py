"""Sensor adapters (stubs for Phase 9 — no hardware yet)."""
from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np

class SensorAdapter(ABC):
    @abstractmethod
    def to_window(self, raw) -> np.ndarray:
        """Return float32 array shaped (T, C) for the anomaly encoder."""

class GenericSensorAdapter(SensorAdapter):
    def to_window(self, raw) -> np.ndarray:
        x = np.asarray(raw, dtype=np.float32)
        if x.ndim == 1:
            x = x[:, None]
        return x

class CameraAdapter(GenericSensorAdapter): ...
class IMUAdapter(GenericSensorAdapter): ...
class AccelerometerAdapter(GenericSensorAdapter): ...
class MicrophoneAdapter(GenericSensorAdapter): ...
