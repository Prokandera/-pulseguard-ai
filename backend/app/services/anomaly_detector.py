from __future__ import annotations
import math
import numpy as np
from sklearn.ensemble import IsolationForest
from app.models.sensor import SensorReading


class AnomalyDetector:
    """Isolation Forest trained only on synthetic, expected wearable readings."""
    def __init__(self) -> None:
        rng = np.random.default_rng(42)
        normal = np.column_stack((rng.normal(76, 7, 800), rng.normal(98, .7, 800), rng.normal(1.0, .18, 800)))
        self.model = IsolationForest(contamination=0.03, random_state=42).fit(normal)

    @staticmethod
    def magnitude(reading: SensorReading) -> float:
        a = reading.accelerometer
        return math.sqrt(a.x ** 2 + a.y ** 2 + a.z ** 2)

    def evaluate(self, reading: SensorReading) -> tuple[bool, float, float, float]:
        magnitude = self.magnitude(reading)
        features = np.array([[reading.heart_rate, reading.spo2, magnitude]])
        # Negative decision scores are outside the learned normal region.
        score = float(self.model.decision_function(features)[0])
        model_anomaly = score < 0
        # Isolation Forest remains the primary detector. These transparent hard
        # bounds guarantee that deliberately extreme demo readings are not
        # missed because synthetic training data is necessarily approximate.
        extreme_reading = reading.heart_rate >= 120 or reading.spo2 <= 92 or magnitude >= 2.0
        confidence = max(0.0, min(1.0, -score / 0.18))
        if extreme_reading:
            confidence = max(confidence, 0.80)
        return model_anomaly or extreme_reading, score, confidence, magnitude
