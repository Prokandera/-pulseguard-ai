from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Accelerometer(BaseModel):
    x: float
    y: float
    z: float


class SensorReading(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    heart_rate: float
    spo2: float
    accelerometer: Accelerometer
