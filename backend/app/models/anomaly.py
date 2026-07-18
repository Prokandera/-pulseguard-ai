from datetime import datetime
from pydantic import BaseModel


class AnomalyEvent(BaseModel):
    event_id: str
    timestamp: datetime
    heart_rate: float
    spo2: float
    accelerometer_magnitude: float
    anomaly_score: float
    confidence: float
    severity: str
    llm_insight: str | None = None
