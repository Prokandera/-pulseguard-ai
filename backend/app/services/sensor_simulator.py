"""A smooth, stateful sensor source shared by every dashboard client."""
from __future__ import annotations
import math
import random
from app.models.sensor import Accelerometer, SensorReading


class SensorSimulator:
    def __init__(self, anomaly_frequency: float) -> None:
        self.heart_rate, self.spo2 = 76.0, 98.0
        self.movement = [0.05, 0.95, 0.08]
        self.anomaly_frequency = anomaly_frequency
        self._anomaly_ticks = 0
        self._scenario = "combined"

    def trigger_anomaly(self) -> str:
        self._anomaly_ticks = 8
        self._scenario = random.choice(["high_heart_rate", "low_spo2", "high_movement", "combined"])
        # A demo trigger must be visible immediately, rather than slowly drifting
        # from a normal baseline over several seconds.
        if self._scenario in {"high_heart_rate", "combined"}:
            self.heart_rate = 138.0
        if self._scenario in {"low_spo2", "combined"}:
            self.spo2 = 90.0
        if self._scenario in {"high_movement", "combined"}:
            self.movement = [1.5, 1.8, 1.3]
        return self._scenario

    @staticmethod
    def _drift(value: float, target: float, variation: float) -> float:
        return value + (target - value) * 0.18 + random.uniform(-variation, variation)

    def next_reading(self) -> SensorReading:
        if self._anomaly_ticks == 0 and random.random() < self.anomaly_frequency:
            self.trigger_anomaly()
        active = self._anomaly_ticks > 0
        if active:
            self._anomaly_ticks -= 1
        high_hr = active and self._scenario in {"high_heart_rate", "combined"}
        low_spo2 = active and self._scenario in {"low_spo2", "combined"}
        high_move = active and self._scenario in {"high_movement", "combined"}
        self.heart_rate = self._drift(self.heart_rate, 150 if high_hr else 76, 2.5)
        self.spo2 = self._drift(self.spo2, 88 if low_spo2 else 98, 0.35)
        target = [1.8, 2.2, 1.5] if high_move else [0.05, 0.95, 0.08]
        self.movement = [self._drift(v, t, 0.08 if not high_move else 0.22) for v, t in zip(self.movement, target)]
        return SensorReading(heart_rate=round(self.heart_rate, 1), spo2=round(self.spo2, 1),
                             accelerometer=Accelerometer(x=round(self.movement[0], 2), y=round(self.movement[1], 2), z=round(self.movement[2], 2)))
